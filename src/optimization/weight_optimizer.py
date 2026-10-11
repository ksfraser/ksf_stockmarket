#!/usr/bin/env python3
"""
Weight-Optimized Signal Scoring System
=======================================

Per-ticker learned weights for each sub-signal type.
Optimized daily using rolling-window backtest accuracy.

Architecture:
  SignalGenerator produces raw sub-signals (MA_ALIGN, RSI, MACD, etc.)
  WeightOptimizer stores per-ticker weights for each sub-signal
  Final score = SUM(sub_signal_value * learned_weight) per ticker
  Rolling coherence: rewards persistent correct signals, penalizes whipsaw

Weight update: gradient-free optimization (hill climbing) since the
objective function (backtest win rate) is non-differentiable.
"""

import sys
import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))

import yfinance as yf
from investment_monitor import SymbolResolver, TechnicalAnalyzer, SignalGenerator
from analysis_db import get_db


# ============================================================================
# DB SCHEMA — Weight tables
# ============================================================================

SCHEMA_SQL = """
-- Per-ticker signal weights (learned)
CREATE TABLE IF NOT EXISTS signal_weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    signal_type TEXT NOT NULL,       -- MA_ALIGN, SMA200, RSI, MACD, BB, STOCH, VWAP, VOL, REL_STR, INV_ETF
    weight REAL NOT NULL DEFAULT 0.0,
    default_weight REAL NOT NULL DEFAULT 0.0,
    n_updates INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, signal_type)
);

-- Weight update log (for tracking convergence)
CREATE TABLE IF NOT EXISTS weight_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    update_date TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    old_weight REAL,
    new_weight REAL,
    delta REAL,
    accuracy_before REAL,     -- rolling 3mo win rate before update
    accuracy_after REAL,      -- rolling 3mo win rate after update (projected)
    UNIQUE(ticker, signal_type, update_date)
);

-- Rolling signal coherence log
CREATE TABLE IF NOT EXISTS signal_coherence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    window_months INTEGER NOT NULL,
    n_signals INTEGER NOT NULL,
    n_transitions INTEGER NOT NULL,  -- BUY->SELL->BUY = 2 transitions
    n_correct INTEGER NOT NULL,
    n_incorrect INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    coherence_score REAL NOT NULL,   -- penalizes whipsaw: win_rate * (1 - transition_ratio)
    UNIQUE(ticker, window_start, window_end, window_months)
);

-- Per-signal-type accuracy by ticker and time period
CREATE TABLE IF NOT EXISTS signal_type_accuracy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    occurrences INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    avg_contribution REAL DEFAULT 0,  -- average contribution to final score
    UNIQUE(ticker, signal_type, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_weights_ticker ON signal_weights(ticker);
CREATE INDEX IF NOT EXISTS idx_coherence_ticker ON signal_coherence(ticker);
CREATE INDEX IF NOT EXISTS idx_type_acc_ticker ON signal_type_accuracy(ticker);
"""


def init_weight_tables(conn: sqlite3.Connection):
    """Create weight-related tables if they don't exist."""
    conn.executescript(SCHEMA_SQL)


# ============================================================================
# DEFAULT WEIGHTS — Based on current SignalGenerator hardcoded values
# ============================================================================

DEFAULT_WEIGHTS = {
    'MA_ALIGN':   0.35,   # was 0.30-0.50
    'SMA200':     0.12,   # was 0.10-0.15
    'RSI':        0.27,   # was 0.20-0.35
    'RSI_DIV':    0.25,   # was 0.25
    'MACD':       0.20,   # was 0.15-0.25
    'BB':         0.15,
    'STOCH':      0.10,
    'VWAP':       0.10,
    'REL_STR':    0.05,   # relative strength boost
    'INV_ETF':    0.08,   # inverse ETF confirmation
    'VOL_CONF':   0.05,   # volume confirmation
}

WEIGHT_BOUNDS = {
    'MA_ALIGN':   (0.10, 0.60),
    'SMA200':     (0.02, 0.30),
    'RSI':        (0.05, 0.50),
    'RSI_DIV':    (0.05, 0.50),
    'MACD':       (0.05, 0.45),
    'BB':         (0.03, 0.30),
    'STOCH':      (0.02, 0.20),
    'VWAP':       (0.02, 0.25),
    'REL_STR':    (0.00, 0.15),
    'INV_ETF':    (0.00, 0.20),
    'VOL_CONF':   (0.00, 0.15),
}


