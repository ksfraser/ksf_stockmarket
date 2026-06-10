#!/usr/bin/env python3
"""
indicator_correlation_study.py
===============================
For each technical indicator at each lookahead (1,3,5,10,20 days):
  - Compute indicator value today
  - Measure what forward return is at N days ahead
  - Report: hit rate, avg return when signal fires, correlation

This answers the question: "Which indicators actually predict
future returns, and at what horizon?"

Usage:
  python3 indicator_correlation_study.py
"""

import sys
import numpy as np
import pandas as pd

# Use modular database connector (MariaDB or SQLite)
sys.path.insert(0, '/home/ksf_stockmarket/ksf_stockmarket/python')
from db_connector import get_connection

conn = get_connection()
cursor = conn.cursor()

symbols = [r[0] for r in cursor.execute("""
    SELECT symbol FROM evalsummary GROUP BY symbol HAVING COUNT(*) > 200 ORDER BY symbol
""").fetchall()]

indicators = {
    'signal_strength': 'Composite signal (-100 to +100)',
    'rsi_14': 'RSI 14-day',
    'macd_hist': 'MACD histogram',
    'atr_pct': 'ATR % of price',
    'bb_pct': 'Bollinger Band % (0=lower, 1=upper)',
    'roc_10': 'Rate of Change 10-day %',
    'roc_20': 'Rate of Change 20-day %',
    'zscore_20': 'Z-Score 20-day',
    'hvol_20': 'Historical Volatility 20-day (annualized %)',
}

lookaheads = [1, 3, 5, 10, 20]

results = {}

print("INDICATOR-TO-RETURNS CORRELATION STUDY")
print(f"{len(symbols)} symbols × {len(indicators)} indicators × {len(lookaheads)} horizons")
print()

for ind_name, ind_desc in indicators.items():
    results[ind_name] = {}

    for horizon in lookaheads:
        all_values = []
        all_returns = []
        returns_when_high = []
        returns_when_low = []

        for sym in symbols:
            df = pd.read_sql_query(f"""
                SELECT eval_date, {ind_name}, close_price
                FROM evalsummary
                WHERE symbol = ? AND {ind_name} IS NOT NULL
                ORDER BY eval_date
            """, conn, params=(sym,))

            if len(df) < 30:
                continue

            close = df['close_price'].values.astype(float)
            vals = df[ind_name].values.astype(float)

            for i in range(len(df) - horizon):
                if np.isnan(vals[i]):
                    continue
                ret = (close[i + horizon] - close[i]) / close[i] * 100
                all_values.append(vals[i])
                all_returns.append(ret)

        if len(all_values) < 100:
            continue

        av = np.array(all_values)
        ar = np.array(all_returns)
        corr = np.corrcoef(av, ar)[0, 1]

        med = np.median(av)
        high_mask = av > med
        low_mask = av <= med

        if high_mask.sum() > 5:
            returns_when_low.extend(ar[low_mask].tolist())
        if low_mask.sum() > 5:
            returns_when_high.extend(ar[high_mask].tolist())

        avg_high = np.mean(returns_when_high) if returns_when_high else 0
        avg_low = np.mean(returns_when_low) if returns_when_low else 0

        # Hit rate: positive signal → positive return?
        pos_sig = av > med
        pos_ret = ar > 0
        hit_rate = (pos_sig == pos_ret).mean() * 100

        results[ind_name][horizon] = {
            'n': len(all_values),
            'correlation': corr,
            'hit_rate': hit_rate,
            'avg_ret_high': avg_high,
            'avg_ret_low': avg_low,
            'spread': avg_high - avg_low,
        }

# Print
print(f"{'Indicator':<18} {'Horiz':>5} {'N':>7} {'Corr':>7} {'Hit%':>6} {'HighSig%':>10} {'LowSig%':>10} {'Spread':>10}")
print("-" * 85)

for ind_name in indicators:
    if ind_name not in results:
        continue
    print(f"\n{ind_name} — {indicators[ind_name]}")
    for horizon in lookaheads:
        if horizon not in results[ind_name]:
            continue
        r = results[ind_name][horizon]
        print(f"  {'Signal → FwdRet':>16} {horizon:>3}d {r['n']:>7d} {r['correlation']:>7.4f} {r['hit_rate']:>5.1f}% {r['avg_ret_high']:>9.3f}% {r['avg_ret_low']:>9.3f}% {r['spread']:>+9.3f}%")

# Save to DB (MySQL compatible)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS indicator_correlation (
        id INT AUTO_INCREMENT PRIMARY KEY,
        indicator VARCHAR(50),
        horizon_days INT,
        n_samples INT,
        correlation DOUBLE,
        hit_rate DOUBLE,
        avg_return_high DOUBLE,
        avg_return_low DOUBLE,
        spread DOUBLE,
        UNIQUE KEY uniq_ind_horizon (indicator, horizon_days)
    ) ENGINE=InnoDB
""")
for ind_name, horizons in results.items():
    for horizon, r in horizons.items():
        cursor.execute("""
            INSERT INTO indicator_correlation
            (indicator, horizon_days, n_samples, correlation, hit_rate,
             avg_return_high, avg_return_low, spread)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                n_samples = VALUES(n_samples),
                correlation = VALUES(correlation),
                hit_rate = VALUES(hit_rate),
                avg_return_high = VALUES(avg_return_high),
                avg_return_low = VALUES(avg_return_low),
                spread = VALUES(spread)
        """, (ind_name, horizon, r['n'], r['correlation'], r['hit_rate'],
              r['avg_ret_high'], r['avg_ret_low'], r['spread']))
conn.commit()
conn.close()
print("\nSaved to indicator_correlation table")
