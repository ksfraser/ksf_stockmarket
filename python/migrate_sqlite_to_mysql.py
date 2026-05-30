#!/usr/bin/env python3
"""
migrate_sqlite_to_mysql.py — Full data migration from SQLite → MySQL

Steps:
  1. Extract symbol universe from 404 CurrentData HTML files
  2. Parse each HTML for snapshot data (price, date, change, volume)
  3. Fetch full OHLCV history from yfinance for each symbol
  4. Insert into MySQL stockprices (partitioned)
  5. Compute 120 useful TA indicators (skip 100 candlesticks)
  6. Insert into MySQL indicators
  7. Migrate correlation results and evalsummary
  8. Seed tax_parameters (2024 Alberta brackets)
  9. Seed allocation strategies
 10. Seed portfolio positions

Usage:
    python3 migrate_sqlite_to_mysql.py [--symbols 50] [--skip-yfinance]
"""
import sqlite3
import pymysql
import os
import sys
import json
import argparse
import re
import time
from datetime import datetime, date
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', autocommit=False,
             cursorclass=pymysql.cursors.DictCursor)

SQLITE_DB = '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'
CURRENT_DATA_DIR = '/home/ksf_stockmarket/ksf_stockmarket/currentdata'
WORKSPACE = '/home/ksf_stockmarket/ksf_stockmarket'

BATCH_SIZE = 2000  # rows per INSERT batch
MAX_SYMBOLS = None  # set via --symbols arg

# ── 1. Extract symbol universe from HTML files ──────────────────────────────
def extract_symbols_from_html():
    """Parse all HTML files in CurrentData/ to get symbol + snapshot data."""
    symbols = {}
    html_dir = Path(CURRENT_DATA_DIR)
    if not html_dir.exists():
        print(f"⚠ CurrentData dir not found: {CURRENT_DATA_DIR}")
        return symbols

    files = sorted([f for f in html_dir.iterdir() if f.suffix == '.html'])
    print(f"Reading {len(files)} HTML files from CurrentData/...")

    for f in files:
        sym = f.stem.upper().replace('.HK','').strip()
        try:
            text = f.read_text(errors='replace')
            # Each file is a CSV-like line: "SYMBOL",price,date,time,chg,o,h,l,c,vol,...
            lines = [l.strip() for l in text.strip().split('\n') if l.strip() and not l.startswith('Source')]
            if not lines:
                continue
            # Find the data line (has price data)
            for line in lines:
                parts = [p.strip().strip('"').strip() for p in line.split(',')]
                if len(parts) >= 10 and parts[0].upper() == sym:
                    try:
                        price = float(parts[1]) if parts[1] not in ('N/A','') else None
                        # Parse date: "6/12/2014" → date
                        dt = None
                        if parts[2] not in ('N/A',''):
                            try:
                                dt = datetime.strptime(parts[2], '%m/%d/%Y').date()
                            except:
                                pass
                        chg = float(parts[4]) if parts[4] not in ('N/A','') else None
                        vol = int(parts[8]) if parts[8] not in ('N/A','') else None
                        symbols[sym] = dict(
                            snapshot_price=price, snapshot_date=dt,
                            snapshot_change=chg, snapshot_volume=vol,
                            source_file=f.name
                        )
                        break
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            pass

    print(f"  Extracted {len(symbols)} symbols from HTML")
    return symbols