# ============================================================================
# WEIGHTED SIGNAL GENERATOR
# ============================================================================

class WeightedSignalGenerator:
    """SignalGenerator that uses learned per-ticker weights."""

    MIN_ALIGNMENT_DURATION = 20  # days

    def __init__(self, conn: sqlite3.Connection, resolver: SymbolResolver = None):
        self.conn = conn
        self.resolver = resolver or SymbolResolver()

    def get_weights(self, ticker: str) -> Dict[str, float]:
        """Get learned weights for a ticker. Falls back to defaults."""
        c = self.conn.cursor()
        c.execute("SELECT signal_type, weight FROM signal_weights WHERE ticker = ?", (ticker,))
        rows = c.fetchall()

        if rows:
            weights = dict(rows)
            # Fill in any missing signal types with defaults
            for sig_type, default_val in DEFAULT_WEIGHTS.items():
                if sig_type not in weights:
                    weights[sig_type] = default_val
            return weights
        return dict(DEFAULT_WEIGHTS)

    def generate(self, ticker: str, indicators: Dict, macro: Dict = None,
                 relative: Dict = None, volume_profile: Dict = None) -> Dict:
        """Generate weighted signal for a ticker."""
        weights = self.get_weights(ticker)

        if not indicators:
            return {'signal': 'HOLD', 'confidence': 0, 'reasons': ['No data'],
                    'ticker': ticker, 'signal_contributions': {}}

        reasons = []
        details = []
        signal_contributions = {}  # tracks each sub-signal's contribution

        buy_total = 0.0
        sell_total = 0.0

        sma20 = indicators.get('sma_20')
        sma50 = indicators.get('sma_50')
        sma200 = indicators.get('sma_200')
        rsi = indicators.get('rsi')
        macd = indicators.get('macd')
        macd_sig = indicators.get('macd_signal')
        stoch_k = indicators.get('stoch_k')
        bb_pos = indicators.get('bb_position')
        bb_squeeze = indicators.get('bb_squeeze')
        vol_ratio = indicators.get('volume_ratio', 1)

        # === MA ALIGNMENT ===
        if sma20 and sma50:
            align = indicators.get('ma_alignment', '')
            align_dur = indicators.get('ma_alignment_duration', 0)
            w = weights['MA_ALIGN']
            if align_dur < self.MIN_ALIGNMENT_DURATION:
                w *= 0.7

            if align == 'BULLISH':
                contribution = min(w + align_dur / 200, w * 1.5)
                buy_total += contribution
                signal_contributions['MA_ALIGN'] = contribution
                reasons.append(f"Bullish MA alignment ({align_dur}d) weight={w:.3f}")
            elif align == 'BEARISH':
                contribution = min(w + align_dur / 200, w * 1.5)
                sell_total += contribution
                signal_contributions['MA_ALIGN'] = -contribution
                reasons.append(f"Bearish MA alignment ({align_dur}d) weight={w:.3f}")

        # === SMA200 ===
        if sma200 and sma20:
            w = weights['SMA200']
            if indicators.get('trend_sma20_direction') == 'above' and sma20 > sma200:
                buy_total += w
                signal_contributions['SMA200'] = w
                reasons.append(f"Above SMA200 weight={w:.3f}")
            elif indicators.get('trend_sma20_direction') == 'below' and sma20 < sma200:
                sell_total += w
                signal_contributions['SMA200'] = -w
                reasons.append(f"Below SMA200 weight={w:.3f}")

        # === RSI ===
        if rsi is not None:
            w = weights['RSI']
            if rsi > 70:
                dur = indicators.get('rsi_overbought_duration', 0)
                adj_w = min(w + dur * 0.02, w * 1.5)
                sell_total += adj_w
                signal_contributions['RSI'] = -adj_w
                reasons.append(f"RSI overbought {rsi:.1f} ({dur}d) weight={adj_w:.3f}")
            elif rsi < 30:
                dur = indicators.get('rsi_oversold_duration', 0)
                adj_w = min(w + dur * 0.02, w * 1.5)
                buy_total += adj_w
                signal_contributions['RSI'] = adj_w
                reasons.append(f"RSI oversold {rsi:.1f} ({dur}d) weight={adj_w:.3f}")

            # RSI divergence (separate weight)
            div = indicators.get('rsi_divergence', 'NONE')
            if div == 'BULLISH_DIVERGENCE':
                dw = weights['RSI_DIV']
                buy_total += dw
                signal_contributions['RSI_DIV'] = dw
                reasons.append(f"Bullish RSI divergence weight={dw:.3f}")
            elif div == 'BEARISH_DIVERGENCE':
                dw = weights['RSI_DIV']
                sell_total += dw
                signal_contributions['RSI_DIV'] = -dw
                reasons.append(f"Bearish RSI divergence weight={dw:.3f}")

        # === MACD ===
        if macd is not None and macd_sig is not None:
            w = weights['MACD']
            cross = indicators.get('macd_crossover_direction', 'NONE')
            cross_days = indicators.get('macd_crossover_days_ago', 999)

            if macd > macd_sig:
                adj_w = w * 1.25 if (cross == 'BULLISH' and cross_days <= 5) else w * 0.75
                buy_total += adj_w
                signal_contributions['MACD'] = adj_w
                reasons.append(f"MACD bullish weight={adj_w:.3f}")
            else:
                adj_w = w * 1.25 if (cross == 'BEARISH' and cross_days <= 5) else w * 0.75
                sell_total += adj_w
                signal_contributions['MACD'] = -adj_w
                reasons.append(f"MACD bearish weight={adj_w:.3f}")

        # === BOLLINGER BANDS ===
        if bb_pos is not None:
            w = weights['BB']
            if bb_pos > 1:
                sell_total += w
                signal_contributions['BB'] = -w
                reasons.append(f"Above upper BB weight={w:.3f}")
            elif bb_pos < 0:
                buy_total += w
                signal_contributions['BB'] = w
                reasons.append(f"Below lower BB weight={w:.3f}")

        # === STOCHASTIC ===
        if stoch_k is not None:
            w = weights['STOCH']
            if stoch_k > 80:
                sell_total += w
                signal_contributions['STOCH'] = -w
                reasons.append(f"Stoch overbought {stoch_k:.1f} weight={w:.3f}")
            elif stoch_k < 20:
                buy_total += w
                signal_contributions['STOCH'] = w
                reasons.append(f"Stoch oversold {stoch_k:.1f} weight={w:.3f}")

        # === VOLUME CONFIRMATION ===
        w = weights['VOL_CONF']
        if vol_ratio > 1.5:
            details.append(f"High volume {vol_ratio:.1f}x — confirming")
            signal_contributions['VOL_CONF'] = w * 0.5  # small confirmation bonus
            if buy_total > sell_total:
                buy_total += w * 0.5
            elif sell_total > buy_total:
                sell_total += w * 0.5
        elif vol_ratio < 0.5:
            details.append(f"Low volume {vol_ratio:.1f}x — weak signal")

        # === VOLUME PROFILE ===
        if volume_profile and volume_profile.get('price_vs_vwap') is not None:
            w = weights['VWAP']
            pv = volume_profile['price_vs_vwap']
            if pv > 3:
                sell_total += w
                signal_contributions['VWAP'] = -w
                reasons.append(f"Price {pv:+.1f}% above VWAP weight={w:.3f}")
            elif pv < -3:
                buy_total += w
                signal_contributions['VWAP'] = w
                reasons.append(f"Price {pv:+.1f}% below VWAP weight={w:.3f}")

        # === RELATIVE STRENGTH ===
        if relative:
            w = weights['REL_STR']
            rs = relative.get('relative_strength', '')
            if rs == 'STRONG_OUTPERFORM':
                buy_total += w
                signal_contributions['REL_STR'] = w
                details.append(f"Outperforming market+sector weight={w:.3f}")
            elif rs == 'WEAK_UNDERPERFORM':
                sell_total += w
                signal_contributions['REL_STR'] = -w
                details.append(f"Underperforming weight={w:.3f}")

        # === INVERSE ETF ===
        if relative:
            w = weights['INV_ETF']
            ietf = relative.get('inverse_etf_trend', '')
            if ietf == 'SH_RISING_MARKET_FALLING':
                sell_total += w
                signal_contributions['INV_ETF'] = -w
                details.append(f"SH rising (market weak) weight={w:.3f}")
            elif ietf == 'SH_FALLING_MARKET_RISING':
                buy_total += w
                signal_contributions['INV_ETF'] = w
                details.append(f"SH falling (market strong) weight={w:.3f}")

        # === COMPUTE FINAL SIGNAL ===
        if buy_total == 0 and sell_total == 0:
            return {
                'signal': 'HOLD', 'confidence': 0.5, 'strength': 'NEUTRAL',
                'reasons': ['No clear signals'], 'details': details,
                'buy_score': 0, 'sell_score': 0, 'ticker': ticker,
                'signal_contributions': signal_contributions,
                'weights_used': weights,
            }

        total = buy_total + sell_total
        threshold = 1.3  # same as original — must dominate by 30%

        if buy_total > sell_total * threshold:
            sig = 'BUY'
            conf = min(buy_total / total, 0.95)
        elif sell_total > buy_total * threshold:
            sig = 'SELL'
            conf = min(sell_total / total, 0.95)
        else:
            sig = 'HOLD'
            conf = 0.5

        # Apply macro multiplier
        if macro:
            multiplier = macro.get('confidence_multiplier', 1.0)
            conf = min(conf * multiplier, 0.95)

        strength = 'STRONG' if conf >= 0.8 else 'MODERATE' if conf >= 0.6 else 'WEAK' if conf >= 0.4 else 'NEUTRAL'

        return {
            'signal': sig,
            'confidence': conf,
            'strength': strength,
            'reasons': reasons,
            'details': details,
            'buy_score': buy_total,
            'sell_score': sell_total,
            'ticker': ticker,
            'signal_contributions': signal_contributions,
            'weights_used': weights,
            'macro_regime': macro.get('regime', 'UNKNOWN') if macro else 'UNKNOWN',
        }


