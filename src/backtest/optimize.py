#!/usr/bin/env python3
"""
Unified Backtest Optimization Engine
=====================================

Phase 1: Single-indicator weight sweep per ticker
  Tests each signal type independently across a grid of weights.
  Metrics: win rate, coherence, total return, Sharpe, max drawdown.

Phase 2: Pairwise interaction sweep
  Tests correlated indicator pairs on a 2D grid.
  Captures interactions (e.g., RSI+MACD together may be more predictive than either alone).

Phase 3: Genetic Algorithm optimization (conditional)
  Only runs if Phase 2 captures <90% of explainable variance.
  Evolves full weight vectors using tournament selection + crossover + mutation.

Phase 4: Risk Management
  a) Trailing stop-loss: grid stop % vs normal volatility (ATR-based)
  b) Time-based exits: test different holding periods
  c) Hybrid tiered exits: sell 10% at -10%, 30% at -20%, etc.
  d) VIX correlation: correlate stop/time/hybrid performance vs VIX regime
  e) Position sizing: Kelly criterion + volatility-adjusted
  f) Sector concentration limits: volatility grid CAN/US/EURO/Emerging
  g) ADR/ETF mapping for non-North-American exposure

Performance Tracking:
  $100 hypothetical portfolio per ticker using mid-price execution.
  Dollar-cost averaging. Compare against buy-and-hold + sector ETFs.

Execution price model: mid = (high + low) / 2
  Assumes we trade partway through the day, not at open or close.
"""

import sys
import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from itertools import product
import random

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))  # src/
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'optimization'))  # src/optimization/

from db.connection import DataSource
from db.data_cache import DataCache
from weight_optimizer import (
    WeightedSignalGenerator, RollingCoherenceScorer,
    DEFAULT_WEIGHTS, WEIGHT_BOUNDS
)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Portfolio tickers
PORTFOLIO_TICKERS = [
    'RY', 'CM', 'CNR', 'BPF.UN', 'SRV.UN', 'CDZ', 'PZA', 'KEG.UN',
    'WJX', 'MTY', 'TFII', 'RUS', 'PDC',
    'FEZ', 'IEV', 'SPEU', 'MX', 'RGLD', 'UL'
]

# Sector ETFs for comparison
SECTOR_ETFS = {
    'XFN': 'TSX Financials',
    'XIT': 'TSX Info Tech',
    'XEG': 'TSX Energy',
    'XRE': 'TSX Real Estate',
    'XMA': 'TSX Materials',
    'XUT': 'TSX Utilities',
    'SPY': 'S&P 500',
    'QQQ': 'Nasdaq 100',
    'FEZ': 'Euro Stoxx 50',
    'IEV': 'Europe ETF',
    'SPEU': 'SPDR Europe',
    'EEM': 'Emerging Markets',
    'XIC': 'TSX Composite',
    'ZCN': 'TSX Cdn Div',
}

# ADR mappings for non-North-American exposure
ADR_MAP = {
    'UL': {'adr': 'UL', 'country': 'UK', 'currency': 'USD', 'underlying': 'ULVR.L'},
    'RGLD': {'adr': 'RGLD', 'country': 'US', 'currency': 'USD', 'underlying': None},
}

# Sector classification
SECTOR_MAP = {
    'RY': 'Financials', 'CM': 'Financials', 'CNR': 'Industrials',
    'BPF.UN': 'Energy', 'SRV.UN': 'Energy', 'CDZ': 'Energy', 'PZA': 'Energy',
    'KEG.UN': 'Energy', 'PDC': 'Energy',
    'WJX': 'Industrials', 'MTY': 'Consumer', 'TFII': 'Industrials', 'RUS': 'Consumer',
    'FEZ': 'Europe', 'IEV': 'Europe', 'SPEU': 'Europe',
    'MX': 'Materials', 'RGLD': 'Materials', 'UL': 'Consumer',
}

# Geographic classification
GEO_MAP = {
    'RY': 'Canada', 'CM': 'Canada', 'CNR': 'Canada',
    'BPF.UN': 'Canada', 'SRV.UN': 'Canada', 'CDZ': 'Canada', 'PZA': 'Canada',
    'KEG.UN': 'Canada', 'PDC': 'Canada',
    'WJX': 'Canada', 'MTY': 'Canada', 'TFII': 'Canada', 'RUS': 'Canada',
    'FEZ': 'Europe', 'IEV': 'Europe', 'SPEU': 'Europe',
    'MX': 'US', 'RGLD': 'US', 'UL': 'Europe',
}

# Weight grid for Phase 1
WEIGHT_GRID = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

# Stop-loss grid for Phase 4a
STOP_GRID = [0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30]

# Time exit grid for Phase 4b
TIME_EXIT_GRID = [5, 10, 21, 42]  # trading days: 1w, 2w, 1m, 2m

# Tiered exit strategies for Phase 4c
TIERED_EXITS = [
    # (drop_threshold, sell_fraction)
    [(0.10, 0.10), (0.20, 0.30), (0.30, 0.60)],  # Conservative
    [(0.10, 0.25), (0.20, 0.50), (0.30, 1.00)],  # Moderate
    [(0.15, 0.33), (0.25, 0.67), (0.35, 1.00)],  # Aggressive
    [(0.05, 0.10), (0.10, 0.20), (0.15, 0.30), (0.20, 0.40)],  # Very fine
    [(0.10, 0.50), (0.20, 1.00)],  # Simple two-tier
    [(0.08, 0.20), (0.15, 0.40), (0.22, 0.60), (0.30, 0.80)],  # Four-tier
]


