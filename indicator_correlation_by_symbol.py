#!/usr/bin/env python3
"""
indicator_correlation_by_symbol.py
===================================
Run indicator-to-returns correlation PER SYMBOL (not pooled).
Also tests expanded candlestick patterns using TA-Lib if available,
or falling back to manual computation of all 10 major patterns.

This answers: "Is the ATR/volatility finding consistent across all 19
symbols, or driven by a few outliers?"
"""

import sqlite3
import numpy as np
import pandas as pd

DB_PATH = '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'
conn = sqlite3.connect(DB_PATH)

symbols = [r[0] for r in conn.execute("""
    SELECT symbol FROM evalsummary GROUP BY symbol HAVING COUNT(*) > 200 ORDER BY symbol
""").fetchall()]

# ─── Expanded candlestick detection (manual, no TA-Lib needed) ───
def detect_all_candlesticks(df):
    """Detect 10 major candlestick patterns manually."""
    c = df['close'].values.astype(float)
    o = df['open'].values.astype(float)
    h = df['high'].values.astype(float)
    l = df['low'].values.astype(float)
    n = len(c)
    body = np.abs(c - o)
    upper_shadow = h - np.maximum(c, o)
    lower_shadow = np.minimum(c, o) - l
    rng = h - l + 1e-10
    body_pct = body / rng

    patterns = {}
    # 1. Doji (tiny body)
    patterns['doji'] = (body_pct < 0.05).astype(float)

    # 2. Hammer (long lower shadow, small body, little upper shadow)
    patterns['hammer'] = ((lower_shadow > 2 * body) &
                          (upper_shadow < body) &
                          (body_pct < 0.3)).astype(float)

    # 3. Inverted Hammer (long upper shadow, small body)
    patterns['inv_hammer'] = ((upper_shadow > 2 * body) &
                              (lower_shadow < body) &
                              (body_pct < 0.3)).astype(float)

    # 4. Shooting Star (long upper shadow after uptrend — use simple version)
    patterns['shooting_star'] = ((upper_shadow > 2 * body) &
                                 (lower_shadow < body) &
                                 (body_pct < 0.3)).astype(float)

    # 5. Engulfing Bull (current bullish body engulfs previous bearish)
    eng_bull = np.zeros(n)
    for i in range(1, n):
        if c[i] > o[i] and c[i-1] <= o[i-1]:  # current bull, prev bear
            if abs(c[i]-o[i]) > abs(c[i-1]-o[i-1]):  # engulfs
                eng_bull[i] = 1
    patterns['engulfing_bull'] = eng_bull

    # 6. Engulfing Bear
    eng_bear = np.zeros(n)
    for i in range(1, n):
        if c[i] <= o[i] and c[i-1] > o[i-1]:
            if abs(c[i]-o[i]) > abs(c[i-1]-o[i-1]):
                eng_bear[i] = 1
    patterns['engulfing_bear'] = eng_bear

    # 7. Morning Star (3-candle: bear, small body, bull that closes past midpoint)
    morning = np.zeros(n)
    for i in range(2, n):
        prev_bear = c[i-2] < o[i-2]
        mid_small = body_pct[i-1] < 0.1
        curr_bull = c[i] > o[i]
        closes_mid = c[i] > (c[i-2] + o[i-2]) / 2
        if prev_bear and mid_small and curr_bull and closes_mid:
            morning[i] = 1
    patterns['morning_star'] = morning

    # 8. Evening Star (opposite of morning)
    evening = np.zeros(n)
    for i in range(2, n):
        prev_bull = c[i-2] > o[i-2]
        mid_small = body_pct[i-1] < 0.1
        curr_bear = c[i] <= o[i]
        closes_mid = c[i] < (c[i-2] + o[i-2]) / 2
        if prev_bull and mid_small and curr_bear and closes_mid:
            evening[i] = 1
    patterns['evening_star'] = evening

    # 9. Marubozu (no shadows — strong trend)
    patterns['marubozu'] = ((upper_shadow < rng * 0.05) &
                            (lower_shadow < rng * 0.05) &
                            (body_pct > 0.8)).astype(float)

    # 10. Spinning Top (small body, both shadows)
    patterns['spinning_top'] = ((body_pct < 0.2) &
                                (upper_shadow > body) &
                                (lower_shadow > body) &
                                (upper_shadow > rng * 0.2) &
                                (lower_shadow > rng * 0.2)).astype(float)

    return patterns