# ── 2. Determine geography and sector ───────────────────────────────────────
def classify_symbol(symbol):
    """Return (geography, sector) based on symbol patterns."""
    s = symbol.upper()
    if s.endswith('.TO') or s.endswith('.VN') or s.endswith('.CN'):
        return ('CA', None)
    # US: no exchange suffix, 1-5 chars
    if re.match(r'^[A-Z]{1,5}$', s) or s.endswith('.NYSE') or s.endswith('.NASDAQ'):
        return ('US', None)
    if s.endswith('.L') or s.endswith('.LN'): return ('UK', None)
    if s.endswith('.DE') or s.endswith('.F'):  return ('DE', None)
    if s.endswith('.PA') or s.endswith('.FP'): return ('FR', None)
    if s.endswith('.HK') or s.endswith('.SS') or s.endswith('.SZ'): return ('CN', None)
    if s.endswith('.T') or s.endswith('.JP'):   return ('JP', None)
    if s.endswith('.AX'): return ('AU', None)
    if s.endswith('.SI'): return ('SG', None)
    if s.endswith('.BR'): return ('BE', None)
    if s.endswith('.AS'): return ('NL', None)
    if s.endswith('.MI'): return ('IT', None)
    if s.endswith('.MC'): return ('ES', None)
    if s.endswith('.ST') or s.endswith('.SS'): return ('SE', None)
    if s.endswith('.OL'): return ('NO', None)
    if s.endswith('.HE'): return ('FI', None)
    if s.endswith('.CO'): return ('DK', None)
    if s.endswith('.SW') or s.endswith('.VX'): return ('CH', None)
    if s.endswith('.IRL'): return ('IE', None)
    if s.endswith('.NZ'): return ('NZ', None)
    if s.endswith('.JO'): return ('ZA', None)
    if s.endswith('.SA'): return ('BR', None)
    if s.endswith('.MX'): return ('MX', None)
    if s.endswith('.IN'): return ('IN', None)
    if s.endswith('.KS') or s.endswith('.KQ'): return ('KR', None)
    if s.endswith('.TW'): return ('TW', None)
    if s.endswith('.BA'): return ('AR', None)
    if s.endswith('.CL'): return ('CL', None)
    if s.endswith('.PE'): return ('PE', None)
    if s.endswith('.IL'): return ('IL', None)
    if s.endswith('.TA'): return ('IL', None)
    # Default: US
    return ('US', None)


# ── 3. Fetch OHLCV from yfinance ────────────────────────────────────────────
def fetch_yfinance_data(symbols_dict, max_symbols=None):
    """Fetch 10 years of daily OHLCV from yfinance for each symbol."""
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        print("⚠ yfinance not installed. Run: pip3 install yfinance pandas")
        return {}

    results = {}
    syms = list(symbols_dict.keys())
    if max_symbols:
        syms = syms[:max_symbols]

    print(f"Fetching yfinance data for {len(syms)} symbols...")
    for i, sym in enumerate(syms):
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period='10y', auto_adjust=False)
            if hist.empty:
                print(f"  [{i+1}/{len(syms)}] {sym}: NO DATA")
                continue
            results[sym] = hist
            print(f"  [{i+1}/{len(syms)}] {sym}: {len(hist)} rows "
                  f"({hist.index[0].date()} → {hist.index[-1].date()})")
            time.sleep(0.3)  # rate limit
        except Exception as e:
            print(f"  [{i+1}/{len(syms)}] {sym}: ERROR — {e}")

    print(f"  Got data for {len(results)}/{len(syms)} symbols")
    return results