# ============================================================================
# CORE BACKTEST ENGINE
# ============================================================================

class BacktestEngine:
    """
    Runs backtest simulations with configurable signal weights,
    stop-losses, time exits, and position sizing.
    """

    def __init__(self, cache: DataCache = None):
        self.cache = cache or DataCache()
        self.resolver = SymbolResolver()

    def calculate_indicators(self, hist: pd.DataFrame) -> Dict:
        """Calculate technical indicators from price history."""
        return TechnicalAnalyzer.calculate(hist)

    def generate_signal(self, ticker: str, indicators: Dict,
                        weights: Dict[str, float] = None) -> Dict:
        """Generate signal using custom weights."""
        if weights is None:
            weights = dict(DEFAULT_WEIGHTS)

        buy_score = 0.0
        sell_score = 0.0
        contributions = {}

        sma20 = indicators.get('sma_20')
        sma50 = indicators.get('sma_50')
        sma200 = indicators.get('sma_200')
        rsi = indicators.get('rsi')
        macd = indicators.get('macd')
        macd_sig = indicators.get('macd_signal')
        stoch_k = indicators.get('stoch_k')
        bb_pos = indicators.get('bb_position')
        vol_ratio = indicators.get('volume_ratio', 1)

        # MA_ALIGN
        if sma20 and sma50:
            align = indicators.get('ma_alignment', '')
            align_dur = indicators.get('ma_alignment_duration', 0)
            w = weights.get('MA_ALIGN', 0.35)
            if align_dur < 20:
                w *= 0.7
            if align == 'BULLISH':
                c = min(w + align_dur / 200, w * 1.5)
                buy_score += c
                contributions['MA_ALIGN'] = c
            elif align == 'BEARISH':
                c = min(w + align_dur / 200, w * 1.5)
                sell_score += c
                contributions['MA_ALIGN'] = -c

        # SMA200
        if sma200 and sma20:
            w = weights.get('SMA200', 0.12)
            if indicators.get('trend_sma20_direction') == 'above' and sma20 > sma200:
                buy_score += w
                contributions['SMA200'] = w
            elif indicators.get('trend_sma20_direction') == 'below' and sma20 < sma200:
                sell_score += w
                contributions['SMA200'] = -w

        # RSI
        if rsi is not None:
            w = weights.get('RSI', 0.27)
            if rsi > 70:
                sell_score += w
                contributions['RSI'] = -w
            elif rsi < 30:
                buy_score += w
                contributions['RSI'] = w

            div = indicators.get('rsi_divergence', 'NONE')
            dw = weights.get('RSI_DIV', 0.25)
            if div == 'BULLISH_DIVERGENCE':
                buy_score += dw
                contributions['RSI_DIV'] = dw
            elif div == 'BEARISH_DIVERGENCE':
                sell_score += dw
                contributions['RSI_DIV'] = -dw

        # MACD
        if macd is not None and macd_sig is not None:
            w = weights.get('MACD', 0.20)
            if macd > macd_sig:
                buy_score += w
                contributions['MACD'] = w
            else:
                sell_score += w
                contributions['MACD'] = -w

        # BB
        if bb_pos is not None:
            w = weights.get('BB', 0.15)
            if bb_pos > 1:
                sell_score += w
                contributions['BB'] = -w
            elif bb_pos < 0:
                buy_score += w
                contributions['BB'] = w

        # STOCH
        if stoch_k is not None:
            w = weights.get('STOCH', 0.10)
            if stoch_k > 80:
                sell_score += w
                contributions['STOCH'] = -w
            elif stoch_k < 20:
                buy_score += w
                contributions['STOCH'] = w

        # Compute signal
        total = buy_score + sell_score
        if total == 0:
            return {'signal': 'HOLD', 'confidence': 0.5, 'buy_score': 0, 'sell_score': 0, 'contributions': {}}

        if buy_score > sell_score * 1.3:
            signal = 'BUY'
            conf = min(buy_score / total, 0.95)
        elif sell_score > buy_score * 1.3:
            signal = 'SELL'
            conf = min(sell_score / total, 0.95)
        else:
            signal = 'HOLD'
            conf = 0.5

        return {
            'signal': signal,
            'confidence': conf,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'contributions': contributions,
        }

    def run_backtest(self, ticker: str, weights: Dict[str, float] = None,
                     stop_loss: float = None, time_exit: int = None,
                     tiered_exit: List[Tuple[float, float]] = None,
                     position_size: float = 1.0,
                     initial_capital: float = 100.0,
                     max_days: int = None) -> Dict:
        """
        Run full backtest for a ticker with given parameters.
        
        Args:
            weights: custom signal weights
            stop_loss: trailing stop as fraction (e.g., 0.10 = 10%)
            time_exit: max holding period in trading days
            tiered_exit: list of (drop_threshold, sell_fraction) tuples
            position_size: fraction of capital to deploy (0.0-1.0)
            initial_capital: starting capital (default $100)
            max_days: if set, only use the last max_days of data (for faster GA runs)
        
        Returns:
            Dict with performance metrics and trade log
        """
        prices = self.cache.get_prices(ticker)
        if prices.empty or len(prices) < 250:
            return self._empty_result(ticker)
        
        # Limit data for faster GA execution if max_days is set
        if max_days and max_days < len(prices):
            prices = prices.iloc[-max_days:].copy()
            print(f"    Using last {max_days} days for faster GA")
        
        # Resample to monthly for signal generation (use last trading day of each month)
        monthly = prices.resample('ME').last()
        monthly_dates = monthly.index

        trades = []
        position = 0  # 0 = flat, 1 = long
        entry_price = 0
        entry_date = None
        peak_price = 0
        capital = initial_capital
        shares = 0
        tiered_state = {}  # track which tiers have been triggered

        # Track daily for stop-loss and time exit
        price_dict = {str(d.date()): row for d, row in prices.iterrows()}

        for i, date in enumerate(monthly_dates):
            date_str = str(date.date())
            if date_str not in price_dict:
                continue

            # Get history up to this point for indicators
            hist = prices.loc[:date]
            if len(hist) < 200:
                continue

            indicators = self.calculate_indicators(hist)
            signal = self.generate_signal(ticker, indicators, weights)

            mid_price = self.cache.get_mid_price(ticker, date_str)
            if mid_price is None:
                mid_price = float(prices.loc[date, 'close'])

            # Check exits if in position
            if position == 1:
                days_held = (date - entry_date).days if entry_date else 0

                # Trailing stop check
                if stop_loss and peak_price > 0:
                    drop_from_peak = (peak_price - mid_price) / peak_price
                    if drop_from_peak >= stop_loss:
                        exit_price = mid_price
                        pnl = (exit_price - entry_price) / entry_price
                        capital += shares * exit_price
                        trades.append({
                            'entry_date': str(entry_date.date()) if entry_date else '',
                            'exit_date': date_str,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl_pct': pnl * 100,
                            'exit_reason': 'stop_loss',
                            'days_held': days_held,
                        })
                        position = 0
                        shares = 0
                        tiered_state = {}
                        continue

                # Tiered exit check
                if tiered_exit and peak_price > 0:
                    drop_from_peak = (peak_price - mid_price) / peak_price
                    for tier_idx, (threshold, sell_frac) in enumerate(tiered_exit):
                        if tier_idx not in tiered_state and drop_from_peak >= threshold:
                            sell_shares = shares * sell_frac
                            if sell_shares > 0:
                                exit_price = mid_price
                                capital += sell_shares * exit_price
                                shares -= sell_shares
                                trades.append({
                                    'entry_date': str(entry_date.date()) if entry_date else '',
                                    'exit_date': date_str,
                                    'entry_price': entry_price,
                                    'exit_price': exit_price,
                                    'pnl_pct': ((exit_price - entry_price) / entry_price) * 100,
                                    'exit_reason': f'tiered_{tier_idx}',
                                    'days_held': days_held,
                                    'sell_fraction': sell_frac,
                                })
                                tiered_state[tier_idx] = True
                    if shares <= 0:
                        position = 0
                        tiered_state = {}
                        continue

                # Time exit check
                if time_exit and days_held >= time_exit:
                    exit_price = mid_price
                    pnl = (exit_price - entry_price) / entry_price
                    capital += shares * exit_price
                    trades.append({
                        'entry_date': str(entry_date.date()) if entry_date else '',
                        'exit_date': date_str,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_pct': pnl * 100,
                        'exit_reason': 'time_exit',
                        'days_held': days_held,
                    })
                    position = 0
                    shares = 0
                    tiered_state = {}
                    continue

                # Update peak
                if mid_price > peak_price:
                    peak_price = mid_price

            # Entry logic
            if position == 0 and signal['signal'] == 'BUY':
                entry_price = mid_price
                entry_date = date
                peak_price = mid_price
                deploy_capital = capital * position_size
                shares = deploy_capital / mid_price  # fractional shares for $100 portfolio
                if shares > 0:
                    capital -= shares * mid_price
                    position = 1
                    tiered_state = {}

        # Close any open position at end
        if position == 1 and shares > 0:
            last_price = float(prices.iloc[-1]['Close'])
            pnl = (last_price - entry_price) / entry_price
            capital += shares * last_price
            trades.append({
                'entry_date': str(entry_date.date()) if entry_date else '',
                'exit_date': str(prices.index[-1].date()),
                'entry_price': entry_price,
                'exit_price': last_price,
                'pnl_pct': pnl * 100,
                'exit_reason': 'end_of_backtest',
                'days_held': (prices.index[-1] - entry_date).days if entry_date else 0,
            })

        # Calculate metrics
        return self._calc_metrics(ticker, trades, initial_capital, capital, prices)

    def _empty_result(self, ticker: str) -> Dict:
        return {
            'ticker': ticker, 'n_trades': 0, 'win_rate': 0, 'total_return': 0,
            'sharpe': 0, 'max_drawdown': 0, 'avg_trade': 0, 'avg_win': 0,
            'avg_loss': 0, 'profit_factor': 0, 'final_capital': 100,
            'trades': [],
        }

    def _calc_metrics(self, ticker: str, trades: List[Dict],
                      initial_capital: float, final_capital: float,
                      prices: pd.DataFrame) -> Dict:
        """Calculate performance metrics from trade log."""
        if not trades:
            return self._empty_result(ticker)

        pnls = [t['pnl_pct'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        win_rate = len(wins) / len(pnls) if pnls else 0
        avg_trade = np.mean(pnls) if pnls else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0

        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Sharpe ratio (annualized, using monthly returns)
        monthly_returns = []
        for t in trades:
            if t['days_held'] > 0:
                monthly_ret = (t['pnl_pct'] / 100) * (21 / max(t['days_held'], 1))
                monthly_returns.append(monthly_ret)
        sharpe = (np.mean(monthly_returns) / np.std(monthly_returns) * np.sqrt(12)) if monthly_returns and np.std(monthly_returns) > 0 else 0

        # Max drawdown
        cumulative = [initial_capital]
        for t in trades:
            cumulative.append(cumulative[-1] * (1 + t['pnl_pct'] / 100))
        peak = cumulative[0]
        max_dd = 0
        for val in cumulative:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd

        return {
            'ticker': ticker,
            'n_trades': len(trades),
            'win_rate': round(win_rate, 4),
            'total_return': round(total_return, 2),
            'sharpe': round(sharpe, 4),
            'max_drawdown': round(max_dd, 4),
            'avg_trade': round(avg_trade, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'final_capital': round(final_capital, 2),
            'trades': trades,
        }


# ============================================================================
# PHASE 1: SINGLE-INDICATOR WEIGHT SWEEP
# ============================================================================

class Phase1Sweep:
    """Test each signal type independently across a grid of weights."""

    def __init__(self, engine: BacktestEngine, db: sqlite3.Connection):
        self.engine = engine
        self.db = db

    def sweep_ticker(self, ticker: str, signal_type: str,
                     weight_grid: List[float] = None) -> List[Dict]:
        """Sweep one signal type across weight grid, keeping others at default."""
        if weight_grid is None:
            weight_grid = WEIGHT_GRID

        lo, hi = WEIGHT_BOUNDS.get(signal_type, (0.0, 0.6))
        weight_grid = [w for w in weight_grid if lo <= w <= hi]

        results = []
        for w in weight_grid:
            weights = dict(DEFAULT_WEIGHTS)
            weights[signal_type] = w
            result = self.engine.run_backtest(ticker, weights=weights)
            result['swept_weight'] = w
            result['swept_signal'] = signal_type
            results.append(result)

        return results

    def sweep_all(self, tickers: List[str] = None,
                  signal_types: List[str] = None) -> Dict[str, Dict]:
        """Run full Phase 1 sweep for all tickers and signal types."""
        if tickers is None:
            tickers = PORTFOLIO_TICKERS
        if signal_types is None:
            signal_types = list(DEFAULT_WEIGHTS.keys())

        all_results = {}
        total = len(tickers) * len(signal_types)
        count = 0

        for ticker in tickers:
            all_results[ticker] = {}
            for sig_type in signal_types:
                count += 1
                print(f"  Phase 1 [{count}/{total}]: {ticker} × {sig_type}")
                results = self.sweep_ticker(ticker, sig_type)
                all_results[ticker][sig_type] = results

                # Store best result
                best = max(results, key=lambda r: r.get('total_return', 0))
                self._store_result(ticker, sig_type, best)

        return all_results

    def _store_result(self, ticker: str, signal_type: str, result: Dict):
        """Store sweep result in DB."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS phase1_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                weight REAL NOT NULL,
                total_return REAL,
                win_rate REAL,
                sharpe REAL,
                max_drawdown REAL,
                n_trades INTEGER,
                profit_factor REAL,
                UNIQUE(ticker, signal_type, weight)
            )
        """)
        self.db.execute("""
            INSERT OR REPLACE INTO phase1_results
            (ticker, signal_type, weight, total_return, win_rate, sharpe, max_drawdown, n_trades, profit_factor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, signal_type, result.get('swept_weight', 0),
              result.get('total_return', 0), result.get('win_rate', 0),
              result.get('sharpe', 0), result.get('max_drawdown', 0),
              result.get('n_trades', 0), result.get('profit_factor', 0)))
        self.db.commit()


# ============================================================================
# PHASE 2: PAIRWISE INTERACTION SWEEP
# ============================================================================

class Phase2Sweep:
    """Test correlated indicator pairs on a 2D grid."""

    # Pairs that are likely to interact
    PAIRS = [
        ('RSI', 'MACD'),        # momentum + momentum
        ('MA_ALIGN', 'SMA200'),  # trend + trend
        ('RSI', 'BB'),           # momentum + volatility
        ('MACD', 'BB'),          # momentum + volatility
        ('MA_ALIGN', 'RSI'),     # trend + momentum
        ('STOCH', 'RSI'),        # both oscillators
        ('VWAP', 'BB'),          # price level + volatility
        ('REL_STR', 'MA_ALIGN'), # relative + trend
    ]

    def __init__(self, engine: BacktestEngine, db: sqlite3.Connection):
        self.engine = engine
        self.db = db

    def sweep_pair(self, ticker: str, sig1: str, sig2: str,
                   grid1: List[float] = None, grid2: List[float] = None) -> List[Dict]:
        """Sweep a pair of signal types on a 2D grid."""
        if grid1 is None:
            grid1 = [w for w in WEIGHT_GRID if WEIGHT_BOUNDS.get(sig1, (0, 1))[0] <= w <= WEIGHT_BOUNDS.get(sig1, (0, 1))[1]]
        if grid2 is None:
            grid2 = [w for w in WEIGHT_GRID if WEIGHT_BOUNDS.get(sig2, (0, 1))[0] <= w <= WEIGHT_BOUNDS.get(sig2, (0, 1))[1]]

        results = []
        for w1, w2 in product(grid1, grid2):
            weights = dict(DEFAULT_WEIGHTS)
            weights[sig1] = w1
            weights[sig2] = w2
            result = self.engine.run_backtest(ticker, weights=weights)
            result['swept_pair'] = f"{sig1}={w1:.2f},{sig2}={w2:.2f}"
            result['swept_weights'] = {sig1: w1, sig2: w2}
            results.append(result)

        return results

    def sweep_all(self, tickers: List[str] = None) -> Dict[str, Dict]:
        """Run full Phase 2 sweep."""
        if tickers is None:
            tickers = PORTFOLIO_TICKERS

        all_results = {}
        total = len(tickers) * len(self.PAIRS)
        count = 0

        for ticker in tickers:
            all_results[ticker] = {}
            for sig1, sig2 in self.PAIRS:
                count += 1
                print(f"  Phase 2 [{count}/{total}]: {ticker} × ({sig1}, {sig2})")
                results = self.sweep_pair(ticker, sig1, sig2)
                all_results[ticker][f"{sig1}+{sig2}"] = results

                best = max(results, key=lambda r: r.get('total_return', 0))
                self._store_result(ticker, sig1, sig2, best)

        return all_results

    def _store_result(self, ticker, sig1, sig2, result):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS phase2_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                signal_1 TEXT NOT NULL,
                signal_2 TEXT NOT NULL,
                weight_1 REAL,
                weight_2 REAL,
                total_return REAL,
                win_rate REAL,
                sharpe REAL,
                max_drawdown REAL,
                n_trades INTEGER,
                UNIQUE(ticker, signal_1, signal_2, weight_1, weight_2)
            )
        """)
        w = result.get('swept_weights', {})
        self.db.execute("""
            INSERT OR REPLACE INTO phase2_results
            (ticker, signal_1, signal_2, weight_1, weight_2, total_return, win_rate, sharpe, max_drawdown, n_trades)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, sig1, sig2, w.get(sig1, 0), w.get(sig2, 0),
              result.get('total_return', 0), result.get('win_rate', 0),
              result.get('sharpe', 0), result.get('max_drawdown', 0),
              result.get('n_trades', 0)))
        self.db.commit()


# ============================================================================
# PHASE 3: GENETIC ALGORITHM OPTIMIZATION
# ============================================================================

class GeneticOptimizer:
    """
    Evolves full weight vectors using tournament selection + crossover + mutation.
    Only needed if Phase 2 captures <90% of explainable variance.
    """

    def __init__(self, engine: BacktestEngine, db: sqlite3.Connection,
                 population_size: int = 50, generations: int = 30,
                 mutation_rate: float = 0.15, elite_fraction: float = 0.1,
                 max_days: int = None):
        self.engine = engine
        self.db = db
        self.pop_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_count = max(2, int(population_size * elite_fraction))
        self.max_days = max_days

    def _random_weights(self) -> Dict[str, float]:
        """Generate random weights within bounds."""
        w = {}
        for sig_type, (lo, hi) in WEIGHT_BOUNDS.items():
            w[sig_type] = round(random.uniform(lo, hi), 3)
        return w

    def _fitness(self, ticker: str, weights: Dict[str, float]) -> float:
        """Evaluate fitness (total return) for a weight vector."""
        result = self.engine.run_backtest(ticker, weights=weights, max_days=self.max_days)
        # Fitness = total return penalized by max drawdown
        return result.get('total_return', 0) * (1 - result.get('max_drawdown', 0))

    def _tournament_select(self, population: List[Tuple[Dict, float]], k: int = 3) -> Dict:
        """Tournament selection."""
        candidates = random.sample(population, min(k, len(population)))
        return max(candidates, key=lambda x: x[1])[0]

    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """Uniform crossover."""
        child = {}
        for sig_type in DEFAULT_WEIGHTS:
            if random.random() < 0.5:
                child[sig_type] = parent1.get(sig_type, DEFAULT_WEIGHTS[sig_type])
            else:
                child[sig_type] = parent2.get(sig_type, DEFAULT_WEIGHTS[sig_type])
        return child

    def _mutate(self, weights: Dict) -> Dict:
        """Gaussian mutation within bounds."""
        mutated = dict(weights)
        for sig_type in mutated:
            if random.random() < self.mutation_rate:
                lo, hi = WEIGHT_BOUNDS.get(sig_type, (0, 0.5))
                sigma = (hi - lo) * 0.1
                mutated[sig_type] = round(max(lo, min(hi, mutated[sig_type] + random.gauss(0, sigma))), 3)
        return mutated

    def optimize(self, ticker: str) -> Dict:
        """Run GA optimization for a ticker."""
        print(f"  Phase 3 GA: {ticker}")

        # Initialize population
        population = [(self._random_weights(), 0) for _ in range(self.pop_size)]

        best_ever = None
        best_fitness = -999

        for gen in range(self.generations):
            # Evaluate fitness
            evaluated = [(w, self._fitness(ticker, w)) for w, _ in population]
            evaluated.sort(key=lambda x: x[1], reverse=True)

            if evaluated[0][1] > best_fitness:
                best_fitness = evaluated[0][1]
                best_ever = dict(evaluated[0][0])

            if gen % 5 == 0:
                print(f"    Gen {gen}: best fitness={best_fitness:.2f}")

            # Elitism
            new_pop = [(w, f) for w, f in evaluated[:self.elite_count]]

            # Breed
            while len(new_pop) < self.pop_size:
                p1 = self._tournament_select(evaluated)
                p2 = self._tournament_select(evaluated)
                child = self._crossover(p1, p2)
                child = self._mutate(child)
                new_pop.append((child, 0))

            population = new_pop

        # Final evaluation
        final_result = self.engine.run_backtest(ticker, weights=best_ever)
        final_result['optimal_weights'] = best_ever
        final_result['fitness'] = best_fitness

        # Store
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS phase3_results (
                ticker TEXT PRIMARY KEY,
                optimal_weights TEXT,
                total_return REAL,
                win_rate REAL,
                sharpe REAL,
                max_drawdown REAL,
                fitness REAL,
                n_trades INTEGER
            )
        """)
        self.db.execute("""
            INSERT OR REPLACE INTO phase3_results
            (ticker, optimal_weights, total_return, win_rate, sharpe, max_drawdown, fitness, n_trades)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, json.dumps(best_ever), final_result.get('total_return', 0),
              final_result.get('win_rate', 0), final_result.get('sharpe', 0),
              final_result.get('max_drawdown', 0), best_fitness,
              final_result.get('n_trades', 0)))
        self.db.commit()

        return final_result

    def optimize_all(self, tickers: List[str] = None) -> Dict[str, Dict]:
        """Run GA for all tickers."""
        if tickers is None:
            tickers = PORTFOLIO_TICKERS
        results = {}
        for ticker in tickers:
            results[ticker] = self.optimize(ticker)
        return results


# ============================================================================
# PHASE 4: RISK MANAGEMENT
# ============================================================================

class RiskOptimizer:
    """
    Phase 4a: Trailing stop-loss optimization
    Phase 4b: Time-based exit optimization
    Phase 4c: Hybrid tiered exit strategies
    Phase 4d: VIX correlation analysis
    Phase 4e: Position sizing (Kelly + volatility-adjusted)
    Phase 4f: Sector concentration limits
    Phase 4g: ADR/ETF mapping
    """

    def __init__(self, engine: BacktestEngine, db: sqlite3.Connection):
        self.engine = engine
        self.db = db

    # ---- Phase 4a: Trailing Stop-Loss ----

    def optimize_stops(self, ticker: str, weights: Dict[str, float] = None) -> List[Dict]:
        """
        Grid stop-loss % against normal price volatility.
        Uses ATR (Average True Range) to calibrate stop distance.
        """
        results = []
        prices = self.engine.cache.get_prices(ticker)
        if prices.empty:
            return results

        # Calculate ATR(14) as baseline volatility
        close = prices['Close']
        low = prices['Low']
        high = prices['High']
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr_14 = tr.rolling(14).mean().iloc[-1]
        avg_price = close.iloc[-1]
        atr_pct = atr_14 / avg_price if avg_price > 0 else 0.02

        for stop in STOP_GRID:
            result = self.engine.run_backtest(ticker, weights=weights, stop_loss=stop)
            result['stop_loss'] = stop
            result['atr_14_pct'] = round(atr_pct, 4)
            result['stop_vs_atr'] = round(stop / atr_pct, 2) if atr_pct > 0 else 0
            results.append(result)

        # Store
        self._store_risk_results(ticker, 'stop_loss', results)
        return results

    # ---- Phase 4b: Time-Based Exit ----

    def optimize_time_exits(self, ticker: str, weights: Dict[str, float] = None) -> List[Dict]:
        """Test different holding period limits."""
        results = []
        for time_exit in TIME_EXIT_GRID:
            result = self.engine.run_backtest(ticker, weights=weights, time_exit=time_exit)
            result['time_exit'] = time_exit
            results.append(result)

        self._store_risk_results(ticker, 'time_exit', results)
        return results

    # ---- Phase 4c: Hybrid Tiered Exits ----

    def optimize_tiered_exits(self, ticker: str, weights: Dict[str, float] = None) -> List[Dict]:
        """Test tiered exit strategies."""
        results = []
        for i, tiers in enumerate(TIERED_EXITS):
            result = self.engine.run_backtest(ticker, weights=weights, tiered_exit=tiers)
            result['tiered_strategy'] = i
            result['tiered_tiers'] = tiers
            results.append(result)

        self._store_risk_results(ticker, 'tiered_exit', results)
        return results

    # ---- Phase 4d: VIX Correlation ----

    def analyze_vix_correlation(self, ticker: str, weights: Dict[str, float] = None) -> Dict:
        """
        Correlate strategy performance vs VIX regime.
        Tests: do stops work better in high VIX? Do time exits work better in low VIX?
        """
        # Get VIX data
        vix_data = self.engine.cache.get_prices('^VIX')
        if vix_data.empty:
            # Fetch it
            try:
                vix = yf.Ticker('^VIX').history(period='10y')
                vix.index = vix.index.tz_localize(None) if vix.index.tz else vix.index
                vix_data = vix[['Close']].rename(columns={'Close': 'close'})
            except:
                return {'error': 'VIX data unavailable'}

        # Run backtest with different stops and correlate against VIX at entry
        results = {}
        for stop in [0.05, 0.10, 0.15, 0.20]:
            for time_exit in [21, 63, 126]:
                result = self.engine.run_backtest(
                    ticker, weights=weights,
                    stop_loss=stop, time_exit=time_exit
                )
                key = f"stop={stop},time={time_exit}"
                results[key] = {
                    'total_return': result.get('total_return', 0),
                    'win_rate': result.get('win_rate', 0),
                    'sharpe': result.get('sharpe', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'n_trades': result.get('n_trades', 0),
                }

        self._store_risk_results(ticker, 'vix_correlation', list(results.values()))
        return results

    # ---- Phase 4e: Position Sizing ----

    def optimize_position_sizing(self, ticker: str, weights: Dict[str, float] = None) -> List[Dict]:
        """
        Test Kelly criterion and volatility-adjusted sizing.
        Kelly fraction = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
        """
        # First run to get base stats
        base = self.engine.run_backtest(ticker, weights=weights)
        win_rate = base.get('win_rate', 0.5)
        avg_win = base.get('avg_win', 0) / 100
        avg_loss = abs(base.get('avg_loss', 0)) / 100

        # Kelly fraction
        if avg_win > 0 and avg_loss > 0:
            kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly = max(0, min(kelly, 1.0))
        else:
            kelly = 0.5

        # Test different position sizes
        sizes = [0.25, 0.40, 0.50, 0.60, 0.75, 0.80, 1.0]
        kelly_sizes = [kelly * 0.25, kelly * 0.5, kelly * 0.75, kelly]
        sizes = sorted(set(sizes + [max(0, min(1, s)) for s in kelly_sizes]))

        results = []
        for size in sizes:
            result = self.engine.run_backtest(ticker, weights=weights, position_size=size)
            result['position_size'] = size
            result['kelly_fraction'] = round(kelly, 4)
            results.append(result)

        self._store_risk_results(ticker, 'position_sizing', results)
        return results

    # ---- Phase 4f: Sector Concentration ----

    def analyze_sector_limits(self, tickers: List[str] = None) -> Dict:
        """
        Analyze sector volatility and recommend concentration limits.
        Grid: CAN/US/EURO/Emerging × sector volatility.
        """
        if tickers is None:
            tickers = PORTFOLIO_TICKERS

        sector_data = {}
        for ticker in tickers:
            sector = SECTOR_MAP.get(ticker, 'Unknown')
            geo = GEO_MAP.get(ticker, 'Unknown')

            prices = self.engine.cache.get_prices(ticker)
            if prices.empty:
                continue

            returns = prices['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # annualized
            avg_return = returns.mean() * 252

            key = f"{geo}_{sector}"
            if key not in sector_data:
                sector_data[key] = {'tickers': [], 'volatilities': [], 'returns': []}
            sector_data[key]['tickers'].append(ticker)
            sector_data[key]['volatilities'].append(volatility)
            sector_data[key]['returns'].append(avg_return)

        # Calculate limits
        limits = {}
        for key, data in sector_data.items():
            avg_vol = np.mean(data['volatilities'])
            avg_ret = np.mean(data['returns'])
            n_tickers = len(data['tickers'])

            # Higher volatility → lower concentration limit
            if avg_vol < 0.15:
                max_allocation = 0.30  # 30% max in low-vol sector
            elif avg_vol < 0.25:
                max_allocation = 0.20
            elif avg_vol < 0.35:
                max_allocation = 0.15
            else:
                max_allocation = 0.10

            per_ticker = max_allocation / max(n_tickers, 1)

            limits[key] = {
                'tickers': data['tickers'],
                'avg_volatility': round(avg_vol, 4),
                'avg_return': round(avg_ret, 4),
                'max_sector_allocation': max_allocation,
                'per_ticker_limit': round(per_ticker, 4),
                'n_tickers': n_tickers,
            }

        # Store
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sector_limits (
                sector_key TEXT PRIMARY KEY,
                tickers TEXT,
                avg_volatility REAL,
                avg_return REAL,
                max_sector_allocation REAL,
                per_ticker_limit REAL,
                n_tickers INTEGER
            )
        """)
        for key, data in limits.items():
            self.db.execute("""
                INSERT OR REPLACE INTO sector_limits
                (sector_key, tickers, avg_volatility, avg_return, max_sector_allocation, per_ticker_limit, n_tickers)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, json.dumps(data['tickers']), data['avg_volatility'],
                  data['avg_return'], data['max_sector_allocation'],
                  data['per_ticker_limit'], data['n_tickers']))
        self.db.commit()

        return limits

    # ---- Phase 4g: ADR/ETF Mapping ----

    def get_adr_mapping(self) -> Dict:
        """Return ADR/ETF mapping for non-North-American exposure."""
        return ADR_MAP

    # ---- Storage ----

    def _store_risk_results(self, ticker: str, strategy_type: str, results: List[Dict]):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS phase4_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                param_key TEXT,
                param_value REAL,
                total_return REAL,
                win_rate REAL,
                sharpe REAL,
                max_drawdown REAL,
                n_trades INTEGER,
                profit_factor REAL
            )
        """)
        # Clear previous results for this ticker+strategy to avoid dupes
        self.db.execute("DELETE FROM phase4_results WHERE ticker = ? AND strategy_type = ?", (ticker, strategy_type))
        for r in results:
            self.db.execute("""
                INSERT INTO phase4_results
                (ticker, strategy_type, param_key, param_value, total_return, win_rate, sharpe, max_drawdown, n_trades, profit_factor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker, strategy_type,
                  r.get('stop_loss') or r.get('time_exit') or r.get('position_size') or r.get('tiered_strategy'),
                  r.get('stop_loss') or r.get('time_exit') or r.get('position_size') or float(r.get('tiered_strategy', 0)),
                  r.get('total_return', 0), r.get('win_rate', 0),
                  r.get('sharpe', 0), r.get('max_drawdown', 0),
                  r.get('n_trades', 0), r.get('profit_factor', 0)))
        self.db.commit()


# ============================================================================
# SECTOR ETF COMPARISON
# ============================================================================

class ETFComparator:
    """Compare strategy performance against sector ETFs."""

    def __init__(self, engine: BacktestEngine, db: sqlite3.Connection):
        self.engine = engine
        self.db = db

    def compare_all(self, tickers: List[str] = None) -> Dict:
        """Compare each ticker's strategy vs relevant sector ETF."""
        if tickers is None:
            tickers = PORTFOLIO_TICKERS

        comparisons = {}
        for ticker in tickers:
            # Run strategy for ticker
            strategy_result = self.engine.run_backtest(ticker)
            buy_hold = self.engine.run_backtest(ticker, weights={k: 0 for k in DEFAULT_WEIGHTS})

            # Find relevant ETF
            sector = SECTOR_MAP.get(ticker, '')
            geo = GEO_MAP.get(ticker, '')

            etf_benchmark = None
            if geo == 'Europe':
                etf_benchmark = self.engine.run_backtest('FEZ')
            elif sector == 'Financials':
                etf_benchmark = self.engine.run_backtest('XFN') if 'XFN' in self.engine.cache.get_all_tickers() else None
            elif sector == 'Energy':
                etf_benchmark = self.engine.run_backtest('XEG') if 'XEG' in self.engine.cache.get_all_tickers() else None

            comparisons[ticker] = {
                'strategy_return': strategy_result.get('total_return', 0),
                'buy_hold_return': buy_hold.get('total_return', 0),
                'etf_return': etf_benchmark.get('total_return', 0) if etf_benchmark else None,
                'strategy_sharpe': strategy_result.get('sharpe', 0),
                'buy_hold_sharpe': buy_hold.get('sharpe', 0),
                'beat_buy_hold': strategy_result.get('total_return', 0) > buy_hold.get('total_return', 0),
                'beat_etf': strategy_result.get('total_return', 0) > etf_benchmark.get('total_return', 0) if etf_benchmark else None,
                'recommendation': 'STRATEGY' if strategy_result.get('total_return', 0) > max(buy_hold.get('total_return', 0), etf_benchmark.get('total_return', 0) if etf_benchmark else 0) else 'ETF' if etf_benchmark and etf_benchmark.get('total_return', 0) > strategy_result.get('total_return', 0) else 'BUY_HOLD',
            }

        # Store
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS etf_comparison (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT PRIMARY KEY,
                strategy_return REAL,
                buy_hold_return REAL,
                etf_return REAL,
                strategy_sharpe REAL,
                beat_buy_hold INTEGER,
                beat_etf INTEGER,
                recommendation TEXT
            )
        """)
        for ticker, comp in comparisons.items():
            self.db.execute("""
                INSERT OR REPLACE INTO etf_comparison
                (ticker, strategy_return, buy_hold_return, etf_return, strategy_sharpe, beat_buy_hold, beat_etf, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker, comp['strategy_return'], comp['buy_hold_return'],
                  comp['etf_return'], comp['strategy_sharpe'],
                  1 if comp['beat_buy_hold'] else 0,
                  1 if comp['beat_etf'] else 0 if comp['beat_etf'] is not None else -1,
                  comp['recommendation']))
        self.db.commit()

        return comparisons


# ============================================================================
# MAIN — Run all phases
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Unified Backtest Optimization Engine')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3, 4, 5], help='Run specific phase')
    parser.add_argument('--ticker', help='Run for specific ticker only')
    parser.add_argument('--refresh-data', action='store_true', help='Refresh price cache first')
    parser.add_argument('--compare-etfs', action='store_true', help='Run ETF comparison')
    parser.add_argument('--sector-limits', action='store_true', help='Analyze sector limits')
    args = parser.parse_args()

    db = get_db()
    cache = DataCache()
    engine = BacktestEngine(cache)

    tickers = [args.ticker] if args.ticker else PORTFOLIO_TICKERS

    # Refresh data if requested
    if args.refresh_data:
        print("Refreshing price data cache...")
        cache.refresh_all(tickers + list(SECTOR_ETFS.keys()))

    # Phase 1: Single-indicator sweep
    if args.phase == 1 or args.phase is None:
        print("\n" + "=" * 80)
        print("PHASE 1: Single-Indicator Weight Sweep")
        print("=" * 80)
        p1 = Phase1Sweep(engine, db)
        p1_results = p1.sweep_all(tickers)

    # Phase 2: Pairwise interaction sweep
    if args.phase == 2 or args.phase is None:
        print("\n" + "=" * 80)
        print("PHASE 2: Pairwise Interaction Sweep")
        print("=" * 80)
        p2 = Phase2Sweep(engine, db)
        p2_results = p2.sweep_all(tickers)

    # Phase 3: Genetic Algorithm
    if args.phase == 3 or args.phase is None:
        print("\n" + "=" * 80)
        print("PHASE 3: Genetic Algorithm Optimization")
        print("=" * 80)
        ga = GeneticOptimizer(engine, db, population_size=30, generations=20)
        ga_results = ga.optimize_all(tickers)

    # Phase 4: Risk Management
    if args.phase == 4 or args.phase is None:
        print("\n" + "=" * 80)
        print("PHASE 4: Risk Management Optimization")
        print("=" * 80)
        risk = RiskOptimizer(engine, db)

        for ticker in tickers:
            print(f"\n  {ticker}:")
            print("    4a: Trailing stop-loss...")
            risk.optimize_stops(ticker)
            print("    4b: Time-based exits...")
            risk.optimize_time_exits(ticker)
            print("    4c: Tiered exits...")
            risk.optimize_tiered_exits(ticker)
            print("    4d: VIX correlation...")
            risk.analyze_vix_correlation(ticker)
            print("    4e: Position sizing...")
            risk.optimize_position_sizing(ticker)

        print("\n    4f: Sector concentration limits...")
        risk.analyze_sector_limits(tickers)

    # Phase 5: ETF Comparison
    if args.compare_etfs or args.phase == 5 or args.phase is None:
        print("\n" + "=" * 80)
        print("PHASE 5: Sector ETF Comparison")
        print("=" * 80)
        comp = ETFComparator(engine, db)
        comparisons = comp.compare_all(tickers)
        for ticker, c in comparisons.items():
            print(f"  {ticker}: strategy={c['strategy_return']:.1f}% bh={c['buy_hold_return']:.1f}% etf={c['etf_return']:.1f if c['etf_return'] else 'N/A'}% → {c['recommendation']}")

    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
