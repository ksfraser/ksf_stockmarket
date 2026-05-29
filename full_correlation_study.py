#!/usr/bin/env python3
"""
full_correlation_study_v2.py — vectorized version
===================================================
Load everything into DataFrames once, then compute all correlations
in-memory using numpy. Should run in <30s for 222 indicators.

Key improvement: one SQL query per symbol (not per indicator),
then vectorized correlation computation.
"""

import sqlite3
import time
import numpy as np
import pandas as pd

DB_PATH = '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'
conn = sqlite3.connect(DB_PATH)

# Get indicator columns
cols_info = conn.execute(
    "SELECT name FROM pragma_table_info('ta_indicators') "
    "WHERE name NOT IN ('symbol','price_date','id') ORDER BY name"
).fetchall()
ind_names = [c[0] for c in cols_info]

symbols = [r[0] for r in conn.execute(
    "SELECT symbol FROM ta_indicators GROUP BY symbol HAVING COUNT(*) > 200 ORDER BY symbol"
).fetchall()]
lookaheads = [1, 3, 5, 10, 20]

print(f"Loading data: {len(symbols)} symbols × {len(ind_names)} indicators...")

# Load all ta_indicator data + prices in ONE query per symbol
# Then compute everything in memory
all_data = {}
for sym in symbols:
    df = pd.read_sql_query(f"""
        SELECT t.*, p.day_close
        FROM ta_indicators t
        JOIN stockprices p ON p.symbol = t.symbol AND p.price_date = t.price_date
        WHERE t.symbol = ?
        ORDER BY t.price_date
    """, conn, params=(sym,))

    if len(df) < 60:
        continue

    close = df['day_close'].values.astype(float)

    # Compute forward returns for all horizons
    for h in lookaheads:
        fwd = np.full(len(df), np.nan)
        fwd[:len(df) - h] = (close[h:] - close[:-h]) / close[:-h] * 100
        df[f'fwd_ret_{h}'] = fwd

    all_data[sym] = df

conn.close()
print(f"Loaded {len(all_data)} symbols in {time.time():.0f}s")

# Now compute correlations per indicator × horizon × symbol
results = {}

for ind_i, ind_name in enumerate(ind_names):
    results[ind_name] = {}

    for h in lookaheads:
        corrs = []
        hit_rates = []

        for sym, df in all_data.items():
            vals = df[ind_name].values.astype(float)
            rets = df[f'fwd_ret_{h}'].values.astype(float)
            valid = ~np.isnan(vals) & ~np.isnan(rets)

            if valid.sum() < 20:
                continue

            v = vals[valid]
            r = rets[valid]

            if np.std(v) < 1e-10 or np.std(r) < 1e-10:
                continue

            c = np.corrcoef(v, r)[0, 1]
            corrs.append(c)

            med = np.median(v)
            hr = ((v > med) == (r > 0)).mean() * 100
            hit_rates.append(hr)

        if len(corrs) < 5:
            continue

        corrs = np.array(corrs)
        avg_c = np.mean(corrs)
        std_c = np.std(corrs)
        agree = (corrs > 0).mean() * 100
        avg_hr = np.mean(hit_rates) if hit_rates else 50

        if abs(avg_c) >= 0.05 and abs(agree - 50) >= 15:
            verdict = 'USEFUL' if avg_c > 0 else 'USEFUL_INVERSE'
        elif abs(avg_c) >= 0.02 or abs(agree - 50) >= 10:
            verdict = 'WEAK'
        else:
            verdict = 'IGNORE'

        results[ind_name][h] = {
            'avg_corr': avg_c, 'std_corr': std_c, 'agree': agree,
            'min_corr': float(np.min(corrs)), 'max_corr': float(np.max(corrs)),
            'n_symbols': len(corrs), 'avg_hr': avg_hr, 'verdict': verdict,
        }

    if (ind_i + 1) % 50 == 0:
        print(f"  [{ind_i+1}/{len(ind_names)}]")

# ── Print ──
print("\n" + "=" * 80)
print("CORRELATION STUDY — 222 TA-Lib indicators × 5 horizons × 19 symbols")
print("=" * 80)

for vf in ['USEFUL', 'USEFUL_INVERSE', 'WEAK', 'IGNORE']:
    subset = {k: v for k, v in results.items()
               if any(r.get('verdict') == vf for r in v.values())}
    if not subset:
        continue

    label = {'USEFUL': '✅ USEFUL (predictive)',
             'USEFUL_INVERSE': '✅ INVERSE (high= sells)',
             'WEAK': '⚠️ WEAK (marginal)',
             'IGNORE': '❌ IGNORE (noise)'}[vf]
    print(f"\n{label} — {len(subset)} indicators")

    if vf == 'IGNORE':
        names = sorted(subset.keys())
        for i in range(0, len(names), 8):
            print(f"  {', '.join(names[i:i+8])}")
        continue

    print(f"  {'Indicator':<32} {'Horiz':>5} {'AvgCorr':>8} {'Agree%':>7} {'N':>3} {'Hi':>7} {'Lo':>7} {'Hit%':>6}")
    print(f"  " + "-" * 78)
    for name in sorted(subset):
        for h in lookaheads:
            if h not in subset[name]:
                continue
            r = subset[name][h]
            print(f"  {name:<32} {h:>3}d {r['avg_corr']:>+8.4f} {r['agree']:>6.0f}% {r['n_symbols']:>3d} {r['min_corr']:>+7.4f} {r['max_corr']:>+7.4f} {r['avg_hr']:>5.1f}%")

# Save
conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS full_correlation_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        indicator TEXT, horizon_days INTEGER,
        avg_correlation REAL, std_correlation REAL,
        pct_symbols_agree REAL, min_correlation REAL, max_correlation REAL,
        n_symbols INTEGER, avg_hit_rate REAL, verdict TEXT,
        UNIQUE(indicator, horizon_days)
    )
""")
for ind_name, horizons in results.items():
    for h, r in horizons.items():
        conn.execute("""
            INSERT OR REPLACE INTO full_correlation_results
            (indicator, horizon_days, avg_correlation, std_correlation,
             pct_symbols_agree, min_correlation, max_correlation,
             n_symbols, avg_hit_rate, verdict)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ind_name, h, r['avg_corr'], r['std_corr'], r['agree'],
              r['min_corr'], r['max_corr'], r['n_symbols'],
              r['avg_hr'], r['verdict']))
conn.commit()

counts = conn.execute(
    "SELECT verdict, COUNT(*) FROM full_correlation_results GROUP BY ORDER BY verdict"
).fetchall()
print("\nSaved to full_correlation_results:")
for c in counts:
    print(f"  {c[0]:<22}: {c[1]:4d}")
conn.close()