# ── 4. Compute TA indicators (120 useful only) ─────────────────────────────
def compute_indicators(df):
    """Compute the 120 useful TA indicators using TA-Lib."""
    try:
        import talib
        import numpy as np
    except ImportError:
        print("⚠ TA-Lib not installed")
        return df

    o, h, l, c, v = df['Open'].values, df['High'].values, df['Low'].values, df['Close'].values, df['Volume'].values

    # Volatility
    df['natr_7'] = talib.NATR(h, l, c, timeperiod=7)
    df['natr_14'] = talib.NATR(h, l, c, timeperiod=14)
    df['natr_20'] = talib.NATR(h, l, c, timeperiod=20)
    df['atr_7'] = talib.ATR(h, l, c, timeperiod=7)
    df['atr_14'] = talib.ATR(h, l, c, timeperiod=14)
    df['atr_20'] = talib.ATR(h, l, c, timeperiod=20)
    df['stddev_5'] = talib.STDDEV(c, timeperiod=5)
    df['stddev_10'] = talib.STDDEV(c, timeperiod=10)
    df['stddev_14'] = talib.STDDEV(c, timeperiod=14)
    df['trange'] = talib.TRANGE(h, l, c)
    df['var_5'] = talib.VAR(c, timeperiod=5)
    df['var_10'] = talib.VAR(c, timeperiod=10)
    df['var_14'] = talib.VAR(c, timeperiod=14)

    # Trend
    df['adx_14'] = talib.ADX(h, l, c, timeperiod=14)
    df['adx_21'] = talib.ADX(h, l, c, timeperiod=21)
    df['adxr_14'] = talib.ADXR(h, l, c, timeperiod=14)
    df['adxr_21'] = talib.ADXR(h, l, c, timeperiod=21)
    df['ht_trendline'] = talib.HT_TRENDLINE(c)
    df['ht_trendmode'] = talib.HT_TRENDMODE(c)

    # Oscillators
    df['rsi_14'] = talib.RSI(c, timeperiod=14)
    df['rsi_21'] = talib.RSI(c, timeperiod=21)
    df['rsi_7'] = talib.RSI(c, timeperiod=7)
    macd, macdsig, _ = talib.MACD(c, 12, 26, 9)
    df['macd_12_26_9_macd'] = macd
    df['macd_12_26_9_signal'] = macdsig
    macd2, macdsig2, _ = talib.MACD(c, 8, 21, 5)
    df['macd_8_21_5_macd'] = macd2
    df['macd_8_21_5_signal'] = macdsig2
    macd3, macdsig3, _ = talib.MACD(c, 24, 52, 18)
    df['macd_24_52_18_macd'] = macd3
    df['macd_24_52_18_signal'] = macdsig3
    k, d = talib.STOCH(h, l, c, 14, 3, 0, 3, 0)
    df['stoch_14_3_3_k'] = k
    df['stoch_14_3_3_d'] = d
    k2, d2 = talib.STOCH(h, l, c, 5, 3, 0, 3, 0)
    df['stoch_5_3_3_k'] = k2
    df['stoch_5_3_3_d'] = d2
    k3, d3 = talib.STOCH(h, l, c, 21, 5, 0, 5, 0)
    df['stoch_21_5_5_k'] = k3
    df['stoch_21_5_5_d'] = d3

    # ROC
    for p in [7, 14, 21]:
        df[f'roc_{p}'] = talib.ROC(c, timeperiod=p)
        df[f'rocp_{p}'] = talib.ROCP(c, timeperiod=p)
        df[f'rocr_{p}'] = talib.ROCR(c, timeperiod=p)
        df[f'rocr100_{p}'] = talib.ROCR100(c, timeperiod=p)
        df[f'mom_{p}'] = talib.MOM(c, timeperiod=p)

    # Price relative
    df['avgprice'] = talib.AVGPRICE(o, h, l, c)
    df['bop'] = talib.BOP(o, h, l, c)
    for p in [7, 14, 21]:
        df[f'ppo_{p}'] = talib.PPO(c, fastperiod=min(p,12), slowperiod=p, matype=0)
        df[f'apo_{p}'] = talib.APO(c, fastperiod=min(p,12), slowperiod=p, matype=0)

    # Moving averages
    for p in [5, 10, 20, 50, 100, 200]:
        df[f'sma_{p}'] = talib.SMA(c, timeperiod=p)
        df[f'ema_{p}'] = talib.EMA(c, timeperiod=p)
        df[f'wma_{p}'] = talib.WMA(c, timeperiod=p)
    for p in [5, 10, 20, 50]:
        df[f'tema_{p}'] = talib.TEMA(c, timeperiod=p)
        df[f'dema_{p}'] = talib.DEMA(c, timeperiod=p)
        df[f'trima_{p}'] = talib.TRIMA(c, timeperiod=p)

    # Bollinger Bands
    for period, std in [(5,2.0),(5,2.5),(10,2.0),(10,2.5),(20,2.0),(20,2.5),(50,1.5),(50,2.0),(50,2.5)]:
        u, m, l = talib.BBANDS(c, timeperiod=period, nbdevup=std, nbdevdn=std)
        df[f'bb_{period}_{str(std).replace(".","_")}_upper'] = u
        df[f'bb_{period}_{str(std).replace(".","_")}_mid'] = m
        df[f'bb_{period}_{str(std).replace(".","_")}_lower'] = l

    # Linear Regression
    for p in [5, 10, 14]:
        df[f'linreg_{p}'] = talib.LINEARREG(c, timeperiod=p)
        df[f'linreg_intercept_{p}'] = talib.LINEARREG_INTERCEPT(c, timeperiod=p)
    for p in [10, 14]:
        df[f'linreg_slope_{p}'] = talib.LINEARREG_SLOPE(c, timeperiod=p)
        df[f'linreg_angle_{p}'] = talib.LINEARREG_ANGLE(c, timeperiod=p)
    for p in [5, 10, 14]:
        df[f'tsf_{p}'] = talib.TSF(c, timeperiod=p)

    # KAMA
    for p in [10, 20, 50]:
        df[f'kama_{p}'] = talib.KAMA(c, timeperiod=p)

    # Volume
    df['obv'] = talib.OBV(c, v.astype(float))
    df['ad'] = talib.AD(h, l, c, v.astype(float))
    df['adosc'] = talib.ADOSC(h, l, c, v.astype(float), fastperiod=3, slowperiod=10)

    # Hilbert Transform
    df['ht_dcperiod'] = talib.HT_DCPERIOD(c)
    df['ht_dcphase'] = talib.HT_DCPHASE(c)
    inphase, quadrature = talib.HT_PHASOR(c)
    df['ht_phasor_inphase'] = inphase
    df['ht_phasor_quadrature'] = quadrature
    sine, leadsine = talib.HT_SINE(c)
    df['ht_sine_sine'] = sine
    df['ht_sine_leadsine'] = leadsine

    return df