# Indicators to test per-symbol
indicators_to_test = {
    'atr_pct': 'ATR %',
    'hvol_20': 'Historical Vol 20d',
    'macd_hist': 'MACD Histogram',
    'rsi_14': 'RSI 14',
    'bb_pct': 'Bollinger %',
    'signal_strength': 'Composite Signal',
}

lookaheads = [1, 3, 5, 10, 20]

# ─── Part 1: Per-symbol indicator correlation ───
print("=" * 80)
print("PER-SYMBOL INDICATOR CORRELATION TO FORWARD RETURNS")
print("=" * 80)

per_symbol_results = {}  # symbol → indicator → horizon → corr

for sym in symbols:
    per_symbol_results[sym] = {}

    # Load prices + computed indicators
    df = pd.read_sql_query(f"""
        SELECT p.price_date, p.day_close as close, p.day_open as open,
               p.day_high as high, p.day_low as low, p.volume,
               e.atr_pct, e.hvol_20, e.macd_hist, e.rsi_14,
               e.bb_pct, e.signal_strength, e.zscore_20,
               e.roc_10, e.roc_20
        FROM stockprices p
        JOIN evalsummary e ON e.symbol = p.symbol AND e.eval_date = p.price_date
        WHERE p.symbol = ?
        ORDER BY p.price_date
    """, conn, params=(sym,), parse_dates=['price_date'])

    if len(df) < 60:
        continue

    close = df['close'].values.astype(float)

    # Add candlestick patterns
    candle_patterns = detect_all_candlesticks(df)
    for pname, pvals in candle_patterns.items():
        df[pname] = pvals

    all_inds = {**indicators_to_test, **{k: k for k in candle_patterns}}

    for ind_name in all_inds:
        if ind_name not in df.columns:
            continue
        vals = df[ind_name].values.astype(float)

        per_symbol_results[sym][ind_name] = {}

        for horizon in lookaheads:
            rets = []
            sigs = []
            for i in range(len(df) - horizon):
                if np.isnan(vals[i]):
                    continue
                ret = (close[i + horizon] - close[i]) / close[i] * 100
                sigs.append(vals[i])
                rets.append(ret)

            if len(sigs) < 30:
                continue

            sigs = np.array(sigs)
            rets = np.array(rets)
            corr = np.corrcoef(sigs, rets)[0, 1]

            # Hit rate: does positive signal → positive return?
            pos_sig = sigs > np.median(sigs)
            pos_ret = rets > 0
            hit_rate = (pos_sig == pos_ret).mean() * 100

            per_symbol_results[sym][ind_name][horizon] = {
                'corr': corr,
                'hit_rate': hit_rate,
                'n': len(sigs),
            }

# ─── Part 2: Summary across symbols ───
print("\nCONSISTENCY CHECK: How many symbols agree on direction?")
print("-" * 80)

print(f"\n{'Indicator':<18} {'Horiz':>5} {'AvgCorr':>8} {'StdCorr':>8} {'Agree%':>7} {'Min':>7} {'Max':>7} {'HitRate':>7}")
print("-" * 75)

