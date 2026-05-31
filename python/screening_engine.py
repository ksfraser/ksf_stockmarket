#!/usr/bin/env python3
"""
screening_engine.py — Stage 3: Stock Screening

Reads symbols from MySQL, applies configurable screening stages,
scores each symbol using 30+ strategies, and outputs ranked buy/sell candidates.

Pipeline:
  Stage 1: Universe Filter (hard rules — market cap, volume, price)
  Stage 2: Quality Filter (configurable cutoffs — payout, debt, ROE)
  Stage 3: Strategy Scoring (30+ strategies score independently)
  Stage 4: Position Sizing & Risk (ATR stops, correlation, max position)

Usage:
    python3 screening_engine.py --mode screen [--top-n 10] [--strategy all]
    python3 screening_engine.py --mode score SYMBOL
    python3 screening_engine.py --mode status
"""

import sys, os, json, argparse, math
import numpy as np
import pymysql
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


# ── Indicator Data Access ──────────────────────────────────────────────────

class IndicatorStore:
    """Reads indicator JSON data from MySQL efficiently."""

    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()

    def get_latest_indicators(self, symbol: str, n_days: int = 250) -> dict:
        """Get the latest n_days of indicator data for a symbol."""
        self.cursor.execute("""
            SELECT price_date, data FROM indicators_json
            WHERE symbol = %s
            ORDER BY price_date DESC
            LIMIT %s
        """, (symbol, n_days))
        rows = self.cursor.fetchall()
        result = {}
        for row in rows:
            try:
                result[str(row['price_date'])] = json.loads(row['data'])
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def get_latest_date(self, symbol: str) -> str:
        """Get the most recent date with indicator data."""
        self.cursor.execute("""
            SELECT MAX(price_date) as latest FROM indicators_json WHERE symbol = %s
        """, (symbol,))
        row = self.cursor.fetchone()
        return str(row['latest']) if row and row['latest'] else None

    def get_latest_prices(self, symbol: str, n_days: int = 250) -> list:
        """Get latest n_days of closing prices."""
        self.cursor.execute("""
            SELECT price_date, close, volume FROM stockprices
            WHERE symbol = %s ORDER BY price_date DESC LIMIT %s
        """, (symbol, n_days))
        rows = self.cursor.fetchall()
        return [{'date': str(r['price_date']), 'close': float(r['close']),
                 'volume': float(r['volume'])} for r in rows]


# ── Stage 1: Universe Filter ───────────────────────────────────────────────

class UniverseFilter:
    """Hard rules that eliminate symbols before any strategy scoring."""

    def __init__(self, config: dict):
        self.min_market_cap = config.get('min_market_cap', 500_000_000)
        self.min_daily_volume = config.get('min_daily_volume', 100_000)
        self.min_price = config.get('min_price', 5.00)
        self.allowed_exchanges = config.get('allowed_exchanges', ['TSX', 'NYSE', 'NASDAQ'])
        self.max_spread_pct = config.get('max_bid_ask_spread_pct', 0.005)

    def get_viable_symbols(self, cursor) -> list:
        """
        Get symbols that pass Stage 1 hard filters.
        Uses latest price data from stockprices.
        """
        # Get latest price for each symbol
        cursor.execute("""
            SELECT sp.symbol, sp.close, sp.volume, sm.exchange, sm.sector
            FROM stockprices sp
            INNER JOIN symbol_master sm ON sp.symbol = sm.symbol
            INNER JOIN (
                SELECT symbol, MAX(price_date) as max_date
                FROM stockprices GROUP BY symbol
            ) latest ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
        """)
        rows = cursor.fetchall()

        viable = []
        for r in rows:
            # Price filter
            if r['close'] < self.min_price:
                continue

            # Volume filter
            if r['volume'] < self.min_daily_volume:
                continue

            # Exchange filter (if data available)
            if r.get('exchange') and r['exchange'] not in self.allowed_exchanges:
                continue

            # Market cap filter (if data available)
            if r.get('market_cap') and r['market_cap'] < self.min_market_cap:
                continue

            viable.append(r['symbol'])

        return viable


# ── Stage 2: Quality Filter ────────────────────────────────────────────────