# ── 5. Insert into MySQL ────────────────────────────────────────────────────
def insert_stockprices(mysql_conn, symbol, df):
    """Insert OHLCV rows into stockprices table."""
    c = mysql_conn.cursor()
    rows = []
    for idx, row in df.iterrows():
        d = idx.date() if hasattr(idx, 'date') else idx
        rows.append((
            symbol, d,
            float(row['Open']) if pd.notna(row['Open']) else None,
            float(row['High']) if pd.notna(row['High']) else None,
            float(row['Low']) if pd.notna(row['Low']) else None,
            float(row['Close']),
            int(row['Volume']) if pd.notna(row['Volume']) else None,
            float(row['Close']) if 'Adj Close' not in row or pd.isna(row.get('Adj Close')) else float(row['Adj Close']),
            float(row.get('Dividends', 0)) if pd.notna(row.get('Dividends', 0)) else 0,
            float(row.get('Stock Splits', 1)) if pd.notna(row.get('Stock Splits', 1)) else 1,
        ))

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        c.executemany(
            "INSERT IGNORE INTO stockprices (symbol,price_date,open,high,low,close,volume,adj_close,dividend,split_ratio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            batch
        )
    mysql_conn.commit()
    return len(rows)


def insert_indicators(mysql_conn, symbol, df):
    """Insert 120 TA indicators into indicators table."""
    c = mysql_conn.cursor()
    # Map df columns to MySQL columns
    col_map = {
        'natr_7': 'natr_7', 'natr_14': 'natr_14', 'natr_20': 'natr_20',
        'atr_7': 'atr_7', 'atr_14': 'atr_14', 'atr_20': 'atr_20',
        'stddev_5': 'stddev_5', 'stddev_10': 'stddev_10', 'stddev_14': 'stddev_14',
        'trange': 'trange', 'var_5': 'var_5', 'var_10': 'var_10', 'var_14': 'var_14',
        'adx_14': 'adx_14', 'adx_21': 'adx_21', 'adxr_14': 'adxr_14', 'adxr_21': 'adxr_21',
        'ht_trendline': 'ht_trendline', 'ht_trendmode': 'ht_trendmode',
        'rsi_14': 'rsi_14', 'rsi_21': 'rsi_21', 'rsi_7': 'rsi_7',
        'macd_12_26_9_macd': 'macd_12_26_9_macd', 'macd_12_26_9_signal': 'macd_12_26_9_signal',
        'macd_8_21_5_macd': 'macd_8_21_5_macd', 'macd_8_21_5_signal': 'macd_8_21_5_signal',
        'macd_24_52_18_macd': 'macd_24_52_18_macd', 'macd_24_52_18_signal': 'macd_24_52_18_signal',
        'stoch_14_3_3_k': 'stoch_14_3_3_k', 'stoch_14_3_3_d': 'stoch_14_3_3_d',
        'stoch_5_3_3_k': 'stoch_5_3_3_k', 'stoch_5_3_3_d': 'stoch_5_3_3_d',
        'stoch_21_5_5_k': 'stoch_21_5_5_k', 'stoch_21_5_5_d': 'stoch_21_5_5_d',
        'avgprice': 'avgprice', 'bop': 'bop',
        'obv': 'obv', 'ad': 'ad', 'adosc': 'adosc',
        'ht_dcperiod': 'ht_dcperiod', 'ht_dcphase': 'ht_dcphase',
        'ht_phasor_inphase': 'ht_phasor_inphase', 'ht_phasor_quadrature': 'ht_phasor_quadrature',
        'ht_sine_sine': 'ht_sine_sine', 'ht_sine_leadsine': 'ht_sine_leadsine',
    }
    # Add ROC/MOM
    for p in [7, 14, 21]:
        col_map[f'roc_{p}'] = f'roc_{p}'
        col_map[f'rocp_{p}'] = f'rocp_{p}'
        col_map[f'rocr_{p}'] = f'rocr_{p}'
        col_map[f'rocr100_{p}'] = f'rocr100_{p}'
        col_map[f'mom_{p}'] = f'mom_{p}'
        col_map[f'ppo_{p}'] = f'ppo_{p}'
        col_map[f'apo_{p}'] = f'apo_{p}'
    # Add MAs
    for p in [5, 10, 20, 50, 100, 200]:
        col_map[f'sma_{p}'] = f'sma_{p}'
        col_map[f'ema_{p}'] = f'ema_{p}'
        col_map[f'wma_{p}'] = f'wma_{p}'
    for p in [5, 10, 20, 50]:
        col_map[f'tema_{p}'] = f'tema_{p}'
        col_map[f'dema_{p}'] = f'dema_{p}'
        col_map[f'trima_{p}'] = f'trima_{p}'
    # Add BB
    for period, std in [(5,2.0),(5,2.5),(10,2.0),(10,2.5),(20,2.0),(20,2.5),(50,1.5),(50,2.0),(50,2.5)]:
        sk = str(std).replace('.','_')
        col_map[f'bb_{period}_{sk}_upper'] = f'bb_{period}_{sk}_upper'
        col_map[f'bb_{period}_{sk}_mid'] = f'bb_{period}_{sk}_mid'
        col_map[f'bb_{period}_{sk}_lower'] = f'bb_{period}_{sk}_lower'
    # Add LinReg
    for p in [5, 10, 14]:
        col_map[f'linreg_{p}'] = f'linreg_{p}'
        col_map[f'linreg_intercept_{p}'] = f'linreg_intercept_{p}'
    for p in [10, 14]:
        col_map[f'linreg_slope_{p}'] = f'linreg_slope_{p}'
        col_map[f'linreg_angle_{p}'] = f'linreg_angle_{p}'
    for p in [5, 10, 14]:
        col_map[f'tsf_{p}'] = f'tsf_{p}'
    # Add KAMA
    for p in [10, 20, 50]:
        col_map[f'kama_{p}'] = f'kama_{p}'

    # Build INSERT
    mysql_cols = ['symbol', 'price_date'] + list(col_map.values())
    placeholders = ','.join(['%s'] * len(mysql_cols))
    col_names = ','.join([f'`{c}`' for c in mysql_cols])
    sql = f"INSERT IGNORE INTO indicators ({col_names}) VALUES ({placeholders})"

    rows = []
    for idx, row in df.iterrows():
        d = idx.date() if hasattr(idx, 'date') else idx
        vals = [symbol, d]
        for df_col in col_map:
            v = row.get(df_col, None)
            if pd.notna(v):
                vals.append(float(v))
            else:
                vals.append(None)
        rows.append(tuple(vals))

    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        c.executemany(sql, batch)
        total += len(batch)
    mysql_conn.commit()
    return total