for ind_name in list(indicators_to_test.keys()) + list(candle_patterns.keys()):
    for horizon in lookaheads:
        corrs = []
        hit_rates = []
        for sym in symbols:
            if (sym in per_symbol_results and
                ind_name in per_symbol_results[sym] and
                horizon in per_symbol_results[sym][ind_name]):
                r = per_symbol_results[sym][ind_name][horizon]
                corrs.append(r['corr'])
                hit_rates.append(r['hit_rate'])

        if not corrs:
            continue

        corrs = np.array(corrs)
        avg_c = np.mean(corrs)
        std_c = np.std(corrs)
        agree = (corrs > 0).mean() * 100  # % of symbols with positive corr
        avg_hr = np.mean(hit_rates)

        if abs(avg_c) > 0.01 or horizon == 20:  # only print meaningful or 20d
            FLAG = ''
            if abs(avg_c) >= 0.08 and abs(agree - 50) > 20:
                FLAG = ' ← CONSISTENT'  # strong enough and most symbols agree
            elif abs(avg_c) < 0.02:
                FLAG = ' ← noise'

            print(f"  {ind_name:<16} {horizon:>3}d {avg_c:>+8.4f} {std_c:>8.4f} {agree:>6.0f}% {np.min(corrs):>+7.4f} {np.max(corrs):>+7.4f} {avg_hr:>6.1f}%{FLAG}")

# ─── Part 3: candlestick-specific table ───
print("\n\nCANDLESTICK PATTERN ACCURACY (expanded set, 10 patterns)")
print("-" * 80)
print(f"\n{'Pattern':<18} {'Horiz':>5} {'AvgCorr':>8} {'Agree%':>7} {'HitRate':>7} {'Verdict'}")
print("-" * 70)

for pname in candle_patterns:
    for horizon in lookaheads:
        corrs = []
        hit_rates = []
        for sym in symbols:
            if (sym in per_symbol_results and
                pname in per_symbol_results[sym] and
                horizon in per_symbol_results[sym][pname]):
                r = per_symbol_results[sym][pname][horizon]
                corrs.append(r['corr'])
                hit_rates.append(r['hit_rate'])

        if not corrs:
            continue

        avg_c = np.mean(corrs)
        agree = (np.array(corrs) > 0).mean() * 100
        avg_hr = np.mean(hit_rates)

        if abs(avg_c) >= 0.03:
            verdict = "USEFUL"
        elif abs(avg_c) >= 0.015:
            verdict = "weak"
        else:
            verdict = "ignore"

        print(f"  {pname:<16} {horizon:>3}d {avg_c:>+8.4f} {agree:>6.0f}% {avg_hr:>6.1f}%  {verdict}")

# ─── Part 4: Per-symbol winners for top 5 symbols ───
print("\n\nBEST INDICATOR PER SYMBOL (20-day horizon, by |correlation|):")
print("-" * 80)
for sym in symbols[:10]:
    if sym not in per_symbol_results:
        continue
    winners = []
    for ind_name, horizons in per_symbol_results[sym].items():
        if 20 in horizons:
            r = horizons[20]
            winners.append((ind_name, r['corr'], r['hit_rate']))
    winners.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"\n  {sym}:")
    for ind, corr, hr in winners[:5]:
        direction = "↑buy" if corr > 0 else "↓sell"
        print(f"    {ind:<16} 20d corr={corr:+.4f}  hit={hr:.0f}%  ({direction})")

# Save all results to DB
conn.execute("""
    CREATE TABLE IF NOT EXISTS indicator_correlation_by_symbol (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        indicator TEXT,
        horizon_days INTEGER,
        correlation REAL,
        hit_rate REAL,
        n_samples INTEGER,
        UNIQUE(symbol, indicator, horizon_days)
    )
""")

for sym, inds in per_symbol_results.items():
    for ind_name, horizons in inds.items():
        for horizon, r in horizons.items():
            conn.execute("""
                INSERT OR REPLACE INTO indicator_correlation_by_symbol
                (symbol, indicator, horizon_days, correlation, hit_rate, n_samples)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sym, ind_name, horizon, r['corr'], r['hit_rate'], r['n']))

conn.commit()
conn.close()
print(f"\n\nSaved per-symbol results to indicator_correlation_by_symbol table")
