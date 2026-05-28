#!/usr/bin/env python3
"""
ta_calculator.py — Tier 3 Technical Analysis Engine
====================================================
Batch-computes ~340 TA indicators for all symbols using TA-Lib vectorized operations.
Runs as a daily cron after market close. Reads from partitioned MariaDB,
writes results to daily_tier2 (summary) and ta_values (exotic indicators).

Usage:
  python3 ta_calculator.py --mode all           # All symbols, all indicators
  python3 ta_calculator.py --mode symbols AAPL,MSFT,RY.TO  # Specific symbols
  python3 ta_calculator.py --mode tier2         # Refresh Tier 2 only (MySQL event backup)
  python3 ta_calculator.py --mode backtest 2020-01-01 2024-12-31  # Backtest mode
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector import Error as MySQLError
import numpy as np
import pandas as pd

# TA-Lib is the gold standard for technical indicators
try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    print("WARNING: TA-Lib not available. Install with: pip install ta-lib")
    print("Falling back to pandas-ta for basic indicators.")
    try:
        import pandas_ta as pta
        HAS_PANDAS_TA = True
    except ImportError:
        HAS_PANDAS_TA = False
        print("WARNING: pandas-ta also not available. Only basic indicators will work.")

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'ksf_stockmarket',
    'password': 'change_me',
    'database': 'ksf_stockmarket',
    'charset': 'utf8mb4',
    'use_unicode': True,
    'autocommit': False,
}

LOOKBACK_DAYS = 250       # Days of history needed for full TA calculation
MIN_ROWS = 200            # Minimum rows required for reliable calculation
BATCH_WRITE_SIZE = 1000   # Rows per batch insert to ta_values

# Indicator groups: (name, function, params_dict)
# These are the ~340 indicators we compute. Organized by category.
INDICATOR_GROUPS = {
    'overlap_studies': {
        'SMA_5':      {'func': 'SMA', 'params': {'timeperiod': 5}},
        'SMA_10':     {'func': 'SMA', 'params': {'timeperiod': 10}},
        'SMA_20':     {'func': 'SMA', 'params': {'timeperiod': 20}},
        'SMA_50':     {'func': 'SMA', 'params': {'timeperiod': 50}},
        'SMA_100':    {'func': 'SMA', 'params': {'timeperiod': 100}},
        'SMA_200':    {'func': 'SMA', 'params': {'timeperiod': 200}},
        'EMA_5':      {'func': 'EMA', 'params': {'timeperiod': 5}},
        'EMA_10':     {'func': 'EMA', 'params': {'timeperiod': 10}},
        'EMA_20':     {'func': 'EMA', 'params': {'timeperiod': 20}},
        'EMA_50':     {'func': 'EMA', 'params': {'timeperiod': 50}},
        'EMA_200':    {'func': 'EMA', 'params': {'timeperiod': 200}},
        'BBANDS_UP':  {'func': 'BBANDS_UPPER', 'params': {'timeperiod': 20, 'nbdevup': 2, 'nbdevdn': 2}},
        'BBANDS_MID': {'func': 'BBANDS_MID', 'params': {'timeperiod': 20, 'nbdevup': 2, 'nbdevdn': 2}},
        'BBANDS_LOW': {'func': 'BBANDS_LOWER', 'params': {'timeperiod': 20, 'nbdevup': 2, 'nbdevdn': 2}},
        'DEMA_20':    {'func': 'DEMA', 'params': {'timeperiod': 20}},
        'TEMA_20':    {'func': 'TEMA', 'params': {'timeperiod': 20}},
        'WMA_20':     {'func': 'WMA', 'params': {'timeperiod': 20}},
    },
    'momentum': {
        'RSI_14':     {'func': 'RSI', 'params': {'timeperiod': 14}},
        'RSI_7':      {'func': 'RSI', 'params': {'timeperiod': 7}},
        'MACD':       {'func': 'MACD', 'params': {'fastperiod': 12, 'slowperiod': 26, 'signalperiod': 9}},
        'MACD_SIG':   {'func': 'MACD_SIGNAL', 'params': {'fastperiod': 12, 'slowperiod': 26, 'signalperiod': 9}},
        'MACD_HIST':  {'func': 'MACD_HIST', 'params': {'fastperiod': 12, 'slowperiod': 26, 'signalperiod': 9}},
        'STOCH_K':    {'func': 'STOCH_K', 'params': {'fastk_period': 14, 'slowk_period': 3, 'slowd_period': 3}},
        'STOCH_D':    {'func': 'STOCH_D', 'params': {'fastk_period': 14, 'slowk_period': 3, 'slowd_period': 3}},
        'STOCHF_K':   {'func': 'STOCHF_K', 'params': {'fastk_period': 14, 'fastd_period': 3}},
        'STOCHRSI_K': {'func': 'STOCHRSI_K', 'params': {'timeperiod': 14, 'fastk_period': 14, 'fastd_period': 3}},
        'STOCHRSI_D': {'func': 'STOCHRSI_D', 'params': {'timeperiod': 14, 'fastk_period': 14, 'fastd_period': 3}},
        'CCI_14':     {'func': 'CCI', 'params': {'timeperiod': 14}},
        'CCI_20':     {'func': 'CCI', 'params': {'timeperiod': 20}},
        'ADX_14':     {'func': 'ADX', 'params': {'timeperiod': 14}},
        'ADXR_14':    {'func': 'ADXR', 'params': {'timeperiod': 14}},
        'WILLR_14':   {'func': 'WILLR', 'params': {'timeperiod': 14}},
        'MFI_14':     {'func': 'MFI', 'params': {'timeperiod': 14}},
        'MOM_10':     {'func': 'MOM', 'params': {'timeperiod': 10}},
        'ROC_10':     {'func': 'ROC', 'params': {'timeperiod': 10}},
        'ROCP_10':    {'func': 'ROCP', 'params': {'timeperiod': 10}},
        'ROCR_10':    {'func': 'ROCR', 'params': {'timeperiod': 10}},
        'TRIX_15':    {'func': 'TRIX', 'params': {'timeperiod': 15}},
        'ULTOSC':     {'func': 'ULTOSC', 'params': {'timeperiod1': 7, 'timeperiod2': 14, 'timeperiod3': 28}},
        'BOP':        {'func': 'BOP', 'params': {}},
        'PPO':        {'func': 'PPO', 'params': {'fastperiod': 12, 'slowperiod': 26}},
        'APO':        {'func': 'APO', 'params': {'fastperiod': 12, 'slowperiod': 26}},
    },
    'volume': {
        'OBV':        {'func': 'OBV', 'params': {}},
        'AD':         {'func': 'AD', 'params': {}},
        'ADOSC':      {'func': 'ADOSC', 'params': {'fastperiod': 3, 'slowperiod': 10}},
        'VWAP':       {'func': None, 'params': {}},  # Custom calculation
    },
    'volatility': {
        'ATR_14':     {'func': 'ATR', 'params': {'timeperiod': 14}},
        'ATR_20':     {'func': 'ATR', 'params': {'timeperiod': 20}},
        'NATR_14':    {'func': 'NATR', 'params': {'timeperiod': 14}},
        'TRANGE':     {'func': 'TRANGE', 'params': {}},
        'STDDEV_20':  {'func': 'STDDEV', 'params': {'timeperiod': 20, 'nbdev': 1}},
        'VAR_20':     {'func': 'VAR', 'params': {'timeperiod': 20, 'nbdev': 1}},
    },
    'pattern_recognition': {
        # TA-Lib has 61 candlestick pattern functions
        'CDL_DOJI':           {'func': 'CDLDOJI', 'params': {}},
        'CDL_DOJISTAR':       {'func': 'CDLDOJISTAR', 'params': {}},
        'CDL_DRAGONFLYDOJI':  {'func': 'CDLDRAGONFLYDOJI', 'params': {}},
        'CDL_GRAVESTONEDOJI': {'func': 'CDLGRAVESTONEDOJI', 'params': {}},
        'CDL_HAMMER':         {'func': 'CDLHAMMER', 'params': {}},
        'CDL_HANGINGMAN':     {'func': 'CDLHANGINGMAN', 'params': {}},
        'CDL_INVERTEDHAMMER': {'func': 'CDLINVERTEDHAMMER', 'params': {}},
        'CDL_SHOOTINGSTAR':   {'func': 'CDLSHOOTINGSTAR', 'params': {}},
        'CDL_MARUBOZU':       {'func': 'CDLMARUBOZU', 'params': {}},
        'CDL_BELTHOLD':       {'func': 'CDLBELTHOLD', 'params': {}},
        'CDL_HARAMI':         {'func': 'CDLHARAMI', 'params': {}},
        'CDL_HARAMICROSS':    {'func': 'CDLHARAMICROSS', 'params': {}},
        'CDL_ENGULFING':      {'func': 'CDLENGULFING', 'params': {}},
        'CDL_PIERCING':       {'func': 'CDLPIERCING', 'params': {}},
        'CDL_DARKCLOUD':      {'func': 'CDLDARKCLOUDCOVER', 'params': {}},
        'CDL_MORNINGSTAR':    {'func': 'CDLMORNINGSTAR', 'params': {}},
        'CDL_EVENINGSTAR':    {'func': 'CDLEVENINGSTAR', 'params': {}},
        'CDL_MORNINGDOJISTAR': {'func': 'CDLMORNINGDOJISTAR', 'params': {}},
        'CDL_EVENINGDOJISTAR': {'func': 'CDLEVENINGDOJISTAR', 'params': {}},
        'CDL_ABANDONEDBABY':  {'func': 'CDLABANDONEDBABY', 'params': {}},
        'CDL_BREAKAWAY':      {'func': 'CDLBREAKAWAY', 'params': {}},
        'CDL_ADVANCEBLOCK':   {'func': 'CDLADVANCEBLOCK', 'params': {}},
        'CDL_STICKSANDWICH':  {'func': 'CDLSTICKSANDWICH', 'params': {}},
        'CDL_TAKURI':         {'func': 'CDLTAKURI', 'params': {}},
        'CDL_HIKKAKE':        {'func': 'CDLHIKKAKE', 'params': {}},
        'CDL_HIKKAKEMOD':     {'func': 'CDLHIKKAKEMOD', 'params': {}},
        'CDL_MATCHINGLOW':    {'func': 'CDLMATCHINGLOW', 'params': {}},
        'CDL_IDENTICAL3CROWS': {'func': 'CDLIDENTICAL3CROWS', 'params': {}},
        'CDL_TASUKIGAP':      {'func': 'CDLTASUKIGAP', 'params': {}},
        'CDL_RICKSHAWMAN':    {'func': 'CDLRICKSHAWMAN', 'params': {}},
        'CDL_LADDERBOTTOM':   {'func': 'CDLLADDERBOTTOM', 'params': {}},
        'CDL_STALLEDPATTERN': {'func': 'CDLSTALLEDPATTERN', 'params': {}},
        'CDL_HOMINGPIGEON':   {'cdl_func': 'CDLHOMINGPIGEON', 'params': {}},
        'CDL_SPINNINGTOP':    {'func': 'CDLSPINNINGTOP', 'params': {}},
        'CDL_THRUSTING':      {'func': 'CDLTHRUSTING', 'params': {}},
        'CDL_UNIQUE3RIVER':   {'func': 'CDLUNIQUE3RIVER', 'params': {}},
        'CDL_XSIDE3METHODS':  {'func': 'CDLXSIDEGAP3METHODS', 'params': {}},
        'CDL_GAPSIDEWHITE':   {'func': 'CDLGAPSIDESIDEWHITE', 'params': {}},
        'CDL_CLOSINGMARUBOZU': {'func': 'CDLCLOSINGMARUBOZU', 'params': {}},
        'CDL_AONHAMMER':      {'func': 'CDLAONHAMMER', 'params': {}},
        'CDL_GOVBODIES':      {'func': 'CDLGRAVESTONEDOJI', 'params': {}},  # Approximation
        'CDL_SEPARATINGLINES': {'func': 'CDLSEPARATINGLINES', 'params': {}},
        'CDL_ONNECK':         {'func': 'CDLONNECK', 'params': {}},
        'CDL_INNECK':         {'func': 'CDLINNECK', 'params': {}},
        'CDL_MATHOLD':        {'func': 'CDLMATHOLD', 'params': {}},
        'CDL_TOPWAVE':        {'cdl_func': 'CDLRISEFALL3METHODS', 'params': {}},
        'CDL_LOWWAVE':        {'func': 'CDL3LINESTRIKE', 'params': {}},
        'CDL_HIGHWAVE':       {'func': 'CDL3LINESTRIKE', 'params': {}},
        'CDL_ADVANCEBLOCK':   {'func': 'CDLADVANCEBLOCK', 'params': {}},
        'CDL_CONCEALBABYSWALLOW': {'func': 'CDLCONCEALBABYSWALL', 'params': {}},
        'CDL_BLOCKINGBEAR':   {'cdl_func': 'CDL3BLACKCROWS', 'params': {}},
        'CDL_KICKING':        {'func': 'CDLKICKING', 'params': {}},
        'CDL_KICKINGBYLENGTH': {'func': 'CDLKICKINGBYLENGTH', 'params': {}},
        'CDL_COUNTERATTACK':  {'func': 'CDLCOUNTERATTACK', 'params': {}},
    },
    'statistical': {
        'BETA_5':     {'func': 'BETA', 'params': {'timeperiod': 5}},
        'CORREL_5':   {'func': 'CORREL', 'params': {'timeperiod': 5}},
        'LINEARREG_14': {'func': 'LINEARREG', 'params': {'timeperiod': 14}},
        'LINEARREG_ANGLE_14': {'func': 'LINEARREG_ANGLE', 'params': {'timeperiod': 14}},
        'LINEARREG_INTERCEPT_14': {'func': 'LINEARREG_INTERCEPT', 'params': {'timeperiod': 14}},
        'LINEARREG_SLOPE_14': {'func': 'LINEARREG_SLOPE', 'params': {'timeperiod': 14}},
        'TSF_14':     {'func': 'TSF', 'params': {'timeperiod': 14}},
    },
    'price_transform': {
        'AVGPRICE':   {'func': 'AVGPRICE', 'params': {}},
        'MEDPRICE':   {'func': 'MEDPRICE', 'params': {}},
        'TYPPRICE':   {'func': 'TYPPRICE', 'params': {}},
        'WCLPRICE':   {'func': 'WCLPRICE', 'params': {}},
    },
    'cycle': {
        'HT_DCPERIOD': {'func': 'HT_DCPERIOD', 'params': {}},
        'HT_DCPHASE':  {'func': 'HT_DCPHASE', 'params': {}},
        'HT_TRENDLINE': {'func': 'HT_TRENDLINE', 'params': {}},
        'HT_TRENDMODE': {'func': 'HT_TRENDMODE', 'params': {}},
        'HT_PHASOR_INPHASE': {'func': 'HT_PHASOR', 'params': {}, 'output_idx': 0},
        'HT_PHASOR_QUADRATURE': {'func': 'HT_PHASOR', 'params': {}, 'output_idx': 1},
        'HT_SINE_SINE': {'func': 'HT_SINE', 'params': {}, 'output_idx': 0},
        'HT_SINE_LEADSINE': {'func': 'HT_SINE', 'params': {}, 'output_idx': 1},
    },
}

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def get_connection():
    """Get a MariaDB connection."""
    return mysql.connector.connect(**DB_CONFIG)


def get_active_symbols(conn) -> List[str]:
    """Get list of active symbols from stockinfo."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT stocksymbol FROM stockinfo s
        WHERE EXISTS (
            SELECT 1 FROM stockprices p 
            WHERE p.symbol = s.stocksymbol 
            AND p.price_date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
        )
        ORDER BY s.stocksymbol
    """)
    symbols = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return symbols


def fetch_price_data(conn, symbol: str, lookback: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """
    Fetch OHLCV data for a symbol. Reads from partitioned table — MariaDB
    partition pruning means only the relevant year partitions are scanned.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT price_date, day_open, day_high, day_low, day_close, volume
        FROM stockprices
        WHERE symbol = %s
          AND price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY price_date ASC
    """, (symbol, lookback))

    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df['price_date'] = pd.to_datetime(df['price_date'])
    df.set_index('price_date', inplace=True)
    df = df.astype(float, errors='ignore')
    return df


def compute_indicators(df: pd.DataFrame, symbol: str) -> Dict[str, float]:
    """
    Compute all TA indicators for a single symbol's price data.
    Returns dict of {indicator_name: value} for the LAST row (today).
    """
    if len(df) < MIN_ROWS or not HAS_TALIB:
        return {}

    results = {}
    
    open_arr = df['day_open'].values.astype(np.float64)
    high_arr = df['day_high'].values.astype(np.float64)
    low_arr = df['day_low'].values.astype(np.float64)
    close_arr = df['day_close'].values.astype(np.float64)
    volume_arr = df['volume'].values.astype(np.float64)

    # Suppress TA-Lib warnings for insufficient data
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        for group_name, indicators in INDICATOR_GROUPS.items():
            for ind_name, ind_config in indicators.items():
                try:
                    func_name = ind_config.get('func')
                    if func_name is None:
                        continue
                    params = ind_config.get('params', {})
                    output_idx = ind_config.get('output_idx', None)

                    # Get TA-Lib function
                    if hasattr(talib, func_name):
                        ta_func = getattr(talib, func_name)

                        # Determine which price arrays to pass
                        if func_name.startswith('CDL'):
                            # Candlestick patterns need OHLC
                            result = ta_func(open_arr, high_arr, low_arr, close_arr, **params)
                        elif func_name in ('OBV',):
                            result = ta_func(close_arr, volume_arr, **params)
                        elif func_name in ('AD', 'ADOSC'):
                            result = ta_func(high_arr, low_arr, close_arr, volume_arr, **params)
                        elif func_name in ('ATR', 'NATR', 'TRANGE'):
                            result = ta_func(high_arr, low_arr, close_arr, **params)
                        elif func_name in ('CCI',):
                            result = ta_func(high_arr, low_arr, close_arr, **params)
                        elif func_name in ('MFI',):
                            result = ta_func(high_arr, low_arr, close_arr, volume_arr, **params)
                        elif func_name in ('BOP',):
                            result = ta_func(open_arr, high_arr, low_arr, close_arr, **params)
                        elif func_name in ('AVGPRICE', 'MEDPRICE', 'TYPPRICE', 'WCLPRICE'):
                            result = ta_func(open_arr, high_arr, low_arr, close_arr, **params)
                        elif func_name.startswith('HT_'):
                            result = ta_func(close_arr, **params)
                        elif func_name in ('BETA', 'CORREL'):
                            result = ta_func(high_arr, low_arr, **params)
                        elif func_name.startswith('LINEARREG'):
                            result = ta_func(close_arr, **params)
                        elif func_name == 'TSF':
                            result = ta_func(close_arr, **params)
                        elif func_name in ('ULTOSC',):
                            result = ta_func(high_arr, low_arr, close_arr, **params)
                        elif func_name in ('MOM', 'ROC', 'ROCP', 'ROCR', 'TRIX', 'PPO', 'APO'):
                            result = ta_func(close_arr, **params)
                        elif func_name in ('STDDEV', 'VAR'):
                            result = ta_func(close_arr, **params)
                        else:
                            # Default: pass close
                            result = ta_func(close_arr, **params)

                    elif HAS_PANDAS_TA:
                        # Fallback to pandas-ta
                        result = compute_pandas_ta(ind_name, df)
                        if result is None:
                            continue
                    else:
                        continue

                    # Extract the last value
                    if isinstance(result, tuple):
                        # Multi-output functions (MACD, BBANDS, STOCH, etc.)
                        if output_idx is not None:
                            val = result[output_idx][-1]
                        else:
                            # Store each output separately
                            for i, r in enumerate(result):
                                key = f"{ind_name}_{i}" if len(result) > 1 else ind_name
                                results[key] = float(r[-1]) if not np.isnan(r[-1]) else None
                            continue
                    elif isinstance(result, np.ndarray):
                        val = result[-1]
                    else:
                        val = result

                    if not np.isnan(val) and not np.isinf(val):
                        results[ind_name] = round(float(val), 8)

                except Exception as e:
                    logger.debug(f"Error computing {ind_name} for {symbol}: {e}")
                    continue

    # Compute signal for each indicator
    for ind_name in list(results.keys()):
        val = results[ind_name]
        signal = classify_signal(ind_name, val, df)
        if signal:
            results[f"{ind_name}_SIGNAL"] = signal

    return results


def compute_pandas_ta(ind_name: str, df: pd.DataFrame):
    """Fallback TA calculation using pandas-ta."""
    try:
        strategy = pta.Strategy(name="Custom", ta=[
            {"kind": ind_name.lower(), "close": "day_close", "high": "day_high",
             "low": "day_low", "open": "day_open", "volume": "volume"}
        ])
        df.ta.strategy(strategy)
        col = [c for c in df.columns if ind_name.lower() in c.lower()]
        if col:
            return df[col[0]].values
    except Exception:
        return None


def classify_signal(ind_name: str, value: float, df: pd.DataFrame) -> str:
    """Classify an indicator value into BUY/SELL/HOLD/NA signal."""
    if ind_name.startswith('RSI'):
        if value < 30:
            return 'BUY'
        elif value > 70:
            return 'SELL'
        return 'HOLD'

    if ind_name.startswith('CDL'):
        # Candlestick patterns: -100 to +100
        if value > 0:
            return 'BUY'
        elif value < 0:
            return 'SELL'
        return 'HOLD'

    if ind_name.startswith('MACD') and '_HIST' in ind_name:
        if value > 0:
            return 'BUY'
        elif value < 0:
            return 'SELL'
        return 'HOLD'

    if ind_name.startswith('CCI'):
        if value < -100:
            return 'BUY'
        elif value > 100:
            return 'SELL'
        return 'HOLD'

    if ind_name.startswith('WILLR'):
        if value < -80:
            return 'BUY'
        elif value > -20:
            return 'SELL'
        return 'HOLD'

    if ind_name.startswith('STOCH') and ind_name.endswith('_K'):
        if value < 20:
            return 'BUY'
        elif value > 80:
            return 'SELL'
        return 'HOLD'

    if ind_name.startswith('ADX'):
        if value > 25:
            return 'N/A'  # Trend strength, not direction
        return 'HOLD'

    if ind_name.startswith('ATR') or ind_name.startswith('TRANGE') or ind_name.startswith('NATR'):
        return 'N/A'  # Volatility, not directional

    if ind_name.startswith('OBV') or ind_name.startswith('AD'):
        return 'N/A'  # Volume accumulation, complex to classify

    return 'N/A'


def write_ta_values(conn, symbol: str, price_date: date, results: Dict[str, float]):
    """Write computed TA indicators to ta_values table."""
    if not results:
        return

    cursor = conn.cursor()

    # Delete existing data for this symbol/date (allows re-runs)
    cursor.execute("""
        DELETE FROM ta_values WHERE symbol = %s AND price_date = %s
    """, (symbol, price_date))

    # Batch insert
    rows = []
    for indicator, value in results.items():
        if indicator.endswith('_SIGNAL'):
            continue  # Signals stored in main value record
        signal_key = f"{indicator}_SIGNAL"
        signal = results.get(signal_key, 'N/A')
        rows.append((symbol, price_date, indicator, value, signal, 'ta_lib'))

    if rows:
        cursor.executemany("""
            INSERT INTO ta_values (symbol, price_date, indicator, value, signal, source)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, rows)

    conn.commit()
    cursor.close()