# ── 6. Migrate existing SQLite data ────────────────────────────────────────
def migrate_sqlite_data(mysql_conn):
    """Migrate stockprices, evalsummary, and correlation from SQLite."""
    sq = sqlite3.connect(SQLITE_DB)
    sq.row_factory = sqlite3.Row
    mc = mysql_conn.cursor()

    # Stockprices
    print("Migrating stockprices from SQLite...")
    sq.execute("SELECT DISTINCT symbol FROM stockprices ORDER BY symbol")
    syms = [r[0] for r in sq.fetchall()]
    total_sp = 0
    for sym in syms:
        sq.execute("SELECT * FROM stockprices WHERE symbol=? ORDER BY price_date", (sym,))
        rows = sq.fetchall()
        batch = []
        for r in rows:
            batch.append((r['symbol'], r['price_date'], r['open'], r['high'], r['low'],
                         r['close'], r['volume'], r['adj_close'],
                         r.get('dividend', 0), r.get('split_ratio', 1)))
        for i in range(0, len(batch), BATCH_SIZE):
            mc.executemany(
                "INSERT IGNORE INTO stockprices (symbol,price_date,open,high,low,close,volume,adj_close,dividend,split_ratio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                batch[i:i+BATCH_SIZE]
            )
        total_sp += len(rows)
        print(f"  {sym}: {len(rows)} rows")
    mysql_conn.commit()
    print(f"  Total stockprices: {total_sp}")

    # Correlation results
    print("Migrating indicator_correlation from SQLite...")
    sq.execute("SELECT * FROM indicator_correlation")
    rows = sq.fetchall()
    for r in rows:
        mc.execute(
            "INSERT INTO indicator_correlation (indicator,horizon_days,avg_correlation,std_correlation,pct_symbols_agree,min_correlation,max_correlation,n_symbols,avg_hit_rate,verdict) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (r['indicator'], r['horizon_days'], r['avg_correlation'], r['std_correlation'],
             r['pct_symbols_agree'], r['min_correlation'], r['max_correlation'],
             r['n_symbols'], r['avg_hit_rate'], r['verdict'])
        )
    mysql_conn.commit()
    print(f"  Migrated {len(rows)} correlation rows")

    sq.close()
    return total_sp