# ============================================================================
# ROLLING COHERENCE SCORER
# ============================================================================

class RollingCoherenceScorer:
    """
    Evaluates signal sequences over rolling windows.
    
    Coherence = win_rate * (1 - transition_penalty)
    
    Where transition_penalty increases with signal direction changes:
      BUY→BUY→BUY→BUY = 0 transitions = full coherence
      BUY→SELL→BUY→SELL = 3 transitions = low coherence (whipsaw)
    
    This rewards persistent correct signals and penalizes whipsaw.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def compute_coherence(self, ticker: str, window_months: int = 3) -> Dict:
        """Compute rolling coherence for a ticker over the recent window."""
        c = self.conn.cursor()

        # Get recent backtest periods with outcomes
        c.execute("""
            SELECT signal_date, signal, outcome_1m, actual_1m_return
            FROM backtest_periods_5y
            WHERE ticker = ? AND signal != 'HOLD' AND outcome_1m IS NOT NULL
            ORDER BY signal_date DESC
            LIMIT ?
        """, (ticker, window_months))

        rows = c.fetchall()
        if len(rows) < 2:
            return {'coherence': 0, 'win_rate': 0, 'transitions': 0, 'max_transitions': 0,
                    'transition_ratio': 0, 'n_signals': len(rows), 'n_dir_signals': 0,
                    'window_months': window_months, 'signals': [], 'dir_signals': [], 'outcomes': []}

        signals = [r[1] for r in rows]
        outcomes = [r[2] for r in rows]
        returns = [r[3] for r in rows]

        # Win rate
        wins = sum(1 for o in outcomes if o == 'WIN')
        win_rate = wins / len(outcomes)

        # Count transitions (direction changes, excluding HOLDs)
        dir_signals = [s for s in signals if s != 'HOLD']
        transitions = 0
        for i in range(1, len(dir_signals)):
            if dir_signals[i] != dir_signals[i - 1]:
                transitions += 1

        max_transitions = max(len(dir_signals) - 1, 0)
        transition_ratio = transitions / max_transitions if max_transitions > 0 else 0

        # Coherence: high win rate + low transitions = good
        coherence = win_rate * (1 - transition_ratio * 0.5)

        return {
            'coherence': round(coherence, 4),
            'win_rate': round(win_rate, 4),
            'transitions': transitions,
            'max_transitions': max_transitions,
            'transition_ratio': round(transition_ratio, 4),
            'n_signals': len(signals),
            'n_dir_signals': len(dir_signals),
            'window_months': window_months,
            'signals': signals,
            'dir_signals': dir_signals,
            'outcomes': outcomes,
        }

    def compute_all_tickers(self, tickers: List[str], window_months: int = 3) -> Dict[str, Dict]:
        """Compute coherence for all tickers."""
        results = {}
        for ticker in tickers:
            results[ticker] = self.compute_coherence(ticker, window_months)
        return results

    def store_coherence(self, ticker: str, window_months: int, result: Dict):
        """Store coherence result in DB."""
        window_end = date.today().isoformat()
        window_start = (date.today() - timedelta(days=window_months * 30)).isoformat()

        self.conn.execute("""
            INSERT OR REPLACE INTO signal_coherence
            (ticker, window_start, window_end, window_months, n_signals,
             n_transitions, n_correct, n_incorrect, win_rate, coherence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker, window_start, window_end, window_months,
            result['n_signals'], result['transitions'],
            int(result['win_rate'] * result['n_signals']),
            result['n_signals'] - int(result['win_rate'] * result['n_signals']),
            result['win_rate'], result['coherence'],
        ))
        self.conn.commit()


