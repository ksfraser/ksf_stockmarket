#!/usr/bin/env python3
"""
compute_all_talib_indicators.py
================================
Compute every TA-Lib indicator we can for each symbol and store in
`ta_indicators` table (wide format: one row per symbol-date, columns
for each indicator). Then run the full correlation study.

This fills the gap: currently only 6 composite scores in evalsummary.
After this run we'll have 80+ TA-Lib indicators per day per symbol,
enabling the "which indicators are actually predictive" analysis.
"""

import sys
import time
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

# Use modular database connector (MariaDB or SQLite)
sys.path.insert(0, '/home/ksf_stockmarket/ksf_stockmarket/python')
from db_connector import get_connection

conn = get_connection()
cursor = conn.cursor()

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    print("ERROR: TA-Lib not available. Install with: pip install ta-lib")
    exit(1)

# Check TA-Lib version and available functions
print(f"TA-Lib version: {talib.__version__}")
print(f"Available groups: {talib.get_function_groups().keys()}")

# Build complete indicator list from TA-Lib
# We want every function that takes OHLCV (or just close) as input
ALL_TA_INDICATORS = {}

# Manually curated subset — TA-Lib has 156 functions but many require
# special inputs (e.g., HT_PHASOR needs timeperiod). We'll test all
# that work with standard OHLCV and reasonable parameters.

# Overlap Studies
for period in [5, 10, 20, 50, 100, 200]:
    ALL_TA_INDICATORS[f'SMA_{period}'] = {'func': talib.SMA, 'args': ['close'], 'kwargs': {'timeperiod': period}}
    ALL_TA_INDICATORS[f'EMA_{period}'] = {'func': talib.EMA, 'args': ['close'], 'kwargs': {'timeperiod': period}}
    ALL_TA_INDICATORS[f'WMA_{period}'] = {'func': talib.WMA, 'args': ['close'], 'kwargs': {'timeperiod': period}}

for tp in [10, 20, 50]:
    ALL_TA_INDICATORS[f'DEMA_{tp}'] = {'func': talib.DEMA, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'TEMA_{tp}'] = {'func': talib.TEMA, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'KAMA_{tp}'] = {'func': talib.KAMA, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'TRIMA_{tp}'] = {'func': talib.TRIMA, 'args': ['close'], 'kwargs': {'timeperiod': tp}}

# Bollinger Bands
for tp in [10, 20, 50]:
        for nb in ['1d5', '2d0', '2d5']:
            name = f'BBANDS_{tp}_{nb}'
            nbv = float(nb.replace('d', '.'))
            ALL_TA_INDICATORS[name] = {'func': talib.BBANDS, 'args': ['close'],
                                        'kwargs': {'timeperiod': tp, 'nbdevup': nbv, 'nbdevdn': nbv},
                                        'multi_output': ['upper', 'mid', 'lower']}