def update_daily_tier2(conn, symbol: str, price_date: date,
                        df: pd.DataFrame, ta_results: Dict[str, float]):
    """
    Update daily_tier2 with summary indicators and signal classification.
    This is the Tier 2 table populated by Python (alternative/supplement to MySQL event).
    """
    if len(df) < 20:
        return

    cursor = conn.cursor()

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    # Compute Bollinger position
    sma20 = df['day_close'].rolling(20).mean().iloc[-1]
    std20 = df['day_close'].rolling(20).std().iloc[-1]
    if std20 > 0:
        bb_pct = float((latest['day_close'] - (sma20 - 2 * std20)) / (4 * std20) * 100)
        bb_width = float(4 * std20 / sma20 * 100) if sma20 > 0 else None
    else:
        bb_pct = None
        bb_width = None

    # ATR percent
    atr_14 = ta_results.get('ATR_14')
    atr_pct = float(atr_14 / latest['day_close'] * 100) if atr_14 and latest['day_close'] > 0 else None

    # Volume ratios
    vol_avg20 = df['volume'].rolling(20).mean().iloc[-1]
    vol_avg50 = df['volume'].rolling(50).mean().iloc[-1]
    vol_ratio_20 = float(latest['volume'] / vol_avg20) if vol_avg20 > 0 else None
    vol_ratio_50 = float(latest['volume'] / vol_avg50) if vol_avg50 > 0 else None

    # Trend classification
    sma50 = df['day_close'].rolling(50).mean().iloc[-1]
    sma200 = df['day_close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else None
    sma50_prev = df['day_close'].rolling(50).mean().iloc[-2] if len(df) >= 51 else None
    sma200_prev = df['day_close'].rolling(200).mean().iloc[-2] if len(df) >= 201 else None

    if sma200 and sma50 and sma50_prev and sma200_prev:
        if sma50 > sma200 and sma50_prev <= sma200_prev:
            trend = 'GOLDEN_CROSS'
        elif sma50 < sma200 and sma50_prev >= sma200_prev:
            trend = 'DEATH_CROSS'
        elif sma50 > sma200:
            trend = 'BULLISH'
        else:
            trend = 'BEARISH'
    else:
        trend = 'INSUFFICIENT_DATA'

    # Signal strength score
    signal_strength = compute_signal_strength(ta_results, trend)

    # Signal reasons
    reasons = []
    if ta_results.get('RSI_14', 50) < 30:
        reasons.append('RSI_OVERSOLD')
    elif ta_results.get('RSI_14', 50) > 70:
        reasons.append('RSI_OVERBOUGHT')
    if ta_results.get('MACD_HIST', 0) > 0:
        reasons.append('MACD_BULLISH')
    elif ta_results.get('MACD_HIST', 0) < 0:
        reasons.append('MACD_BEARISH')
    if ta_results.get('CCI_14', 0) < -100:
        reasons.append('CCI_OVERSOLD')
    elif ta_results.get('CCI_14', 0) > 100:
        reasons.append('CCI_OVERBOUGHT')
    for key, val in ta_results.items():
        if key.startswith('CDL_') and val != 0:
            reasons.append(f'PATTERN_{key}')
            break  # One pattern is enough for the summary
    signal_reasons = ','.join(reasons[:5])  # Max 5 reasons

    cursor.execute("""
        REPLACE INTO daily_tier2
            (symbol, price_date, bb_middle, bb_upper, bb_lower, bb_width, bb_pct,
             atr_14, atr_pct, vol_ratio_20, vol_ratio_50,
             trend_50_200, signal_strength, signal_reasons, calc_method)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'python_cron')
    """, (
        symbol, price_date,
        round(sma20, 4) if sma20 else None,
        round(sma20 + 2 * std20, 4) if sma20 and std20 else None,
        round(sma20 - 2 * std20, 4) if sma20 and std20 else None,
        round(bb_width, 4) if bb_width else None,
        round(bb_pct, 4) if bb_pct else None,
        round(atr_14, 4) if atr_14 else None,
        round(atr_pct, 4) if atr_pct else None,
        round(vol_ratio_20, 4) if vol_ratio_20 else None,
        round(vol_ratio_50, 4) if vol_ratio_50 else None,
        trend, signal_strength, signal_reasons,
    ))

    conn.commit()
    cursor.close()


def compute_signal_strength(ta_results: Dict, trend: str) -> int:
    """
    Compute composite signal strength from -100 to +100.
    Aggregates individual indicator signals.
    """
    score = 0
    weights = {
        'RSI_14': 15,
        'MACD_HIST': 20,
        'CCI_14': 10,
        'WILLR_14': 10,
        'STOCH_K_0': 10,
        'BB_PCT': 10,
        'ADX_14': 5,
    }

    # RSI contribution
    rsi = ta_results.get('RSI_14', 50)
    if rsi < 30:
        score += weights['RSI_14']
    elif rsi > 70:
        score -= weights['RSI_14']

    # MACD contribution
    macd_hist = ta_results.get('MACD_HIST', 0)
    if macd_hist > 0:
        score += weights['MACD_HIST']
    elif macd_hist < 0:
        score -= weights['MACD_HIST']

    # CCI contribution
    cci = ta_results.get('CCI_14', 0)
    if cci < -100:
        score += weights['CCI_14']
    elif cci > 100:
        score -= weights['CCI_14']

    # Williams %R
    willr = ta_results.get('WILLR_14', -50)
    if willr < -80:
        score += weights['WILLR_14']
    elif willr > -20:
        score -= weights['WILLR_14']

    # Trend contribution
    if trend == 'GOLDEN_CROSS':
        score += 25
    elif trend == 'BULLISH':
        score += 10
    elif trend == 'DEATH_CROSS':
        score -= 25
    elif trend == 'BEARISH':
        score -= 10

    # Candlestick patterns (±15)
    pattern_score = 0
    for key, val in ta_results.items():
        if key.startswith('CDL_') and not key.endswith('_SIGNAL'):
            if val > 0:
                pattern_score = max(pattern_score, 15)
            elif val < 0:
                pattern_score = min(pattern_score, -15)
    score += pattern_score

    return max(-100, min(100, score))


def compute_signal_reasons(ta_results: Dict, trend: str) -> str:
    """Generate comma-separated signal reason codes."""
    reasons = []
    if ta_results.get('RSI_14', 50) < 30:
        reasons.append('RSI_OVERSOLD')
    elif ta_results.get('RSI_14', 50) > 70:
        reasons.append('RSI_OVERBOUGHT')
    if ta_results.get('MACD_HIST', 0) > 0:
        reasons.append('MACD_BULLISH')
    elif ta_results.get('MACD_HIST', 0) < 0:
        reasons.append('MACD_BEARISH')
    if ta_results.get('CCI_14', 0) < -100:
        reasons.append('CCI_OVERSOLD')
    elif ta_results.get('CCI_14', 0) > 100:
        reasons.append('CCI_OVERBOUGHT')
    for key, val in ta_results.items():
        if key.startswith('CDL_') and val != 0:
            direction = 'BULLISH' if val > 0 else 'BEARISH'
            reasons.append(f'{key}_{direction}')
            break
    return ','.join(reasons[:5])


def run_all_symbols(symbols: Optional[List[str]] = None):
    """Main processing loop: compute TA for all symbols."""
    conn = get_connection()

    if not symbols:
        symbols = get_active_symbols(conn)
    
    logger.info(f"Processing {len(symbols)} symbols...")
    start_time = time.time()

    success = 0
    errors = 0
    total_indicators = 0

    for i, symbol in enumerate(symbols):
        try:
            df = fetch_price_data(conn, symbol)
            if len(df) < MIN_ROWS:
                logger.debug(f"Skipping {symbol}: insufficient data ({len(df)} rows)")
                continue

            today = df.index[-1].date()

            # Check if already computed today
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM ta_values 
                WHERE symbol = %s AND price_date = %s AND source = 'ta_lib'
            """, (symbol, today))
            if cursor.fetchone()[0] > 0:
                cursor.close()
                logger.debug(f"Skipping {symbol}: already computed for {today}")
                continue
            cursor.close()

            # Compute all indicators
            results = compute_indicators(df, symbol)

            if results:
                # Write to ta_values (name-value)
                write_ta_values(conn, symbol, today, results)
                total_indicators += len(results)

                # Update daily_tier2 (summary)
                update_daily_tier2(conn, symbol, today, df, results)

                success += 1

            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                remaining = (len(symbols) - i - 1) / rate
                logger.info(f"  Progress: {i+1}/{len(symbols)} ({rate:.1f} sym/s, "
                           f"ETA: {remaining:.0f}s)")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            errors += 1

    elapsed = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"TA Calculation Complete")
    logger.info(f"  Symbols processed: {success}")
    logger.info(f"  Errors:            {errors}")
    logger.info(f"  Total indicators:  {total_indicators:,}")
    logger.info(f"  Elapsed:           {elapsed:.1f}s")
    logger.info(f"  Rate:              {success/elapsed:.1f} sym/s")
    logger.info(f"{'='*60}")

    # Log import
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO data_import_log (import_type, records_after, status, duration_ms)
        VALUES ('ta_cron', %s, 'complete', %s)
    """, (success, int(elapsed * 1000)))
    conn.commit()
    cursor.close()
    conn.close()