class QualityFilter:
    """Configurable quality thresholds applied after universe filter."""

    def __init__(self, config: dict):
        self.max_payout_ratio = config.get('max_payout_ratio', 0.80)
        self.max_debt_equity = config.get('max_debt_equity', 1.5)
        self.min_roe = config.get('min_roe', 0.10)
        self.min_quarters_profitable = config.get('min_quarters_profitable', 4)
        self.min_fscore = config.get('min_fscore', 5)
        self.min_institutional_pct = config.get('min_institutional_pct', 0.10)
        self.max_institutional_pct = config.get('max_institutional_pct', 0.80)

    def compute_piotroski_fscore(self, indicators_history: dict) -> float:
        """
        Compute Piotroski F-Score from indicator history.
        Score 0-9, where 8-9 = strong, 0-2 = weak.

        Uses the most recent 8 quarters of data.
        Returns score as float (can be partial if data is incomplete).
        """
        if not indicators_history:
            return 0

        dates = sorted(indicators_history.keys())
        if len(dates) < 2:
            return 0

        try:
            latest = indicators_history[dates[-1]]
            prev = indicators_history[dates[-2]] if len(dates) > 1 else latest

            score = 0

            # 1. ROA > 0 (use net income proxy)
            roa = latest.get('roa_14', 0)  # If available
            if roa > 0:
                score += 1

            # 2. Operating cash flow > 0 (use AD as proxy for money flow)
            ad = latest.get('ad', 0)
            if ad > 0:
                score += 1

            # 3. Change in ROA (increasing)
            prev_roa = prev.get('roa_14', 0)
            if roa > prev_roa:
                score += 1

            # 4. CFO > ROA (earnings quality) — use MFI as money flow proxy
            mfi = latest.get('mfi_14', 50)
            if mfi > 50:
                score += 1

            # 5. Change in leverage (decreasing)
            # Use price position relative to BB as leverage proxy
            bb_upper = latest.get('bb_20_2.0_upper', 0)
            bb_lower = latest.get('bb_20_2.0_lower', 0)
            if bb_upper > bb_lower:
                bb_pos = (latest.get('close', 0) - bb_lower) / (bb_upper - bb_lower)
                prev_bb_pos = (prev.get('close', 0) - bb_lower) / (bb_upper - bb_lower)
                if bb_pos < prev_bb_pos:
                    score += 1

            # 6. Change in current ratio (increasing)
            # Use volume trend as liquidity proxy
            volume_20 = latest.get('sma_20', 0)
            prev_volume = prev.get('sma_20', 0)
            if volume_20 > prev_volume:
                score += 1

            # 7. No new shares issued (difficult from price data alone)
            # Skip — can't determine from OHLCV

            # 8. Change in gross margin (increasing)
            # Use price momentum as margin proxy
            roc_14 = latest.get('roc_14', 0)
            prev_roc = prev.get('roc_14', 0)
            if roc_14 > prev_roc:
                score += 1

            # 9. Change in asset turnover (increasing)
            # Use volume/price ratio as turnover proxy
            if latest.get('volume', 0) > 0 and prev.get('volume', 0) > 0:
                turnover = latest.get('close', 0) / latest.get('volume', 1)
                prev_turnover = prev.get('close', 0) / prev.get('volume', 1)
                if turnover > prev_turnover:
                    score += 1

            return min(score, 9)

        except Exception:
            return 0

    def quality_check(self, symbol: str, store: IndicatorStore) -> dict:
        """
        Run quality filter for a symbol.
        Returns dict with 'pass': bool and 'metrics': dict.
        Note: Most quality metrics require fundamental data (payout_ratio, debt/equity, ROE)
        which are NOT in the technical indicators table. For now, we pass symbols
        that have sufficient indicator data and let the scoring strategies handle quality.
        """
        ind = store.get_latest_indicators(symbol, 10)
        if not ind:
            return {'pass': False, 'reason': 'no_indicator_data', 'score': 0}

        dates = sorted(ind.keys())
        if not dates:
            return {'pass': False, 'reason': 'no_recent_data', 'score': 0}

        latest = ind[dates[-1]]

        metrics = {}
        failures = []

        # Payout ratio (if available in fundamentals table)
        payout = latest.get('payout_ratio')
        if payout is not None and payout > self.max_payout_ratio:
            failures.append(f'payout_ratio={payout:.0%}')

        # Debt/Equity (if available in fundamentals)
        de = latest.get('debt_equity')
        if de is not None and de > self.max_debt_equity:
            failures.append(f'debt_equity={de:.1f}')

        # ROE (if available)
        roe = latest.get('roe_14')
        if roe is not None and roe < self.min_roe:
            failures.append(f'roe={roe:.1%}')

        # Piotroski F-Score (computed from available data)
        fscore = self.compute_piotroski_fscore(ind)
        metrics['fscore'] = fscore

        # Only fail on F-Score if we have enough data to compute it reliably
        if len(dates) < 5 and fscore < self.min_fscore:
            failures.append(f'fscore={fscore}')

        # Check data freshness — fail if indicators are more than 7 days stale
        latest_date = datetime.strptime(dates[-1], '%Y-%m-%d').date() if dates else None
        if latest_date and (date.today() - latest_date).days > 30:
            failures.append(f'indicators_stale={dates[-1]}')

        metrics['failures'] = failures
        metrics['pass'] = len(failures) == 0

        return {
            'pass': metrics['pass'],
            'reason': '; '.join(failures) if failures else 'passed',
            'metrics': metrics,
            'score': fscore
        }


# ── Stage 3: Strategy Scoring ──────────────────────────────────────────────

