"""Concrete advisor strategies with real selection logic."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from advisors.base import AdvisorBase, Signal

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "buffett": {
        "min_market_cap": 10_000_000_000,
        "min_roe": 15.0,
        "max_debt_ratio": 50.0,
        "lookback_days": 365,
    },
    "dividend_growth": {
        "min_yield": 2.0,
        "max_yield": 6.0,
        "max_payout_ratio": 60.0,
        "min_consecutive_years": 5,
        "lookback_days": 365 * 3,
    },
    "momentum": {
        "lookback_days": 252,
        "momentum_window": 20,
        "min_price": 5.0,
        "min_volume": 200_000,
        "max_positions": 15,
    },
}


class BuffettQualityStrategy(AdvisorBase):
    name = "Buffett Quality"
    slug = "buffett_quality"

    def _buffett_cfg(self) -> dict[str, Any]:
        raw = self.config.get("buffett") or {}
        if not raw:
            return _DEFAULTS["buffett"]
        return {**_DEFAULTS["buffett"], **raw}

    def select_universe(self, run_date: date) -> list[str]:
        cfg = self._buffett_cfg()
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT f.symbol
                FROM {self._t('fundamentals')} f
                INNER JOIN (
                    SELECT symbol, MAX(fetch_date) AS max_fd
                    FROM {self._t('fundamentals')}
                    GROUP BY symbol
                ) latest ON latest.symbol = f.symbol AND latest.max_fd = f.fetch_date
                WHERE f.roe IS NOT NULL
                  AND f.debt_to_equity IS NOT NULL
                  AND f.market_cap >= %s
                  AND f.roe >= %s
                  AND f.debt_to_equity <= %s
                  AND EXISTS (
                      SELECT 1 FROM {self._t('stockprices')} p
                      WHERE p.symbol = f.symbol AND p.price_date <= %s
                  )
                GROUP BY f.symbol
                """,
                (
                    cfg["min_market_cap"],
                    cfg["min_roe"],
                    cfg["max_debt_ratio"],
                    run_date,
                ),
            )
            return [r["symbol"] for r in cur.fetchall()]

    def score(self, symbol: str, run_date: date) -> float:
        cfg = self._buffett_cfg()
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT roe, debt_to_equity, market_cap, gross_margin
                FROM {self._t('fundamentals')}
                WHERE symbol = %s
                  AND fetch_date >= %s
                ORDER BY fetch_date DESC
                LIMIT 1
                """,
                (symbol, run_date - timedelta(days=cfg["lookback_days"])),
            )
            row = cur.fetchone()
        if not row:
            return 0.0
        score = 0.0
        score += min(row["roe"] or 0, 30.0) * 2.0
        score += max(0.0, 100.0 - (row["debt_to_equity"] or 100.0)) * 0.5
        if row.get("market_cap"):
            score += 10.0
        if row.get("gross_margin"):
            score += row["gross_margin"] * 1.0
        return score

    def generate_signals(self, run_date: date, max_positions: int = 20) -> list[Signal]:
        max_positions = min(int(self.config.get("max_positions", 6)), 6)
        signals = super().generate_signals(run_date, max_positions=max_positions)
        if not signals:
            return signals
        weight = max(0.10, 0.5 / max_positions)
        total_weight = weight * len(signals)
        if total_weight > 0.5 and len(signals) > 1:
            weight = 0.5 / len(signals)
        for sig in signals:
            sig.weight = weight
        return signals


class DividendGrowthStrategy(AdvisorBase):
    name = "Dividend Growth"
    slug = "dividend_growth"

    def select_universe(self, run_date: date) -> list[str]:
        cfg = {**_DEFAULTS["dividend_growth"], **self.config}
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT f.symbol
                FROM {self._t('fundamentals')} f
                WHERE f.fetch_date >= %s
                  AND f.dividend_yield IS NOT NULL
                  AND f.dividend_yield BETWEEN %s AND %s
                """,
                (
                    run_date - timedelta(days=cfg["lookback_days"]),
                    cfg["min_yield"],
                    cfg["max_yield"],
                ),
            )
            return [r["symbol"] for r in cur.fetchall()]

    def score(self, symbol: str, run_date: date) -> float:
        cfg = {**_DEFAULTS["dividend_growth"], **self.config}
        earliest = run_date - timedelta(days=cfg["lookback_days"])
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT amount, ex_date
                FROM {self._t('dividends')}
                WHERE symbol = %s AND ex_date BETWEEN %s AND %s
                ORDER BY ex_date DESC
                """,
                (symbol, earliest, run_date),
            )
            rows = cur.fetchall()
        if not rows:
            return 0.0
        years: dict[int, float] = {}
        for r in rows:
            y = r["ex_date"].year
            years[y] = years.get(y, 0.0) + float(r["amount"])
        unique_years = sorted(years.items(), reverse=True)
        if len(unique_years) < cfg["min_consecutive_years"]:
            return 0.0
        consecutive = 0
        prev = None
        for _, total in unique_years:
            if prev is not None and total <= prev:
                break
            consecutive += 1
            prev = total
        if consecutive < cfg["min_consecutive_years"]:
            return 0.0
        base = float(unique_years[0][1]) / float(unique_years[-1][1] or 1)
        return 50.0 + (base * 30.0) + (consecutive * 2.0)


class MomentumStrategy(AdvisorBase):
    name = "Momentum"
    slug = "momentum"

    def select_universe(self, run_date: date) -> list[str]:
        cfg = {**_DEFAULTS["momentum"], **self.config}
        start = run_date - timedelta(days=cfg["lookback_days"])
        cutoff = run_date - timedelta(days=cfg["momentum_window"])
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT symbol,
                       MIN(close) AS older,
                       MAX(close) AS newer,
                       AVG(volume) AS avg_volume
                FROM {self._t('stockprices')}
                WHERE price_date BETWEEN %s AND %s
                GROUP BY symbol
                HAVING avg_volume >= %s
                   AND newer >= %s
                """,
                (start, cutoff, cfg["min_volume"], cfg["min_price"]),
            )
            return [r["symbol"] for r in cur.fetchall()]

    def score(self, symbol: str, run_date: date) -> float:
        cfg = {**_DEFAULTS["momentum"], **self.config}
        start = run_date - timedelta(days=cfg["lookback_days"])
        cutoff = run_date - timedelta(days=cfg["momentum_window"])
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT close
                FROM {self._t('stockprices')}
                WHERE symbol = %s AND price_date BETWEEN %s AND %s
                ORDER BY price_date ASC
                """,
                (symbol, start, cutoff),
            )
            rows = [float(r["close"]) for r in cur.fetchall()]
        if len(rows) < 2:
            return 0.0
        momentum = (rows[-1] - rows[0]) / rows[0] * 100.0
        return max(momentum, 0.0)


# ------------------------------------------------------------------
# Sector / balanced / bond strategies
# ------------------------------------------------------------------

# Maps screener sector names -> low-cost TSX ETF symbol where available.
# ETFs are the preferred pick; unknown sectors fall back to stock screening.
SECTOR_ETF_MAP: dict[str, str | None] = {
    "Finance": "XFN.TO",
    "Energy Minerals": "XEG.TO",
    "Electronic Technology": "XIT.TO",
    "Technology Services": "XIT.TO",
    "Health Technology": "XIC.TO",  # broad proxy; no dedicated health-tech ETF in universe yet
    "Non-Energy Minerals": "XMA.TO",
    "Real Estate": "XRE.TO",
    # Broad proxies for sectors without a pure ETF:
    "Industrial Services": "XIC.TO",
    "Producer Manufacturing": "XIC.TO",
    "Process Industries": "XIC.TO",
    "Transportation": "XIC.TO",
    "Retail Trade": "XIC.TO",
    "Consumer Non-Durables": "XIC.TO",
    "Consumer Durables": "XIC.TO",
    "Health Services": "XIC.TO",
    "Communication Services": "XIC.TO",
    "Miscellaneous": "XIC.TO",
    # US-only sectors handled via same broad proxies or skipped
    "Distribution Services": "XIC.TO",
    "Commercial Services": "XIC.TO",
    "Consumer Services": "XIC.TO",
    "Utilities": "XIC.TO",
}

_SCREENER_TO_FUNDAMENTALS: dict[str, str | None] = {
    "Finance": "Financial Services",
    "Energy Minerals": "Energy",
    "Electronic Technology": "Technology",
    "Technology Services": "Technology",
    "Health Technology": "Healthcare",
    "Health Services": "Healthcare",
    "Non-Energy Minerals": "Basic Materials",
    "Process Industries": "Industrials",
    "Producer Manufacturing": "Industrials",
    "Industrial Services": "Industrials",
    "Retail Trade": "Consumer Cyclical",
    "Consumer Non-Durables": "Consumer Defensive",
    "Consumer Durables": "Consumer Cyclical",
    "Transportation": "Industrials",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Communication Services": "Communication Services",
    "Miscellaneous": None,
    "Distribution Services": "Industrials",
    "Commercial Services": "Industrials",
    "Consumer Services": "Consumer Cyclical",
}


class SectorStrategy(AdvisorBase):
    name = "Sector"
    slug = "sector"

    def select_universe(self, run_date: date) -> list[str]:
        sector = self.config.get("sector", "")
        if not sector:
            return []
        symbols: list[str] = []
        etf = SECTOR_ETF_MAP.get(sector)
        if etf:
            symbols.append(etf)
        fund_sector = _SCREENER_TO_FUNDAMENTALS.get(sector)
        if fund_sector:
            start = run_date - timedelta(days=365)
            with self.db.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT DISTINCT f.symbol
                    FROM {self._t('fundamentals')} f
                    LEFT JOIN {self._t('stockprices')} p
                      ON p.symbol = f.symbol AND p.price_date <= %s
                    WHERE f.sector = %s
                      AND f.fetch_date >= %s
                      AND p.symbol IS NOT NULL
                    ORDER BY f.symbol
                    LIMIT 40
                    """,
                    (run_date, fund_sector, start),
                )
                symbols.extend(r["symbol"] for r in cur.fetchall())
        seen: set[str] = set()
        deduped: list[str] = []
        for s in symbols:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        return deduped

    def score(self, symbol: str, run_date: date) -> float:
        sector = self.config.get("sector", "")
        etf = SECTOR_ETF_MAP.get(sector)
        if symbol == etf:
            return 100.0
        start = run_date - timedelta(days=365)
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT market_cap FROM {self._t('fundamentals')}
                WHERE symbol = %s AND fetch_date >= %s
                ORDER BY fetch_date DESC LIMIT 1
                """,
                (symbol, start),
            )
            row = cur.fetchone()
            mc = float(row["market_cap"] or 0)
        return mc if mc > 0 else 0.1


class BondBasketStrategy(AdvisorBase):
    name = "Bond Basket"
    slug = "bond_basket"

    def select_universe(self, run_date: date) -> list[str]:
        return ["TBIL.TO", "ZGB.TO", "HMP.TO", "ZAG.TO"]

    def score(self, symbol: str, run_date: date) -> float:
        return 1.0


class BalancedFundStrategy(AdvisorBase):
    name = "Balanced Fund"
    slug = "balanced_fund"

    def select_universe(self, run_date: date) -> list[str]:
        equity = self.config.get("equity", "XIC.TO")
        basket = BondBasketStrategy(
            self.db, config={"table_prefix": self.table_prefix}
        )
        bond_symbols = basket.select_universe(run_date)
        return [equity] + bond_symbols

    def score(self, symbol: str, run_date: date) -> float:
        equity = self.config.get("equity", "XIC.TO")
        return 100.0 if symbol == equity else 1.0

    def generate_signals(self, run_date: date, max_positions: int = 20) -> list[Signal]:
        equity = self.config.get("equity", "XIC.TO")
        basket = BondBasketStrategy(
            self.db, config={"table_prefix": self.table_prefix}
        )
        bond_symbols = basket.select_universe(run_date)
        if not bond_symbols:
            return []
        weight_per_bond = 0.4 / len(bond_symbols)
        signals: list[Signal] = [
            Signal(
                symbol=equity,
                action="BUY",
                weight=0.6,
                reason="equity 60%",
                confidence=0.8,
            )
        ]
        for sym in bond_symbols:
            signals.append(
                Signal(
                    symbol=sym,
                    action="BUY",
                    weight=weight_per_bond,
                    reason="bond basket 40%",
                    confidence=0.7,
                )
            )
        return signals


class VectorVestSafeStockStrategy(AdvisorBase):
    """Safe Stock Selector — VectorVest 5-point checklist advisor.

    Criteria:
      1. Smooth & steady price uptrend over 1 year (linear regression slope > 0, R² >= threshold).
      2. Price currently rising (close > close 20 trading days ago).
      3. Earnings rising (forward_eps positive or earnings_growth > 0).
      4. Market on your side (SPY 20-day trend positive).
      5. Follow-through confirmed (today close > today open and > yesterday close).
    """

    name = "VectorVest Safe Stock"
    slug = "vectorvest_safe"

    _DEFAULTS = {
        "smooth_r2_min": 0.55,
        "min_price_days": 200,
        "market_symbol": "SPY",
    }

    def _smooth_uptrend(self, closes: list[float]) -> tuple[bool, float, float]:
        n = len(closes)
        if n < 2:
            return False, 0.0, 0.0
        x = list(range(n))
        y = closes
        sx = sum(x)
        sy = sum(y)
        sxy = sum(a * b for a, b in zip(x, y))
        sxx = sum(a * a for a in x)
        den = n * sxx - sx * sx
        if den == 0:
            return False, 0.0, 0.0
        slope = (n * sxy - sx * sy) / den
        intercept = (sy - slope * sx) / n
        ss_res = sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((yi - sy / n) ** 2 for yi in y)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        cfg = {**self._DEFAULTS, **self.config}
        return slope > 0 and r2 >= cfg["smooth_r2_min"], slope, r2

    def select_universe(self, run_date: date) -> list[str]:
        cfg = {**self._DEFAULTS, **self.config}
        start = run_date - timedelta(days=cfg["min_price_days"] + 60)
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT DISTINCT symbol
                FROM {self._t('stockprices')}
                WHERE price_date >= %s
                GROUP BY symbol
                HAVING COUNT(*) >= %s
                """,
                (str(start), cfg["min_price_days"]),
            )
            return [r["symbol"] for r in cur.fetchall()]

    def score(self, symbol: str, run_date: date) -> float:
        cfg = {**self._DEFAULTS, **self.config}
        start = run_date - timedelta(days=cfg["min_price_days"] + 60)

        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT price_date, open, high, low, close, volume
                FROM {self._t('stockprices')}
                WHERE symbol = %s AND price_date >= %s
                ORDER BY price_date ASC
                """,
                (symbol, str(start)),
            )
            rows = cur.fetchall()

        if not rows or len(rows) < cfg["min_price_days"]:
            return 0.0

        closes = [float(r["close"]) for r in rows]
        today = rows[-1]
        yesterday = rows[-2] if len(rows) > 1 else None

        # 1) Smooth uptrend
        smooth_ok, _, _ = self._smooth_uptrend(closes)

        # 2) Price rising
        price_rising = len(closes) > 20 and closes[-1] > closes[-21]

        # 3) Earnings rising
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT forward_eps, earnings_growth, trailing_eps
                FROM {self._t('fundamentals')}
                WHERE symbol = %s
                ORDER BY fetch_date DESC
                LIMIT 1
                """,
                (symbol,),
            )
            fund = cur.fetchone()
        earnings_rising = False
        if fund:
            fwd = fund.get("forward_eps")
            eg = fund.get("earnings_growth")
            if fwd is not None and float(fwd) > 0:
                earnings_rising = True
            elif eg is not None and float(eg) > 0:
                earnings_rising = True
            elif fund.get("trailing_eps") is not None and float(fund["trailing_eps"]) > 0:
                earnings_rising = True

        # 4) Market on your side
        market_ok = self._market_trend(run_date)

        # 5) Follow-through
        follow_through = False
        if today and yesterday:
            c = float(today["close"])
            o = float(today["open"])
            yc = float(yesterday["close"])
            follow_through = c > o and c > yc

        pass_count = sum([
            1 if smooth_ok else 0,
            1 if price_rising else 0,
            1 if earnings_rising else 0,
            1 if market_ok else 0,
            1 if follow_through else 0,
        ])
        return float(pass_count)

    def _market_trend(self, run_date: date) -> bool:
        cfg = {**self._DEFAULTS, **self.config}
        start = run_date - timedelta(days=40)
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT close FROM {self._t('stockprices')}
                WHERE symbol = %s AND price_date BETWEEN %s AND %s
                ORDER BY price_date ASC
                """,
                (cfg["market_symbol"], str(start), str(run_date)),
            )
            rows = cur.fetchall()
        if not rows or len(rows) < 20:
            return True
        closes = [float(r["close"]) for r in rows]
        return closes[-1] > closes[-21] if len(closes) > 21 else closes[-1] > closes[0]

    def generate_signals(self, run_date: date, max_positions: int = 20) -> list[Signal]:
        universe = self.select_universe(run_date)
        if not universe:
            return []
        scored: list[tuple[str, float, bool]] = []
        for symbol in universe:
            try:
                s = self.score(symbol, run_date)
            except Exception:
                continue
            if s >= 4.0:
                scored.append((symbol, s, True))
            elif s > 0:
                scored.append((symbol, s, False))
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = scored[:max_positions]
        signals: list[Signal] = []
        for rank, (symbol, score, passed) in enumerate(selected, start=1):
            signals.append(
                Signal(
                    symbol=symbol,
                    action="BUY",
                    weight=1.0 / max_positions,
                    reason=f"vv pass={int(score)}/5 rank={rank}",
                    confidence=min(score / 5.0, 1.0) if passed else score / 5.0 * 0.6,
                    meta={"rank": rank, "pass_count": int(score), "passed": passed},
                )
            )
        return signals