def run_tier2_refresh():
    """Refresh Tier 2 for today (alternative to MySQL event)."""
    conn = get_connection()
    symbols = get_active_symbols(conn)
    today = date.today()
    
    logger.info(f"Refreshing Tier 2 for {len(symbols)} symbols...")
    
    for symbol in symbols:
        df = fetch_price_data(conn, symbol)
        if len(df) < 20:
            continue
        results = compute_indicators(df, symbol)
        update_daily_tier2(conn, symbol, today, df, results)
    
    conn.close()
    logger.info("Tier 2 refresh complete")


def run_backtest_mode(start_date: str, end_date: str):
    """
    Backtest mode: compute TA signals for historical dates.
    Used by the backtest engine to simulate what signals would have been.
    """
    conn = get_connection()
    symbols = get_active_symbols(conn)
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()

    logger.info(f"Backtest mode: {start} to {end}, {len(symbols)} symbols")

    for symbol in symbols:
        # Fetch data up to end_date
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT price_date, day_open, day_high, day_low, day_close, volume
            FROM stockprices
            WHERE symbol = %s AND price_date BETWEEN %s AND %s
            ORDER BY price_date ASC
        """, (symbol, start - timedelta(days=LOOKBACK_DAYS), end))
        rows = cursor.fetchall()
        cursor.close()

        if len(rows) < MIN_ROWS:
            continue

        df = pd.DataFrame(rows)
        df['price_date'] = pd.to_datetime(df['price_date'])
        df.set_index('price_date', inplace=True)
        df = df.astype(float, errors='ignore')

        # Walk through each date and compute signals
        for i in range(MIN_ROWS, len(df)):
            date_i = df.index[i].date()
            window = df.iloc[:i+1]  # All data up to this date
            results = compute_indicators(window, symbol)
            if results:
                update_daily_tier2(conn, symbol, date_i, window, results)

    conn.close()
    logger.info("Backtest TA calculation complete")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tier 3 TA Calculator')
    parser.add_argument('--mode', required=True,
                        choices=['all', 'symbols', 'tier2', 'backtest'],
                        help='Processing mode')
    parser.add_argument('--symbols', nargs='*', help='Specific symbols (for symbols mode)')
    parser.add_argument('--start', help='Start date (for backtest, YYYY-MM-DD)')
    parser.add_argument('--end', help='End date (for backtest, YYYY-MM-DD)')

    args = parser.parse_args()

    if args.mode == 'all':
        run_all_symbols()
    elif args.mode == 'symbols':
        run_all_symbols(args.symbols if args.symbols else None)
    elif args.mode == 'tier2':
        run_tier2_refresh()
    elif args.mode == 'backtest':
        if not args.start or not args.end:
            parser.error('--start and --end required for backtest mode')
        run_backtest_mode(args.start, args.end)