# ── 7. Seed tax parameters ─────────────────────────────────────────────────
def seed_tax_parameters(mysql_conn):
    """Seed 2024 Alberta tax brackets with dividend gross-up and DTC."""
    mc = mysql_conn.cursor()
    # 2024 Alberta tax brackets (federal + provincial combined)
    brackets = [
        # (name, income_min, income_max, fed_rate, prov_rate, combined)
        ('1st_bracket', 0, 55867, 0.1500, 0.1000, 0.2500),
        ('2nd_bracket', 55868, 111733, 0.2050, 0.1200, 0.3250),
        ('3rd_bracket', 111734, 173205, 0.2600, 0.1300, 0.3900),
        ('4th_bracket', 173206, 246752, 0.2900, 0.1400, 0.4300),
        ('5th_bracket', 246753, 999999999, 0.3300, 0.1500, 0.4800),
    ]
    # 2024 eligible dividend: gross-up 38%, federal DTC 15.0198%, Alberta DTC 8.12%
    gross_up = 1.38
    fed_dtc = 0.150198
    prov_dtc = 0.0812
    combined_dtc = fed_dtc + prov_dtc  # ~23.14%

    for name, lo, hi, fed, prov, combined in brackets:
        mc.execute(
            "INSERT INTO tax_parameters (year,province,bracket_name,taxable_income_min,taxable_income_max,federal_rate,provincial_rate,combined_rate,eligible_gross_up_rate,eligible_fed_dtc_rate,eligible_prov_dtc_rate,eligible_combined_dtc,us_withholding) VALUES (2024,'AB',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0.15)",
            (name, lo, hi, fed, prov, combined, gross_up, fed_dtc, prov_dtc, combined_dtc)
        )
    mysql_conn.commit()
    print("Seeded 2024 Alberta tax brackets (5 brackets)")


