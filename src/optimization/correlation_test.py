#!/usr/bin/env python3
"""
Indicator Correlation Testing Module
=====================================
Tests each indicator's predictive power for future returns.
Only indicators with statistically significant correlation get non-zero weights.

Methodology:
1. For each ticker, calculate indicator values at each historical point
2. Measure forward returns (1m, 3m, 6m) after each signal
3. Compute correlation (Pearson + Spearman) between signal and return
4. Compute win rate when signal fires vs when it doesn't
5. Compute information coefficient (IC) — rank correlation
6. Test for statistical significance (p-value < 0.05)
7. Store results in DB for weight optimization

Reference: This is similar to the approach used by:
- Quantopian/Lean (alphabetical factor analysis)
- WorldQuant's 101 Alphas framework
- bullarc (Go-based signal fusion with backtesting)
- VectorTA (340+ indicators with SIMD acceleration)
"""

import sys
import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from scipy import stats

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from data_cache import DataCache
from advanced_patterns import AdvancedPatternAnalyzer
from investment_monitor import TechnicalAnalyzer
from analysis_db import get_db


class CorrelationTester:
    """
    Tests predictive power of each indicator for future returns.
    """

    def __init__(self, cache: DataCache = None, db: sqlite3.Connection = None):
        self.cache = cache or DataCache()
        self.db = db or get_db()
        self._ensure_tables()

    def _ensure_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS indicator_correlation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                indicator TEXT NOT NULL,
                forward_period TEXT NOT NULL,  -- '1m', '3m', '6m'
                pearson_corr REAL,
                pearson_pvalue REAL,
                spearman_corr REAL,
                spearman_pvalue REAL,
                information_coefficient REAL,
                signal_win_rate REAL,
                no_signal_win_rate REAL,
                n_signals INTEGER,
                n_total INTEGER,
                significant INTEGER DEFAULT 0,
                recommended_weight REAL DEFAULT 0,
                tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, indicator, forward_period)
            );
            CREATE INDEX IF NOT EXISTS idx_corr_ticker ON indicator_correlation(ticker);
            CREATE INDEX IF NOT EXISTS idx_corr_sig ON indicator_correlation(significant);
        """)
        self.db.commit()

    def test_all_indicators(self, ticker: str, min_signals: int = 20) -> Dict:
        """
        Test all indicators for a single ticker.
        Returns dict of {indicator: {period: correlation_result}}
        """
        prices = self.cache.get_prices(ticker)
        if prices.empty or len(prices) < 250:
            return {}

        results = {}
        forward_periods = {'1m': 21, '3m': 63, '6m': 126}

        # Calculate all indicators at each historical point
        print(f"  {ticker}: calculating indicators across {len(prices)} bars...")

        indicator_history = self._calculate_indicator_history(prices)
        if not indicator_history:
            return {}

        # Calculate forward returns
        close = prices['Close']
        for period_name, period_days in forward_periods.items():
            forward_returns = close.pct_change(period_days).shift(-period_days) * 100

            for indicator_name, indicator_values in indicator_history.items():
                # Align series
                common_idx = indicator_values.index.intersection(forward_returns.index)
                if len(common_idx) < min_signals:
                    continue

                ind_vals = indicator_values.loc[common_idx]
                fwd_rets = forward_returns.loc[common_idx]

                # Remove NaN
                valid = ~(np.isnan(ind_vals) | np.isnan(fwd_rets))
                if valid.sum() < min_signals:
                    continue

                ind_clean = ind_vals[valid]
                fwd_clean = fwd_rets[valid]

                # Pearson correlation
                pearson_r, pearson_p = stats.pearsonr(ind_clean, fwd_clean)

                # Spearman rank correlation
                spearman_r, spearman_p = stats.spearmanr(ind_clean, fwd_clean)

                # Information Coefficient (rank IC)
                ic = stats.spearmanr(ind_clean.rank(), fwd_clean.rank())[0]

                # Win rate analysis
                # For directional indicators: positive signal → positive return?
                median_signal = ind_clean.median()
                signal_up = ind_clean > median_signal
                signal_down = ind_clean <= median_signal

                if signal_up.sum() > 0 and signal_down.sum() > 0:
                    win_rate_up = (fwd_clean[signal_up] > 0).mean()
                    win_rate_down = (fwd_clean[signal_down] > 0).mean()
                    signal_win_rate = win_rate_up
                    no_signal_win_rate = win_rate_down
                else:
                    signal_win_rate = 0.5
                    no_signal_win_rate = 0.5

                # Significance: p < 0.05 and |correlation| > 0.1
                significant = int(pearson_p < 0.05 and abs(pearson_r) > 0.1)

                # Recommended weight based on IC and significance
                if significant:
                    # Weight proportional to IC strength
                    recommended_weight = min(abs(ic) * 2, 0.5)
                else:
                    recommended_weight = 0.0

                result = {
                    'ticker': ticker,
                    'indicator': indicator_name,
                    'forward_period': period_name,
                    'pearson_corr': round(pearson_r, 4),
                    'pearson_pvalue': round(pearson_p, 4),
                    'spearman_corr': round(spearman_r, 4),
                    'spearman_pvalue': round(spearman_p, 4),
                    'information_coefficient': round(ic, 4),
                    'signal_win_rate': round(signal_win_rate, 4),
                    'no_signal_win_rate': round(no_signal_win_rate, 4),
                    'n_signals': int(valid.sum()),
                    'significant': significant,
                    'recommended_weight': round(recommended_weight, 4),
                }

                key = f"{indicator_name}_{period_name}"
                results[key] = result

                # Store in DB
                self.db.execute("""
                    INSERT OR REPLACE INTO indicator_correlation
                    (ticker, indicator, forward_period, pearson_corr, pearson_pvalue,
                     spearman_corr, spearman_pvalue, information_coefficient,
                     signal_win_rate, no_signal_win_rate, n_signals, n_total,
                     significant, recommended_weight, tested_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ticker, indicator_name, period_name, pearson_r, pearson_p,
                      spearman_r, spearman_p, ic, signal_win_rate,
                      no_signal_win_rate, int(valid.sum()), len(common_idx),
                      significant, recommended_weight, datetime.now().isoformat()))

        self.db.commit()
        return results

    def _calculate_indicator_history(self, prices: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate indicator values at each historical point (expanding window)."""
        close = prices['Close']
        high = prices['High']
        low = prices['Low']
        open_s = prices['Open']
        volume = prices['Volume']

        indicators = {}
        n = len(prices)

        # We'll calculate at monthly intervals to speed things up
        # Use every 21st trading day (approximately monthly)
        step = 21
        calculation_points = range(200, n, step)  # Start at 200 for indicator warmup

        print(f"    Calculating at {len(list(calculation_points))} time points...")

        # Pre-calculate all rolling indicators
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))

        # CCI
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(20).mean()
        mean_dev = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        cci_series = (tp - sma_tp) / (0.015 * mean_dev)

        # Williams %R
        hh14 = high.rolling(14).max()
        ll14 = low.rolling(14).min()
        williams_r_series = ((hh14 - close) / (hh14 - ll14)) * -100

        # Fast Stochastic
        hh14_f = high.rolling(14).max()
        ll14_f = low.rolling(14).min()
        fast_k = ((close - ll14_f) / (hh14_f - ll14_f)) * 100
        fast_d = fast_k.rolling(3).mean()

        # Triple MA
        sma4 = close.rolling(4).mean()
        sma9 = close.rolling(9).mean()
        sma18 = close.rolling(18).mean()

        # KST (short-term)
        roc10 = close.pct_change(10) * 100
        roc15 = close.pct_change(15) * 100
        roc20 = close.pct_change(20) * 100
        roc30 = close.pct_change(30) * 100
        kst = (roc10.rolling(10).mean() * 1 +
               roc15.rolling(10).mean() * 2 +
               roc20.rolling(10).mean() * 3 +
               roc30.rolling(15).mean() * 4)
        kst_signal = kst.rolling(9).mean()

        # Pattern signals (simplified — just check at each point)
        pattern_sell = pd.Series(0.0, index=close.index)
        pattern_buy = pd.Series(0.0, index=close.index)

        for i in calculation_points:
            if i >= n:
                break
            try:
                window_data = prices.iloc[max(0, i-60):i+1]
                if len(window_data) < 30:
                    continue

                pat_result = AdvancedPatternAnalyzer.full_analysis(window_data)

                sell_score = 0
                buy_score = 0

                for ptype in ['head_shoulders', 'double_top', 'diamond_top']:
                    p = pat_result.get(ptype, {})
                    if p.get('detected'):
                        sell_score += p.get('confidence', 0)

                p = pat_result.get('wedge', {})
                if p.get('detected') and p.get('subtype') == 'rising_wedge':
                    sell_score += p.get('confidence', 0)

                p = pat_result.get('triangle', {})
                if p.get('detected') and p.get('subtype') == 'descending':
                    sell_score += p.get('confidence', 0)

                gaps = pat_result.get('gaps', [])
                recent_gaps = [g for g in gaps if g['type'] == 'gap_down']
                if recent_gaps:
                    sell_score += 0.3

                pattern_sell.iloc[i] = sell_score
                pattern_buy.iloc[i] = buy_score
            except:
                continue

        # Collect indicator values at calculation points
        for i in calculation_points:
            if i >= n:
                break
            idx = close.index[i]

            indicators.setdefault('RSI', {})[idx] = rsi_series.iloc[i]
            indicators.setdefault('CCI', {})[idx] = cci_series.iloc[i]
            indicators.setdefault('WILLIAMS_R', {})[idx] = williams_r_series.iloc[i]
            indicators.setdefault('FAST_STOCH_K', {})[idx] = fast_k.iloc[i]
            indicators.setdefault('FAST_STOCH_D', {})[idx] = fast_d.iloc[i]
            indicators.setdefault('KST', {})[idx] = kst.iloc[i]
            indicators.setdefault('KST_SIGNAL', {})[idx] = kst_signal.iloc[i]
            indicators.setdefault('TRIPLE_MA_BULLISH', {})[idx] = float(
                sma4.iloc[i] > sma9.iloc[i] > sma18.iloc[i]
            ) if not np.isnan(sma4.iloc[i]) and not np.isnan(sma9.iloc[i]) and not np.isnan(sma18.iloc[i]) else 0
            indicators.setdefault('PATTERN_SELL', {})[idx] = pattern_sell.iloc[i]

        # Convert to Series
        result = {}
        for name, values in indicators.items():
            if values:
                result[name] = pd.Series(values)

        return result

    def get_significant_indicators(self, ticker: str, period: str = '3m') -> List[Dict]:
        """Get indicators that showed significant predictive power."""
        rows = self.db.execute("""
            SELECT indicator, pearson_corr, pearson_pvalue, information_coefficient,
                   signal_win_rate, no_signal_win_rate, recommended_weight, n_signals
            FROM indicator_correlation
            WHERE ticker = ? AND forward_period = ? AND significant = 1
            ORDER BY ABS(information_coefficient) DESC
        """, (ticker, period)).fetchall()

        return [{
            'indicator': r[0],
            'pearson_corr': r[1],
            'pvalue': r[2],
            'ic': r[3],
            'signal_win_rate': r[4],
            'no_signal_win_rate': r[5],
            'recommended_weight': r[6],
            'n_signals': r[7],
        } for r in rows]

    def generate_report(self, ticker: str) -> str:
        """Generate a correlation report for a ticker."""
        L = []
        L.append(f"{'=' * 80}")
        L.append(f"INDICATOR CORRELATION REPORT: {ticker}")
        L.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        L.append(f"{'=' * 80}")

        for period in ['1m', '3m', '6m']:
            sig = self.get_significant_indicators(ticker, period)
            L.append(f"\n--- {period} Forward Returns ---")
            if sig:
                for s in sig:
                    L.append(f"  {s['indicator']:20s}: IC={s['ic']:+.3f}  "
                             f"corr={s['pearson_corr']:+.3f}  "
                             f"p={s['pvalue']:.4f}  "
                             f"WR={s['signal_win_rate']:.1%} vs {s['no_signal_win_rate']:.1%}  "
                             f"weight={s['recommended_weight']:.3f}")
            else:
                L.append("  No significant indicators found")

        return "\n".join(L)


def main():
    """Run correlation testing for all portfolio tickers."""
    import argparse
    parser = argparse.ArgumentParser(description='Indicator Correlation Testing')
    parser.add_argument('--ticker', help='Test specific ticker')
    parser.add_argument('--all', action='store_true', help='Test all portfolio tickers')
    parser.add_argument('--report', help='Generate report for ticker')
    args = parser.parse_args()

    cache = DataCache()
    db = get_db()
    tester = CorrelationTester(cache, db)

    if args.report:
        print(tester.generate_report(args.report))
        return

    if args.ticker:
        tickers = [args.ticker]
    elif args.all:
        try:
            with open('/tmp/portfolio_from_email.json', 'r') as f:
                portfolio = json.load(f)
            tickers = list(portfolio.keys())
        except:
            tickers = ['RY', 'CM', 'CNR', 'BPF.UN', 'FEZ', 'MX', 'UL', 'PZA']
    else:
        print("Use --ticker <symbol> or --all")
        return

    print(f"Running correlation testing for {len(tickers)} tickers...")
    print("This will take several minutes per ticker...")
    print()

    for ticker in tickers:
        print(f"\n{'=' * 60}")
        print(f"Testing: {ticker}")
        print(f"{'=' * 60}")
        results = tester.test_all_indicators(ticker)

        # Print summary
        sig_count = sum(1 for r in results.values() if r.get('significant'))
        total_count = len(results)
        print(f"  Results: {sig_count}/{total_count} significant correlations")

        if sig_count > 0:
            print(f"  Significant indicators:")
            for key, r in results.items():
                if r.get('significant'):
                    print(f"    {r['indicator']:20s} ({r['forward_period']}): "
                          f"IC={r['information_coefficient']:+.3f} "
                          f"WR={r['signal_win_rate']:.1%} "
                          f"weight={r['recommended_weight']:.3f}")

    # Final summary
    print(f"\n{'=' * 80}")
    print("CORRELATION TESTING COMPLETE")
    print(f"{'=' * 80}")
    print("\nRecommended weights by ticker:")
    for ticker in tickers:
        sig = tester.get_significant_indicators(ticker, '3m')
        if sig:
            weights = ', '.join(f"{s['indicator']}={s['recommended_weight']:.3f}" for s in sig[:5])
            print(f"  {ticker}: {weights}")


if __name__ == '__main__':
    main()