# ============================================================================
# WEIGHT OPTIMIZER — Hill climbing with rolling accuracy feedback
# ============================================================================

class WeightOptimizer:
    """
    Optimizes per-ticker signal weights using hill climbing.
    
    Each day after scanning:
    1. Compute rolling 3mo coherence for each ticker
    2. For each signal type, compute its individual accuracy
    3. Adjust weights: increase weight for accurate signals, decrease for inaccurate
    4. Apply constraints: weights must stay in bounds, sum to reasonable total
    
    This is NOT gradient descent (the objective is non-differentiable).
    It's coordinate-wise hill climbing with adaptive step sizes.
    """

    def __init__(self, conn: sqlite3.Connection, learning_rate: float = 0.05):
        self.conn = conn
        self.lr = learning_rate
        self.coherence_scorer = RollingCoherenceScorer(conn)

    def initialize_weights(self, tickers: List[str]):
        """Set default weights for all tickers."""
        for ticker in tickers:
            for sig_type, default_val in DEFAULT_WEIGHTS.items():
                lo, hi = WEIGHT_BOUNDS[sig_type]
                self.conn.execute("""
                    INSERT OR REPLACE INTO signal_weights
                    (ticker, signal_type, weight, default_weight, n_updates, last_updated)
                    VALUES (?, ?, ?, ?, 0, ?)
                """, (ticker, sig_type, default_val, default_val, datetime.now().isoformat()))
        self.conn.commit()
        print(f"Initialized weights for {len(tickers)} tickers × {len(DEFAULT_WEIGHTS)} signal types")

    def compute_signal_type_accuracy(self, ticker: str, signal_type: str,
                                      months_back: int = 12) -> Dict:
        """
        Compute how often a specific sub-signal was correct.
        
        For each backtest period where this sub-signal contributed,
        check if the direction it pushed was correct.
        """
        c = self.conn.cursor()

        # Get backtest periods with signal details
        c.execute("""
            SELECT signal_date, signal, outcome_1m, actual_1m_return
            FROM backtest_periods_5y
            WHERE ticker = ? AND outcome_1m IS NOT NULL
            AND signal_date >= ?
            ORDER BY signal_date
        """, (ticker, (date.today() - timedelta(days=months_back * 30)).isoformat()))

        rows = c.fetchall()
        if not rows:
            return {'occurrences': 0, 'wins': 0, 'win_rate': 0.5}

        # We need to re-run the signal generator to get sub-signal contributions
        # This is expensive, so we'll use a simplified approach:
        # Check if the overall signal was correct and attribute to active sub-signals
        resolver = SymbolResolver()
        resolved = resolver.resolve(ticker)

        stock = yf.Ticker(resolved)
        hist = stock.history(period='6y')
        if hist.empty:
            return {'occurrences': 0, 'wins': 0, 'win_rate': 0.5}
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index

        occurrences = 0
        wins = 0

        for date_str, signal, outcome, ret in rows:
            target = pd.Timestamp(date_str)
            valid = hist.index[hist.index <= target]
            if len(valid) == 0:
                continue
            target_date = valid[-1]
            idx = hist.index.get_indexer([target_date], method='nearest')[0]
            if idx < 200:
                continue

            hist_at = hist.iloc[:idx + 1].copy()
            indicators = TechnicalAnalyzer.calculate(hist_at)
            if not indicators:
                continue

            # Check if this signal type was active
            was_active = self._check_signal_active(signal_type, indicators)
            if was_active:
                occurrences += 1
                if outcome == 'WIN':
                    wins += 1

        win_rate = wins / occurrences if occurrences > 0 else 0.5
        return {'occurrences': occurrences, 'wins': wins, 'win_rate': win_rate}

    def _check_signal_active(self, signal_type: str, indicators: Dict) -> bool:
        """Check if a specific sub-signal type is active given indicators."""
        if signal_type == 'MA_ALIGN':
            return indicators.get('ma_alignment', '') in ('BULLISH', 'BEARISH')
        elif signal_type == 'SMA200':
            sma20 = indicators.get('sma_20')
            sma200 = indicators.get('sma_200')
            return sma20 is not None and sma200 is not None
        elif signal_type == 'RSI':
            rsi = indicators.get('rsi')
            return rsi is not None and (rsi > 70 or rsi < 30)
        elif signal_type == 'RSI_DIV':
            return indicators.get('rsi_divergence', 'NONE') != 'NONE'
        elif signal_type == 'MACD':
            macd = indicators.get('macd')
            macd_sig = indicators.get('macd_signal')
            return macd is not None and macd_sig is not None
        elif signal_type == 'BB':
            bb_pos = indicators.get('bb_position')
            return bb_pos is not None and (bb_pos > 1 or bb_pos < 0)
        elif signal_type == 'STOCH':
            stoch = indicators.get('stoch_k')
            return stoch is not None and (stoch > 80 or stoch < 20)
        elif signal_type == 'VWAP':
            return False  # needs volume_profile data
        elif signal_type == 'REL_STR':
            return False  # needs relative data
        elif signal_type == 'INV_ETF':
            return False  # needs relative data
        elif signal_type == 'VOL_CONF':
            vol = indicators.get('volume_ratio', 1)
            return vol > 1.5 or vol < 0.5
        return False

    def optimize_weights(self, ticker: str, months_back: int = 12) -> Dict:
        """
        Optimize weights for a single ticker using hill climbing.
        
        Strategy:
        1. Compute accuracy for each signal type
        2. If a signal type has >60% win rate → increase its weight
        3. If a signal type has <40% win rate → decrease its weight
        4. Keep weights within bounds
        """
        c = self.conn.cursor()
        c.execute("SELECT signal_type, weight, default_weight FROM signal_weights WHERE ticker = ?", (ticker,))
        current_weights = {r[0]: (r[1], r[2]) for r in c.fetchall()}

        if not current_weights:
            self.initialize_weights([ticker])
            c.execute("SELECT signal_type, weight, default_weight FROM signal_weights WHERE ticker = ?", (ticker,))
            current_weights = {r[0]: (r[1], r[2]) for r in c.fetchall()}

        changes = {}
        update_date = date.today().isoformat()

        for sig_type in DEFAULT_WEIGHTS:
            if sig_type not in current_weights:
                continue

            current_w, default_w = current_weights[sig_type]
            lo, hi = WEIGHT_BOUNDS[sig_type]

            # Compute accuracy for this signal type
            acc = self.compute_signal_type_accuracy(ticker, sig_type, months_back)
            win_rate = acc['win_rate']

            # Hill climbing step
            if acc['occurrences'] < 3:
                # Not enough data — nudge toward default
                delta = (default_w - current_w) * 0.1
            elif win_rate > 0.60:
                # Signal is accurate — increase weight
                delta = self.lr * (win_rate - 0.50) * 2
            elif win_rate < 0.40:
                # Signal is inaccurate — decrease weight
                delta = self.lr * (win_rate - 0.50) * 2
            else:
                # Near random — nudge toward default
                delta = (default_w - current_w) * 0.05

            new_w = max(lo, min(hi, current_w + delta))

            if abs(new_w - current_w) > 0.001:
                changes[sig_type] = {
                    'old': current_w,
                    'new': new_w,
                    'delta': new_w - current_w,
                    'win_rate': win_rate,
                    'occurrences': acc['occurrences'],
                }

                # Update DB
                c.execute("""
                    UPDATE signal_weights
                    SET weight = ?, n_updates = n_updates + 1, last_updated = ?
                    WHERE ticker = ? AND signal_type = ?
                """, (new_w, datetime.now().isoformat(), ticker, sig_type))

                # Log update
                c.execute("""
                    INSERT OR REPLACE INTO weight_updates
                    (ticker, update_date, signal_type, old_weight, new_weight, delta,
                     accuracy_before, accuracy_after)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (ticker, update_date, sig_type, current_w, new_w,
                      new_w - current_w, win_rate, win_rate))

        self.conn.commit()
        return changes

    def optimize_all(self, tickers: List[str], months_back: int = 12) -> Dict[str, Dict]:
        """Optimize weights for all tickers."""
        all_changes = {}
        for ticker in tickers:
            changes = self.optimize_weights(ticker, months_back)
            if changes:
                all_changes[ticker] = changes
                print(f"  {ticker}: {len(changes)} weight adjustments")
                for sig_type, ch in changes.items():
                    direction = "↑" if ch['delta'] > 0 else "↓"
                    print(f"    {sig_type}: {ch['old']:.3f} → {ch['new']:.3f} ({direction}) wr={ch['win_rate']:.1%} n={ch['occurrences']}")
        return all_changes


# ============================================================================
# MAIN — Initialize and run optimization
# ============================================================================

def main():
    db_path = os.path.expanduser('~/.hermes/cache/analysis_results.db')
    conn = get_db()

    # 1. Create weight tables
    print("=" * 80)
    print("INITIALIZING WEIGHT TABLES")
    print("=" * 80)
    init_weight_tables(conn)

    # 2. Get tickers from portfolio
    with open('/tmp/portfolio_from_email.json', 'r') as f:
        portfolio = json.load(f)
    tickers = list(portfolio.keys())

    # 3. Initialize weights
    print("\n" + "=" * 80)
    print("INITIALIZING WEIGHTS")
    print("=" * 80)
    optimizer = WeightOptimizer(conn, learning_rate=0.05)
    optimizer.initialize_weights(tickers)

    # 4. Compute rolling coherence
    print("\n" + "=" * 80)
    print("COMPUTING ROLLING COHERENCE")
    print("=" * 80)
    scorer = RollingCoherenceScorer(conn)
    for window in [1, 3, 6]:
        print(f"\n{window}-month rolling coherence:")
        results = scorer.compute_all_tickers(tickers, window_months=window)
        for ticker, result in sorted(results.items(), key=lambda x: x[1].get('coherence', 0), reverse=True):
            if result['n_signals'] > 0:
                print(f"  {ticker}: coherence={result['coherence']:.3f} "
                      f"wr={result['win_rate']:.1%} "
                      f"transitions={result['transitions']}/{result['max_transitions']} "
                      f"signals={result['signals'][:5]}")
                scorer.store_coherence(ticker, window, result)

    # 5. Optimize weights
    print("\n" + "=" * 80)
    print("OPTIMIZING WEIGHTS (this will take a while — fetching historical data)")
    print("=" * 80)
    changes = optimizer.optimize_all(tickers, months_back=12)

    # 6. Show final weights
    print("\n" + "=" * 80)
    print("CURRENT WEIGHTS")
    print("=" * 80)
    c = conn.cursor()
    for ticker in tickers:
        c.execute("""
            SELECT signal_type, weight, default_weight, n_updates
            FROM signal_weights WHERE ticker = ? ORDER BY signal_type
        """, (ticker,))
        rows = c.fetchall()
        if rows:
            print(f"\n{ticker}:")
            for sig_type, weight, default, n_updates in rows:
                delta = weight - default
                indicator = "↑" if delta > 0.01 else "↓" if delta < -0.01 else "="
                print(f"  {sig_type:12s}: {weight:.3f} (default={default:.3f}, {indicator}{abs(delta):.3f}, updates={n_updates})")

    print("\nDone.")


if __name__ == '__main__':
    main()