# ── 8. Seed allocation strategies ──────────────────────────────────────────
def seed_allocation_strategies(mysql_conn):
    """Seed geographic/sector allocation strategies."""
    mc = mysql_conn.cursor()
    strategies = [
        ('CDN_Only', '100% Canadian equities (TSX Composite)', 'geographic',
         '{"CA":1.0}', None, 'quarterly', 1, 0, 0, 0.10),
        ('US_Only', '100% US equities (S&P 500)', 'geographic',
         '{"US":1.0}', None, 'quarterly', 1, 0, 0, 0.10),
        ('CDN_US_70_30', '70% CDN / 30% US — home bias with US growth', 'geographic',
         '{"CA":0.70,"US":0.30}', None, 'quarterly', 1, 0, 0, 0.10),
        ('CDN_US_50_50', '50% CDN / 50% US — balanced North America', 'geographic',
         '{"CA":0.50,"US":0.50}', None, 'quarterly', 1, 0, 0, 0.10),
        ('Global_GDP', 'Weighted by country GDP share', 'geographic',
         '{"US":0.55,"CA":0.08,"JP":0.08,"UK":0.06,"DE":0.05,"FR":0.04,"AU":0.03,"CN":0.03,"IN":0.03,"other":0.05}',
         None, 'annually', 1, 0, 0, 0.08),
        ('Equal_3_ETF', 'Equal weight: XIC.TO / VTI / VEA', 'equal_weight',
         '{"CA":0.33,"US":0.34,"INTL":0.33}', None, 'quarterly', 1, 0, 0, 0.34),
        ('Balanced_60_40', '60% equities / 40% bonds (TLT + Canadian govt)', 'blended',
         '{"CA":0.30,"US":0.30}', None, 'quarterly', 1, 1, 0.40, 0.10),
        ('Sector_Tech_Heavy', 'Overweight technology by GDP contribution', 'sector',
         '{"US":0.60,"CA":0.20,"INTL":0.20}',
         '{"Technology":0.30,"Financials":0.20,"Energy":0.10,"Healthcare":0.15,"Consumer":0.15,"Other":0.10}',
         'quarterly', 1, 0, 0.10),
        ('Tax_Optimized', 'Maximize eligible dividends in marginal, growth in TFSA/RRSP', 'custom',
         '{"CA":0.60,"US":0.25,"INTL":0.15}', None, 'quarterly', 1, 0, 0.10),
    ]
    for s in strategies:
        mc.execute(
            "INSERT INTO allocation_strategies (name,description,type,geo_weights,sector_weights,reweight_frequency,tax_optimized,include_bonds,bond_pct,max_single_position) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            s
        )
    mysql_conn.commit()
    print(f"Seeded {len(strategies)} allocation strategies")