# Momentum
for tp in [7, 14, 21]:
    ALL_TA_INDICATORS[f'RSI_{tp}'] = {'func': talib.RSI, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'MOM_{tp}'] = {'func': talib.MOM, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'ROC_{tp}'] = {'func': talib.ROC, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'ROCP_{tp}'] = {'func': talib.ROCP, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'ROCR_{tp}'] = {'func': talib.ROCR, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'ROCR100_{tp}'] = {'func': talib.ROCR100, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'WILLR_{tp}'] = {'func': talib.WILLR, 'args': ['high', 'low', 'close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'CCI_{tp}'] = {'func': talib.CCI, 'args': ['high', 'low', 'close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'MFI_{tp}'] = {'func': talib.MFI, 'args': ['high', 'low', 'close', 'volume'], 'kwargs': {'timeperiod': tp}}

# MACD
for fast, slow, sig in [(8,21,5), (12,26,9), (24,52,18)]:
    name = f'MACD_{fast}_{slow}_{sig}'
    ALL_TA_INDICATORS[name] = {'func': talib.MACD, 'args': ['close'],
                               'kwargs': {'fastperiod': fast, 'slowperiod': slow, 'signalperiod': sig},
                               'multi_output': ['macd', 'signal', 'hist']}

# Stochastic
for fk, sk, sd in [(5,3,3), (14,3,3), (21,5,5)]:
    name = f'STOCH_{fk}_{sk}_{sd}'
    ALL_TA_INDICATORS[name] = {'func': talib.STOCH, 'args': ['high', 'low', 'close'],
                               'kwargs': {'fastk_period': fk, 'slowk_period': sk, 'slowd_period': sd},
                               'multi_output': ['k', 'd']}

# Stochastic RSI
for tp, fk, fd in [(14,14,3), (14,5,3)]:
    name = f'STOCHRSI_{tp}_{fk}_{fd}'
    ALL_TA_INDICATORS[name] = {'func': talib.STOCHRSI, 'args': ['close'],
                               'kwargs': {'timeperiod': tp, 'fastk_period': fk, 'fastd_period': fd},
                               'multi_output': ['k', 'd']}

# ADX family
for tp in [7, 14, 21]:
    ALL_TA_INDICATORS[f'ADX_{tp}'] = {'func': talib.ADX, 'args': ['high', 'low', 'close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'ADXR_{tp}'] = {'func': talib.ADXR, 'args': ['high', 'low', 'close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'APO_{tp}'] = {'func': talib.APO, 'args': ['close'], 'kwargs': {'fastperiod': tp, 'slowperiod': tp*2}}
    ALL_TA_INDICATORS[f'PPO_{tp}'] = {'func': talib.PPO, 'args': ['close'], 'kwargs': {'fastperiod': tp, 'slowperiod': tp*2}}

# ULTOSC
ALL_TA_INDICATORS['ULTOSC'] = {'func': talib.ULTOSC, 'args': ['high', 'low', 'close'],
                                'kwargs': {'timeperiod1': 7, 'timeperiod2': 14, 'timeperiod3': 28}}
ALL_TA_INDICATORS['BOP'] = {'func': talib.BOP, 'args': ['open', 'high', 'low', 'close'], 'kwargs': {}}

# Cycle
for tp in [7, 14, 20]:
    ALL_TA_INDICATORS[f'ATR_{tp}'] = {'func': talib.ATR, 'args': ['high', 'low', 'close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'NATR_{tp}'] = {'func': talib.NATR, 'args': ['high', 'low', 'close'], 'kwargs': {'timeperiod': tp}}

ALL_TA_INDICATORS['TRANGE'] = {'func': talib.TRANGE, 'args': ['high', 'low', 'close'], 'kwargs': {}}

# Volume
ALL_TA_INDICATORS['OBV'] = {'func': talib.OBV, 'args': ['close', 'volume'], 'kwargs': {}}
ALL_TA_INDICATORS['AD'] = {'func': talib.AD, 'args': ['high', 'low', 'close', 'volume'], 'kwargs': {}}
ALL_TA_INDICATORS['ADOSC'] = {'func': talib.ADOSC, 'args': ['high', 'low', 'close', 'volume'],
                               'kwargs': {'fastperiod': 3, 'slowperiod': 10}}

# Price transform
for fname in ['AVGPRICE', 'MEDPRICE', 'TYPPRICE', 'WCLPRICE']:
    ALL_TA_INDICATORS[fname] = {'func': getattr(talib, fname), 'args': ['open', 'high', 'low', 'close'], 'kwargs': {}}

# Statistical
for tp in [5, 10, 14]:
    ALL_TA_INDICATORS[f'LINEARREG_{tp}'] = {'func': talib.LINEARREG, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'LINEARREG_ANGLE_{tp}'] = {'func': talib.LINEARREG_ANGLE, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'LINEARREG_SLOPE_{tp}'] = {'func': talib.LINEARREG_SLOPE, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'LINEARREG_INTERCEPT_{tp}'] = {'func': talib.LINEARREG_INTERCEPT, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'TSF_{tp}'] = {'func': talib.TSF, 'args': ['close'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'STDDEV_{tp}'] = {'func': talib.STDDEV, 'args': ['close'], 'kwargs': {'timeperiod': tp, 'nbdev': 1}}
    ALL_TA_INDICATORS[f'VAR_{tp}'] = {'func': talib.VAR, 'args': ['close'], 'kwargs': {'timeperiod': tp, 'nbdev': 1}}
    ALL_TA_INDICATORS[f'BETA_{tp}'] = {'func': talib.BETA, 'args': ['high', 'low'], 'kwargs': {'timeperiod': tp}}
    ALL_TA_INDICATORS[f'CORREL_{tp}'] = {'func': talib.CORREL, 'args': ['high', 'low'], 'kwargs': {'timeperiod': tp}}

# Cycle
ALL_TA_INDICATORS['HT_DCPERIOD'] = {'func': talib.HT_DCPERIOD, 'args': ['close'], 'kwargs': {}}
ALL_TA_INDICATORS['HT_DCPHASE'] = {'func': talib.HT_DCPHASE, 'args': ['close'], 'kwargs': {}}
ALL_TA_INDICATORS['HT_TRENDLINE'] = {'func': talib.HT_TRENDLINE, 'args': ['close'], 'kwargs': {}}
ALL_TA_INDICATORS['HT_TRENDMODE'] = {'func': talib.HT_TRENDMODE, 'args': ['close'], 'kwargs': {}}
ALL_TA_INDICATORS['HT_PHASOR'] = {'func': talib.HT_PHASOR, 'args': ['close'], 'kwargs': {}, 'multi_output': ['inphase', 'quadrature']}
ALL_TA_INDICATORS['HT_SINE'] = {'func': talib.HT_SINE, 'args': ['close'], 'kwargs': {}, 'multi_output': ['sine', 'leadsine']}

# --- 61 Candlestick Patterns (TA-Lib CDL*) ---
CDL_PATTERNS = [
    'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE',
    'CDL3OUTSIDE', 'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS',
    'CDLABANDONEDBABY', 'CDLADVANCEBLOCK', 'CDLBELTHOLD', 'CDLBREAKAWAY',
    'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL', 'CDLCOUNTERATTACK',
    'CDLDARKCLOUDCOVER', 'CDLDOJI', 'CDLDOJISTAR', 'CDLDRAGONFLYDOJI',
    'CDLENGULFING', 'CDLEVENINGDOJISTAR', 'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE',
    'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN', 'CDLHARAMI',
    'CDLHARAMICROSS', 'CDLHIKKAKE', 'CDLHIKKAKEMOD', 'CDLHOMINGPIGEON',
    'CDLIDENTICAL3CROWS', 'CDLINNECK', 'CDLINVERTEDHAMMER', 'CDLKICKING',
    'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM', 'CDLLONGLEGGEDDOJI',
    'CDLLONGLINE', 'CDLMARUBOZU', 'CDLMATCHINGLOW', 'CDLMATHOLD',
    'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR', 'CDLONNECK', 'CDLPIERCING',
    'CDLRICKSHAWMAN', 'CDLRISEFALL3METHODS', 'CDLSEPARATINGLINES',
    'CDLSHOOTINGSTAR', 'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN',
    'CDLSTICKSANDWICH', 'CDLTAKURI', 'CDLTASUKIGAP', 'CDLTHRUSTING',
    'CDLTRISTAR', 'CDLUNIQUE3RIVER', 'CDLUPSIDEGAP2CROWS',
    'CDLXSIDEGAP3METHODS',
]

for cdl in CDL_PATTERNS:
    ALL_TA_INDICATORS[cdl] = {'func': getattr(talib, cdl), 'args': ['open', 'high', 'low', 'close'], 'kwargs': {}}

print(f"Total indicators to compute: {len(ALL_TA_INDICATORS)}")

# ── Get symbols with sufficient data
cursor.execute("""
    SELECT DISTINCT symbol FROM stockprices GROUP BY symbol HAVING COUNT(*) >= 200 ORDER BY symbol
""")
symbols = [r[0] for r in cursor.fetchall()]
print(f"\nProcessing {len(symbols)} symbols...")
t0 = time.time()

# Process symbols into ta_indicators table
out_dict_template = {}  # Will be populated on first iteration

for si, sym in enumerate(symbols):
    df = pd.read_sql_query("""
        SELECT price_date, day_open as open, day_high as high,
               day_low as low, day_close as close, volume
        FROM stockprices
        WHERE symbol = ?
        ORDER BY price_date
    """, conn, params=(sym,), parse_dates=['price_date'])

    if len(df) < 55:
        continue

    df = df.set_index('price_date').sort_index()
    close = df['close'].values.astype(float)
    open_ = df['open'].values.astype(float)
    high = df['high'].values.astype(float)
    low = df['low'].values.astype(float)
    volume = df['volume'].values.astype(float)

    # Build output dict
    out_dict = {}
    for ind_name, ind_cfg in ALL_TA_INDICATORS.items():
        try:
            fn = ind_cfg['func']
            arg_map = {'close': close, 'open': open_, 'high': high, 'low': low, 'volume': volume}
            args = [arg_map[a] for a in ind_cfg['args']]
            kwargs = ind_cfg.get('kwargs', {})
            result = fn(*args, **kwargs)
            if isinstance(result, tuple):
                suffixes = ind_cfg.get('multi_output', ['out1', 'out2', 'out3'])
                for j, suf in enumerate(suffixes):
                    col = f'{ind_name}_{suf}'.replace('.', 'd')
                    out_dict[col] = result[j]
            else:
                col = ind_name.replace('.', 'd')
                out_dict[col] = result
        except Exception:
            pass

    # On first symbol, check/update table structure
    if si == 0 and out_dict:
        # Check if table exists and has correct columns
        try:
            cursor.execute("SELECT COUNT(*) FROM ta_indicators LIMIT 1")
            table_exists = True
        except:
            table_exists = False

        if not table_exists:
            # Build and execute CREATE TABLE - use MySQL syntax
            col_defs = ['`symbol` VARCHAR(20) NOT NULL', '`price_date` DATE NOT NULL']
            for col in sorted(out_dict.keys()):
                if col.endswith('_upper') or col.endswith('_lower') or col.endswith('_mid'):
                    col_defs.append(f'`{col}` DOUBLE')
                else:
                    col_defs.append(f'`{col}` DOUBLE')
            col_defs.append('PRIMARY KEY (`symbol`, `price_date`)')
            create_sql = f"CREATE TABLE ta_indicators ({', '.join(col_defs)}) ENGINE=InnoDB"
            cursor.execute(create_sql)
            conn.commit()
            print(f"  Created ta_indicators table with {len(out_dict)} indicator columns")

    # Write to database (MySQL compatible)
    if out_dict:
        dates = df.index
        cols_list = ['symbol', 'price_date'] + [c for c in sorted(out_dict.keys())]

        # Build insert SQL with %s placeholders for MySQL
        placeholders = ', '.join(['%s'] * len(cols_list))
        cols_str = ', '.join([f'`{c}`' for c in cols_list])
        insert_sql = f"INSERT INTO ta_indicators ({cols_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE "
        update_sql = ', '.join([f'`{c}` = VALUES(`{c}`)' for c in out_dict.keys()])

        # Prepare data for executemany
        batch_data = []
        for i, date in enumerate(dates):
            row = [sym, str(date)[:10]]
            for col in sorted(out_dict.keys()):
                row.append(out_dict[col][i] if hasattr(out_dict[col], '__getitem__') else out_dict[col])
            batch_data.append(tuple(row))

        cursor.executemany(insert_sql + update_sql, batch_data)

    if (si + 1) % 5 == 0:
        conn.commit()
        elapsed = time.time() - t0
        n_cols = len(out_dict) if 'out_dict' in dir() else 0
        print(f"  [{si+1}/{len(symbols)}] {elapsed:.0f}s — {sym} ({len(df)} rows x {n_cols} indicators)")

conn.commit()

# Final stats
cursor.execute("SELECT COUNT(*) FROM ta_indicators")
total_rows = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(DISTINCT symbol) FROM ta_indicators")
n_symbols = cursor.fetchone()[0]
cursor.execute("SHOW COLUMNS FROM ta_indicators")
n_indicators = len(cursor.fetchall()) - 2  # minus symbol and price_date columns

print(f"\n✅ DONE: {total_rows:,} rows, {n_symbols} symbols, {n_indicators} indicator columns")
print(f"Time: {time.time()-t0:.0f}s")

conn.close()