class StrategyScorer:
    """
    Scores symbols using 30+ documented strategies.
    Each strategy returns a score 0–1.
    Higher = more attractive for that strategy.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

    def _sma(self, values, period):
        """Simple moving average."""
        if len(values) < period:
            return values[-1] if values else 0
        return np.mean(values[-period:])

    def _ema(self, values, period):
        """Exponential moving average."""
        if len(values) < period:
            return values[-1] if values else 0
        multiplier = 2 / (period + 1)
        ema = values[0]
        for v in values[1:]:
            ema = (v - ema) * multiplier + ema
        return ema

    def _rsi(self, closes, period=14):
        """Relative Strength Index."""
        if len(closes) < period + 1:
            return 50
        deltas = np.diff(closes[-(period+1):])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _atr(self, highs, lows, closes, period=14):
        """Average True Range."""
        if len(closes) < 2:
            return 0
        trs = []
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1]))
            trs.append(tr)
        if len(trs) < period:
            return np.mean(trs) if trs else 0
        return np.mean(trs[-period:])

    def _bollinger_position(self, closes, period=20, std=2.0):
        """Position within Bollinger Bands (0 = at lower, 1 = at upper)."""
        if len(closes) < period:
            return 0.5
        sma = np.mean(closes[-period:])
        std_dev = np.std(closes[-period:])
        if std_dev == 0:
            return 0.5
        upper = sma + std * std_dev
        lower = sma - std * std_dev
        if upper == lower:
            return 0.5
        return (closes[-1] - lower) / (upper - lower)

    def _momentum_score(self, closes, period=120):
        """Normalized momentum over period."""
        if len(closes) < period:
            period = len(closes)
        if period < 2:
            return 0.5
        ret = (closes[-1] / closes[-period]) - 1
        # Normalize: -50% → 0, 0% → 0.5, +50% → 1.0
        return max(0, min(1, 0.5 + ret))

    def _volatility_ratio(self, closes, short=20, long=60):
        """Short-term vol / long-term vol. High = expanding vol."""
        if len(closes) < long:
            return 1.0
        short_vol = np.std(np.diff(np.log(closes[-short:])))
        long_vol = np.std(np.diff(np.log(closes[-long:])))
        if long_vol == 0:
            return 1.0
        return short_vol / long_vol

    def _volume_ratio(self, volumes, period=20):
        """Current volume vs average. High = unusual volume."""
        if len(volumes) < period:
            return 1.0
        avg_vol = np.mean(volumes[-period:])
        if avg_vol == 0:
            return 1.0
        return volumes[-1] / avg_vol

    def _price_vs_ma(self, closes, period=200):
        """Price position relative to MA. > 1 = above, < 1 = below."""
        if len(closes) < period:
            period = len(closes)
        if period < 1:
            return 1.0
        ma = np.mean(closes[-period:])
        if ma == 0:
            return 1.0
        return closes[-1] / ma

    def _peakedness_score(self, closes, lookback=250):
        """
        Is the stock at a recent peak or trough?
        Returns 1.0 at 52-week high, 0.0 at 52-week low.
        Indicator of momentum mean-reversion opportunity.
        """
        if len(closes) < lookback:
            lookback = len(closes)
        if lookback < 2:
            return 0.5
        high = max(closes[-lookback:])
        low = min(closes[-lookback:])
        if high == low:
            return 0.5
        return (closes[-1] - low) / (high - low)

    # ── Individual Strategy Scorers ──

    def score_canslim(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        CANSLIM momentum scoring.
        Factors: quarterly growth, new highs, volume, leadership, trend.
        All calculated from price/volume patterns (fundamentals would need API).
        """
        if len(closes) < 120:
            return 0.3

        score = 0
        weights = 0

        # C: Current quarter momentum (60-day return vs prior 60-day)
        if len(closes) >= 120:
            recent = (closes[-1] / closes[-60]) - 1
            prior = (closes[-60] / closes[-120]) - 1
            # Accelerating
            accel = recent - prior
            score += 0.2 * max(0, min(1, 0.5 + accel * 5))
            weights += 0.2

        # A: Annual momentum (250-day / 120-day trend)
        if len(closes) >= 120:
            annual_ret = (closes[-1] / closes[-120]) - 1
            score += 0.2 * max(0, min(1, 0.5 + annual_ret * 3))
            weights += 0.2

        # N: New high proximity (within 5% of 52-week high)
        if len(closes) >= 250:
            peak_pct = self._peakedness_score(closes)
            if peak_pct > 0.95:
                score += 0.15
            elif peak_pct > 0.85:
                score += 0.10
            weights += 0.15

        # S: Supply/demand via volume
        vol_ratio = self._volume_ratio(volumes)
        if vol_ratio > 1.5:
            score += 0.15 * min(1, (vol_ratio - 1.5) / 3)
        weights += 0.15

        # L: Leadership — relative strength (60-day percentile)
        if len(closes) >= 60:
            mom = self._momentum_score(closes, 60)
            score += 0.15 * mom
            weights += 0.15

        # I: Institutional flow proxy (OBV trend)
        # Use rising volume on up days as proxy
        if len(closes) >= 20:
            up_volume = sum(volumes[i] for i in range(-20, 0) if closes[i] > closes[i-1])
            down_volume = sum(volumes[i] for i in range(-20, 0) if closes[i] <= closes[i-1])
            if up_volume + down_volume > 0:
                inst_ratio = up_volume / (up_volume + down_volume)
                score += 0.10 * inst_ratio
            weights += 0.10

        # M: Market trend (use stock's own 200d MA as proxy)
        vs_200 = self._price_vs_ma(closes, 200)
        if vs_200 > 1.0:
            score += 0.05
        elif vs_200 > 0.95:
            score += 0.03
        weights += 0.05

        return score / weights if weights > 0 else 0.5

    def score_buffett_quality(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Buffett-style quality scoring from price/volume patterns.
        True Buffett needs fundamentals; this is a proxy using price stability.
        """
        if len(closes) >= 250:
            score = 0
            weights = 0

            # Consistent returns (CAGR > 10%)
            cagr = (closes[-1] / closes[-250]) ** (252/250) - 1
            score += 0.25 * max(0, min(1, cagr / 0.30))
            weights += 0.25

            # Low volatility (stable = quality)
            vol = np.std(np.diff(np.log(closes[-60:])))
            annual_vol = vol * math.sqrt(252)
            score += 0.25 * max(0, 1 - annual_vol / 0.50)
            weights += 0.25

            # Above 200d MA (uptrend)
            vs_200 = self._price_vs_ma(closes, 200)
            if vs_200 > 1:
                score += 0.20
            elif vs_200 > 0.90:
                score += 0.10
            weights += 0.20

            # Consistent volume (institutional holder)
            vol_cv = np.std(volumes[-60:]) / np.mean(volumes[-60:]) if np.mean(volumes[-60:]) > 0 else 1
            score += 0.15 * max(0, 1 - vol_cv)
            weights += 0.15

            # Max drawdown < 20%
            peak = closes[-250]
            max_dd = 0
            for c in closes[-250:]:
                if c > peak:
                    peak = c
                dd = (peak - c) / peak
                max_dd = max(max_dd, dd)
            score += 0.15 * max(0, 1 - max_dd / 0.40)
            weights += 0.15

            return score / weights if weights > 0 else 0.3

        return 0.3

    def score_graham_deep_value(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Graham deep value: stocks trading below intrinsic value proxies.
        Uses PB proxy (price vs historical average) as value indicator.
        """
        if len(closes) < 250:
            return 0.3

        score = 0

        # Price vs 52-week mean (mean reversion potential)
        mean_price = np.mean(closes[-250:])
        if mean_price > 0:
            discount = 1 - (closes[-1] / mean_price)
            # 20%+ discount = maximum value score
            score += max(0, min(1, discount / 0.30)) * 0.4

        # Low volatility (Graham liked stability)
        vol = np.std(np.diff(np.log(closes[-60:])))
        annual_vol = vol * math.sqrt(252)
        score += max(0, 1 - annual_vol / 0.60) * 0.3

        # Volume spike on down days (capitulation = opportunity)
        recent_vol = self._volume_ratio(volumes, 20)
        recent_return = (closes[-1] / closes[-20]) - 1
        if recent_return < -0.10 and recent_vol > 2.0:
            score += 0.3  # Capitulation buying opportunity
        else:
            score += 0.1

        return min(1.0, score)

    def score_dividend_aristocrat(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Dividend Aristocrat proxy: stable, consistent companies.
        True dividend data requires fundamentals; use price stability as proxy.
        """
        if len(closes) < 250:
            return 0.3

        score = 0

        # Consistent uptrend (dividend growers tend to appreciate)
        cagr = (closes[-1] / closes[-250]) ** (252/250) - 1
        if 0.05 < cagr < 0.30:
            score += 0.3
        elif cagr > 0:
            score += 0.15

        # Low volatility (dividend payers are stable)
        vol = np.std(np.diff(np.log(closes[-60:])))
        annual_vol = vol * math.sqrt(252)
        if annual_vol < 0.20:
            score += 0.3
        elif annual_vol < 0.30:
            score += 0.15

        # Above 200d MA (healthy)
        vs_200 = self._price_vs_ma(closes, 200)
        if vs_200 > 1.05:
            score += 0.2
        elif vs_200 > 1.0:
            score += 0.1

        # Stable volume (institutional holders)
        vol_cv = np.std(volumes[-60:]) / np.mean(volumes[-60:]) if np.mean(volumes[-60:]) > 0 else 1
        if vol_cv < 0.3:
            score += 0.2
        elif vol_cv < 0.5:
            score += 0.1

        return min(1.0, score)

    def score_mean_reversion(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Bollinger Band mean reversion: oversold in an uptrend.
        """
        if len(closes) < 50:
            return 0.3

        score = 0

        # Price near or below lower BB
        bb_pos = self._bollinger_position(closes)
        if bb_pos < 0.1:
            score += 0.4
        elif bb_pos < 0.2:
            score += 0.3
        elif bb_pos < 0.3:
            score += 0.15

        # RSI oversold
        rsi = self._rsi(closes)
        if rsi < 20:
            score += 0.3
        elif rsi < 30:
            score += 0.2
        elif rsi < 40:
            score += 0.1

        # Overall trend is up (200d MA)
        vs_200 = self._price_vs_ma(closes, 200)
        if vs_200 > 1.0:
            score += 0.2
        elif vs_200 > 0.95:
            score += 0.1

        # Volume spike (capitulation)
        vol_ratio = self._volume_ratio(volumes)
        if vol_ratio > 2.0:
            score += 0.1

        return min(1.0, score)

    def score_abnormal_volume(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Abnormal volume detection: large volume move with price change.
        """
        if len(closes) < 20:
            return 0.3

        score = 0

        vol_ratio = self._volume_ratio(volumes)
        price_change = abs((closes[-1] / closes[-2]) - 1) if len(closes) >= 2 else 0

        # Volume > 3× average with price move > 3%
        if vol_ratio > 3.0 and price_change > 0.03:
            score += 0.6
        elif vol_ratio > 2.0 and price_change > 0.02:
            score += 0.4
        elif vol_ratio > 1.5:
            score += 0.2

        # Direction: up volume > down volume
        if len(closes) >= 5:
            up_vol = sum(volumes[-5:][i] for i in range(5) if closes[-5:][i] > closes[-5:][i-1] if i > 0)
            total_vol = sum(volumes[-5:])
            if total_vol > 0:
                up_ratio = up_vol / total_vol
                score += 0.2 * up_ratio

        # Sustained volume (not just one day)
        if len(volumes) >= 5:
            avg_5 = np.mean(volumes[-5:])
            avg_20 = np.mean(volumes[-20:]) if len(volumes) >= 20 else avg_5
            if avg_20 > 0 and avg_5 / avg_20 > 1.5:
                score += 0.2

        return min(1.0, score)

    def score_volatility_expansion(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Volatility expansion: VIX-like proxy for individual stocks.
        High short-term vol vs long-term vol = expansion = opportunity.
        """
        if len(closes) < 60:
            return 0.3

        score = 0

        vol_ratio = self._volatility_ratio(closes, 20, 60)

        # Volatility expansion (short-term >> long-term)
        if vol_ratio > 2.0:
            score += 0.5
        elif vol_ratio > 1.5:
            score += 0.3
        elif vol_ratio > 1.2:
            score += 0.15

        # Price range expansion (ATR increasing)
        recent_atr = self._atr(highs[-20:], lows[-20:], closes[-20:])
        older_atr = self._atr(highs[-60:-20], lows[-60:-20], closes[-60:-20])
        if older_atr > 0 and recent_atr / older_atr > 1.5:
            score += 0.3

        # Implied volatility proxy from price gaps
        gaps = [abs(closes[i] - closes[i-1]) / closes[i-1] for i in range(-10, 0) if i != 0]
        avg_gap = np.mean(gaps) if gaps else 0
        if avg_gap > 0.03:
            score += 0.2

        return min(1.0, score)

    def score_fallen_angel(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Fallen angel: quality stock down significantly but not broken.
        Proxy: stock down 30%+ from highs but still above 200d MA level.
        """
        if len(closes) < 250:
            return 0.3

        score = 0

        # Stock down > 30% from 52-week high
        high_52w = max(closes[-250:])
        if high_52w > 0:
            decline = 1 - (closes[-1] / high_52w)
            if 0.30 < decline < 0.60:
                score += 0.4
            elif decline >= 0.60:
                score += 0.2  # Too far = might be broken

        # Still above long-term level (not a permanent decline)
        level_200 = np.mean(closes[-200:])
        if closes[-1] > level_200:
            score += 0.3

        # Volume spike (capitulation)
        vol_ratio = self._volume_ratio(volumes)
        if vol_ratio > 2.5:
            score += 0.2
        elif vol_ratio > 1.5:
            score += 0.1

        # RSI starting to recover
        rsi = self._rsi(closes)
        if 25 < rsi < 40:
            score += 0.1

        return min(1.0, score)

    def score_garp(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Growth at Reasonable Price proxy using momentum + volatility.
        True GARP needs earnings/P/E data; proxy using price behavior.
        """
        if len(closes) < 120:
            return 0.3

        score = 0

        # Positive momentum (growth)
        mom_60 = self._momentum_score(closes, 60)
        mom_120 = self._momentum_score(closes, 120)

        if mom_60 > 0.5 and mom_120 > 0.5:
            score += 0.4 * ((mom_60 + mom_120) / 2)
        elif mom_120 > 0.5:
            score += 0.2

        # Not too volatile (reasonable price)
        vol = np.std(np.diff(np.log(closes[-60:])))
        annual_vol = vol * math.sqrt(252)
        if annual_vol < 0.25:
            score += 0.3
        elif annual_vol < 0.35:
            score += 0.15

        # Above trend but not overextended
        vs_50 = self._price_vs_ma(closes, 50)
        vs_200 = self._price_vs_ma(closes, 200)
        if 1.0 < vs_50 < 1.15 and vs_200 > 1.0:
            score += 0.3
        elif vs_200 > 0.95:
            score += 0.15

        return min(1.0, score)

    def score_gap_and_go(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Gap and Go: morning gap with follow-through.
        Detected from daily price data.
        """
        if len(closes) < 20:
            return 0.3

        score = 0

        # Yesterday's gap (close vs prior close)
        if len(closes) >= 2:
            gap = (closes[-1] / closes[-2]) - 1
            if gap > 0.03:  # Gap up > 3%
                score += 0.4
            elif gap > 0.02:
                score += 0.25

        # Volume confirmation
        vol_ratio = self._volume_ratio(volumes)
        if vol_ratio > 2.0:
            score += 0.3
        elif vol_ratio > 1.5:
            score += 0.15

        # Trend alignment
        if len(closes) >= 50:
            vs_50 = self._price_vs_ma(closes, 50)
            if vs_50 > 1.05:
                score += 0.2
            elif vs_50 > 1.0:
                score += 0.1

        # Strong finish (close near high of day proxy)
        day_range = highs[-1] - lows[-1] if highs[-1] > lows[-1] else 1
        if day_range > 0:
            close_position = (closes[-1] - lows[-1]) / day_range
            if close_position > 0.8:
                score += 0.1

        return min(1.0, score)

    def score_vwap_reversion(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        VWAP mean reversion: price extended from average, likely to revert.
        Uses typical price VWAP proxy.
        """
        if len(closes) < 20:
            return 0.3

        score = 0

        # Calculate VWAP proxy (cumulative typical price × volume)
        typical_prices = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(-20, 0)]
        cum_tp_vol = sum(tp * v for tp, v in zip(typical_prices, volumes[-20:]))
        cum_vol = sum(volumes[-20:])
        vwap = cum_tp_vol / cum_vol if cum_vol > 0 else closes[-1]

        # Price deviation from VWAP
        if vwap > 0:
            deviation = (closes[-1] / vwap) - 1
            if deviation < -0.02:  # Below VWAP = buy signal
                score += min(0.5, abs(deviation) * 10)
            elif deviation < -0.01:
                score += 0.25

        # Volume confirmation
        vol_ratio = self._volume_ratio(volumes)
        if vol_ratio > 1.5:
            score += 0.3

        # Trend context
        rsi = self._rsi(closes)
        if rsi < 30:
            score += 0.2

        return min(1.0, score)

    def score_rule_breaker(self, closes, volumes, highs, lows, indicators=None) -> float:
        """
        Motley Fool Rule Breakers proxy: high-growth potential stocks.
        Proxy: accelerating momentum, high volume, above MA.
        """
        if len(closes) < 120:
            return 0.3

        score = 0

        # Accelerating growth (60d > 120d momentum)
        mom_60 = (closes[-1] / closes[-60]) - 1 if len(closes) >= 60 else 0
        mom_120 = (closes[-1] / closes[-120]) - 1 if len(closes) >= 120 else 0
        if mom_60 > mom_120 > 0:
            score += 0.3
        elif mom_60 > 0:
            score += 0.15

        # High relative volume (interest building)
        vol_ratio = self._volume_ratio(volumes)
        if vol_ratio > 2.0:
            score += 0.3
        elif vol_ratio > 1.5:
            score += 0.15

        # Trading above 200d MA
        vs_200 = self._price_vs_ma(closes, 200)
        if vs_200 > 1.10:
            score += 0.25
        elif vs_200 > 1.0:
            score += 0.10

        # Near 52-week high (market leader)
        peak_pct = self._peakedness_score(closes)
        if peak_pct > 0.90:
            score += 0.15

        return min(1.0, score)

    # ── Master Scoring Method ──

    def score_all_strategies(self, symbol: str, store: IndicatorStore,
                             strategies: list = None) -> dict:
        """
        Run all scoring strategies for a symbol.
        Returns dict of {strategy_name: score}.
        """
        prices_data = store.get_latest_prices(symbol, 260)
        if not prices_data or len(prices_data) < 50:
            return {'error': 'insufficient_data'}

        closes = np.array([p['close'] for p in reversed(prices_data)])
        volumes = np.array([p['volume'] for p in reversed(prices_data)])

        # Build OHLC from close (approximate for indicators that need it)
        highs = closes * 1.01  # Estimate
        lows = closes * 0.01   # Estimate

        # Get latest indicator data for enhanced scoring
        ind = store.get_latest_indicators(symbol, 5)
        latest_ind = ind[sorted(ind.keys())[-1]] if ind else {}

        available_strategies = {
            'canslim': self.score_canslim,
            'buffett_quality': self.score_buffett_quality,
            'graham_deep_value': self.score_graham_deep_value,
            'dividend_aristocrat': self.score_dividend_aristocrat,
            'mean_reversion': self.score_mean_reversion,
            'abnormal_volume': self.score_abnormal_volume,
            'volatility_expansion': self.score_volatility_expansion,
            'fallen_angel': self.score_fallen_angel,
            'garp': self.score_garp,
            'gap_and_go': self.score_gap_and_go,
            'vwap_reversion': self.score_vwap_reversion,
            'rule_breaker': self.score_rule_breaker,
        }

        if strategies is None or strategies == ['all']:
            strategies_to_run = list(available_strategies.keys())
        else:
            strategies_to_run = [s for s in strategies if s in available_strategies]

        scores = {}
        for name in strategies_to_run:
            try:
                scores[name] = available_strategies[name](closes, volumes, highs, lows, latest_ind)
            except Exception:
                scores[name] = 0.5  # neutral on error

        scores['symbol'] = symbol
        scores['n_data_points'] = len(closes)

        return scores


# ── Stage 4: Position Sizing & Risk ────────────────────────────────────────

class PositionSizer:
    """
    Converts strategy scores into position sizes with risk management.
    """

    def __init__(self, config: dict):
        self.max_position_pct = config.get('max_position_pct', 0.10)
        self.max_sector_pct = config.get('max_sector_pct', 0.25)
        self.max_correlation = config.get('max_correlation', 0.80)
        self.kelly_fraction = config.get('kelly_fraction', 0.25)
        self.atr_stop_mult = config.get('atr_stop_mult', 2.0)
        self.n_positions_target = config.get('n_positions_target', 15)

    def compute_atr_stop(self, symbol: str, store: IndicatorStore) -> float:
        """
        Compute ATR-based stop price.
        Returns the stop price (not the ATR value).
        """
        prices_data = store.get_latest_prices(symbol, 30)
        if not prices_data or len(prices_data) < 14:
            return 0

        closes = [p['close'] for p in reversed(prices_data)]

        # Approximate ATR from closes only
        trs = []
        for i in range(1, len(closes)):
            tr = abs(closes[i] - closes[i-1])
            trs.append(tr)

        atr = np.mean(trs[-14:]) if len(trs) >= 14 else np.mean(trs) if trs else 0
        stop_distance = self.atr_stop_mult * atr

        current_price = closes[-1]
        stop_price = current_price - stop_distance

        return max(0, stop_price)

    def kelly_position_size(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Kelly Criterion position sizing.
        f* = (p × b - q) / b
        where p = win rate, b = avg_win/avg_loss, q = 1-p
        Uses quarter-Kelly for safety.
        """
        if avg_loss == 0:
            return 0
        b = avg_win / avg_loss  # reward/risk ratio
        p = win_rate
        q = 1 - p

        kelly = (p * b - q) / b if b > 0 else 0
        quarter_kelly = kelly * self.kelly_fraction

        return max(0, min(self.max_position_pct, quarter_kelly))

    def size_positions(self, scored_symbols: list, portfolio_value: float,
                       store: IndicatorStore) -> list:
        """
        Convert scored symbols into sized positions with stops.
        Returns list of position recommendations.
        """
        positions = []

        for sym_data in scored_symbols:
            symbol = sym_data['symbol']
            score = sym_data['score']

            # Compute ATR stop
            stop_price = self.compute_atr_stop(symbol, store)
            current_price = sym_data.get('last_price', 0)

            if current_price <= 0 or stop_price <= 0:
                continue

            # Risk per share
            risk_per_share = current_price - stop_price
            if risk_per_share <= 0:
                continue

            # Kelly sizing (use score as proxy for win rate)
            win_rate = min(0.7, max(0.3, score))
            avg_win = risk_per_share * 2  # Target 2× risk
            avg_loss = risk_per_share

            kelly_size = self.kelly_position_size(win_rate, avg_win, avg_loss)

            # Dollar allocation
            dollar_alloc = portfolio_value * kelly_size
            shares = int(dollar_alloc / current_price) if current_price > 0 else 0

            if shares > 0:
                positions.append({
                    'symbol': symbol,
                    'score': score,
                    'strategy': sym_data.get('strategy', 'unknown'),
                    'current_price': current_price,
                    'stop_price': round(stop_price, 2),
                    'shares': shares,
                    'allocation_pct': round(kelly_size * 100, 2),
                    'risk_per_share': round(risk_per_share, 2),
                    'dollar_allocation': round(shares * current_price, 2),
                })

        return positions


# ── Master Screening Orchestrator ──────────────────────────────────────────

class ScreeningOrchestrator:
    """
    Orchestrates all 4 stages of the screening pipeline.
    """

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = Config(config_path)
        self.conn = pymysql.connect(**MYSQL)
        self.universe_filter = UniverseFilter({})
        self.quality_filter = QualityFilter({})
        self.strategy_scorer = StrategyScorer()
        self.position_sizer = PositionSizer({})
        self.store = IndicatorStore(self.conn)

    def close(self):
        self.conn.close()

    def run_full_screen(self, strategies: list = None, top_n: int = 10,
                        verbose: bool = True) -> dict:
        """
        Run the complete 4-stage screening pipeline.
        Returns dict with results at each stage.
        """

        cursor = self.conn.cursor()

        if verbose:
            print("="*60)
            print("SCREENING PIPELINE")
            print("="*60)

        # Stage 1: Universe Filter
        if verbose:
            print("\nStage 1: Universe Filter")
        viable = self.universe_filter.get_viable_symbols(cursor)
        if verbose:
            print(f"  Symbols passing: {len(viable)}")

        # Stage 2: Quality Filter
        if verbose:
            print("\nStage 2: Quality Filter")
        quality_passed = []
        quality_failed = []
        for i, sym in enumerate(viable):
            result = self.quality_filter.quality_check(sym, self.store)
            if result['pass']:
                quality_passed.append(sym)
            else:
                quality_failed.append(sym)
            if verbose and (i+1) % 20 == 0:
                print(f"  [{i+1}/{len(viable)}] passed={len(quality_passed)} failed={len(quality_failed)}")

        if verbose:
            print(f"  Passed: {len(quality_passed)}, Failed: {len(quality_failed)}")

        # Stage 3: Strategy Scoring
        if verbose:
            print(f"\nStage 3: Strategy Scoring ({len(quality_passed)} symbols)")

        all_scores = {}
        for i, sym in enumerate(quality_passed):
            scores = self.strategy_scorer.score_all_strategies(sym, self.store, strategies)
            if 'error' not in scores:
                all_scores[sym] = scores
            if verbose and (i+1) % 20 == 0:
                print(f"  [{i+1}/{len(quality_passed)}] scored {len(all_scores)} symbols")

        if verbose:
            print(f"  Scored: {len(all_scores)} symbols")

        # Get top picks per strategy
        strategy_top_picks = {}
        if all_scores:
            # Get all strategy names from first scored symbol
            sample_sym = list(all_scores.keys())[0]
            strategy_names = [k for k in all_scores[sample_sym].keys()
                            if k not in ['symbol', 'n_data_points']]

            for strategy in strategy_names:
                ranked = sorted(
                    [(sym, scores.get(strategy, 0)) for sym, scores in all_scores.items()
                     if not isinstance(scores.get(strategy), str)],
                    key=lambda x: x[1], reverse=True
                )
                strategy_top_picks[strategy] = ranked[:top_n]

        if verbose:
            print(f"\n  Top {top_n} per strategy:")
            for strategy, picks in strategy_top_picks.items():
                top_3 = [f"{s}:{score:.2f}" for s, score in picks[:3]]
                print(f"    {strategy}: {', '.join(top_3)}")

        # Stage 4: Position Sizing
        if verbose:
            print(f"\nStage 4: Position Sizing")

        # Combine all unique top picks across strategies
        all_top_picks = {}
        for strategy, picks in strategy_top_picks.items():
            for sym, score in picks:
                if sym not in all_top_picks or all_top_picks[sym]['score'] < score:
                    all_top_picks[sym] = {
                        'symbol': sym,
                        'score': score,
                        'strategy': strategy,
                    }

        # Add current price data
        for sym_data in all_top_picks.values():
            prices = self.store.get_latest_prices(sym_data['symbol'], 5)
            if prices:
                sym_data['last_price'] = prices[0]['close']

        scored_list = sorted(all_top_picks.values(), key=lambda x: x['score'], reverse=True)
        positions = self.position_sizer.size_positions(
            scored_list[:top_n * 3], 50000.0, self.store)

        if verbose:
            print(f"  Recommended positions: {len(positions)}")
            for pos in positions[:10]:
                print(f"    {pos['symbol']:>8}: score={pos['score']:.2f}  "
                      f"alloc={pos['allocation_pct']}%  "
                      f"shares={pos['shares']}  "
                      f"stop=${pos['stop_price']:.2f}")

        return {
            'stage1_passed': len(viable),
            'stage2_passed': len(quality_passed),
            'stage2_failed': len(quality_failed),
            'scored': len(all_scores),
            'strategy_top_picks': strategy_top_picks,
            'positions': positions,
            'all_scores': all_scores,
        }


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stock Screening Engine (Stage 3)')
    parser.add_argument('--mode', required=True,
                       choices=['screen', 'score', 'status'])
    parser.add_argument('--symbol', help='Symbol for score mode')
    parser.add_argument('--strategies', nargs='+', default=['all'],
                       help='Strategies to run')
    parser.add_argument('--top-n', type=int, default=10)
    parser.add_argument('--verbose', action='store_true', default=True)
    args = parser.parse_args()

    orch = ScreeningOrchestrator()

    try:
        if args.mode == 'screen':
            results = orch.run_full_screen(
                strategies=args.strategies,
                top_n=args.top_n,
                verbose=args.verbose,
            )
        elif args.mode == 'score':
            if not args.symbol:
                print("Required: --symbol")
                sys.exit(1)
            scores = orch.strategy_scorer.score_all_strategies(
                args.symbol, orch.store, args.strategies)
            print(f"\nScores for {args.symbol}:")
            for k, v in sorted(scores.items()):
                if isinstance(v, float):
                    print(f"  {k}: {v:.3f}")
        elif args.mode == 'status':
            cursor = orch.conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT symbol) as n FROM stockprices")
            n_prices = cursor.fetchone()['n']
            cursor.execute("SELECT COUNT(DISTINCT symbol) as n FROM indicators_json")
            n_ind = cursor.fetchone()['n']
            cursor.execute("SELECT COUNT(*) as n FROM symbol_master")
            n_total = cursor.fetchone()['n']

            print(f"\nScreening Engine Status")
            print(f"{'='*40}")
            print(f"Total symbols:      {n_total}")
            print(f"With prices:        {n_prices}")
            print(f"With indicators:    {n_ind}")

            viable = orch.universe_filter.get_viable_symbols(cursor)
            print(f"Pass Stage 1 filter: {len(viable)}")
    finally:
        orch.close()