# ── 9. Seed portfolio ──────────────────────────────────────────────────────
def seed_portfolio(mysql_conn):
    """Seed Kevin's current portfolio positions."""
    mc = mysql_conn.cursor()
    positions = [
        # RRSP
        ('GLD', 'RRSP', 40, 404.78, 40*404.78, '2025-05-15', 'Trailing Stop', 0.10, None, 'Sold 40 @ 404.78'),
        ('VCE.TO', 'RRSP', 20, 73.98, 20*73.98, '2025-05-15', 'Trailing Stop', 0.10, None, 'Bought 20 @ 73.98'),
        ('XIC.TO', 'RRSP', 20, 55.12, 20*55.12, '2025-05-15', 'Trailing Stop', 0.10, None, 'Bought 20 @ 55.12'),
        ('MTY', 'RRSP', 25, 39.47, 25*39.47, '2025-05-15', 'Trailing Stop', 0.10, None, 'BUY 25 @ 39.47, stop 35.47'),
        ('CEF', 'RRSP', 50, 0, 0, None, 'Trailing Stop', 0.10, None, '50 shares, 10% trailing stop, $2 gap buffer'),
        # TFSA
        ('BPF.UN', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('CDZ', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('CM', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('CNR', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('FEZ', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('IEV', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('MX', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('PDC', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('PZA', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('RGLD', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('RUS', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('RY', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('SPEU', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('SRV.UN', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('TFII', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('UL', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
        ('WJX', 'TFSA', 0, 0, 0, None, None, None, None, 'Watchlist'),
    ]
    for p in positions:
        mc.execute(
            "INSERT INTO portfolio (symbol,account_type,shares,cost_basis,cost_basis_total,entry_date,strategy,trailing_stop_pct,last_signal,notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            p
        )
    mysql_conn.commit()
    print(f"Seeded {len(positions)} portfolio positions")


# ── MAIN ────────────────────────────────────────────────────────────────────
def main():
    global MAX_SYMBOLS
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbols', type=int, default=None, help='Max symbols to fetch from yfinance')
    parser.add_argument('--skip-yfinance', action='store_true', help='Skip yfinance fetch, migrate SQLite only')
    parser.add_argument('--skip-schema', action='store_true', help='Skip schema creation')
    args = parser.parse_args()
    MAX_SYMBOLS = args.symbols

    print("=" * 60)
    print("SQLite → MySQL Migration (Schema v4 Slim)")
    print("=" * 60)

    # Connect MySQL
    print("\n[1/7] Connecting to MySQL...")
    mysql_conn = pymysql.connect(**MYSQL)
    print(f"  Connected to {MYSQL['host']}/{MYSQL['database']}")

    # Create schema
    if not args.skip_schema:
        print("\n[2/7] Creating schema...")
        schema_path = os.path.join(WORKSPACE, 'database', 'schema_v4_slim.sql')
        with open(schema_path) as f:
            schema_sql = f.read()
        # Execute each statement
        for stmt in schema_sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--') and not stmt.startswith('/*'):
                try:
                    mysql_conn.cursor().execute(stmt)
                except Exception as e:
                    if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                        pass
                    else:
                        print(f"  ⚠ {e}")
        mysql_conn.commit()
        print("  Schema created")

    # Extract symbols from HTML
    print("\n[3/7] Extracting symbols from CurrentData HTML...")
    symbols = extract_symbols_from_html()

    # Classify and insert symbol_master
    print("\n[4/7] Inserting symbol_master...")
    mc = mysql_conn.cursor()
    for sym, info in symbols.items():
        geo, sector = classify_symbol(sym)
        mc.execute(
            "INSERT IGNORE INTO symbol_master (symbol,geography,sector,snapshot_price,snapshot_date) VALUES (%s,%s,%s,%s,%s)",
            (sym, geo, sector, info.get('snapshot_price'), info.get('snapshot_date'))
        )
    mysql_conn.commit()
    print(f"  Inserted {len(symbols)} symbols into symbol_master")

    # Migrate existing SQLite data
    print("\n[5/7] Migrating SQLite data...")
    total = migrate_sqlite_data(mysql_conn)
    print(f"  Migrated {total} rows")

    # Fetch yfinance and compute indicators
    if not args.skip_yfinance:
        print("\n[6/7] Fetching yfinance data + computing indicators...")
        import pandas as pd
        yf_data = fetch_yfinance_data(symbols, max_symbols=MAX_SYMBOLS)
        total_ind = 0
        for sym, df in yf_data.items():
            insert_stockprices(mysql_conn, sym, df)
            df = compute_indicators(df)
            n = insert_indicators(mysql_conn, sym, df)
            total_ind += n
            print(f"  {sym}: {n} indicator rows")
        print(f"  Total indicators: {total_ind}")
    else:
        print("\n[6/7] Skipping yfinance (--skip-yfinance)")

    # Seed reference data
    print("\n[7/7] Seeding reference data...")
    seed_tax_parameters(mysql_conn)
    seed_allocation_strategies(mysql_conn)
    seed_portfolio(mysql_conn)

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    mc = mysql_conn.cursor()
    for tbl in ['symbol_master', 'stockprices', 'indicators', 'indicator_correlation',
                'tax_parameters', 'allocation_strategies', 'portfolio']:
        mc.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt = mc.fetchone()[0]
        print(f"  {tbl}: {cnt:,} rows")

    mysql_conn.close()


if __name__ == '__main__':
    main()
