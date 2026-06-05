#!/usr/bin/env python3
"""
daily_pipeline.py — Stage 1 & 2 of the investment agent pipeline.

STAGE 1: Daily Price Download
  - For every active symbol in symbol_master, fetch today's OHLCV from yfinance
  - Includes dividend actions, stock splits
  - Store in stockprices table
  - Respects is_active flag (inactive symbols = keep history, skip fetch)

STAGE 2: Indicator Calculation
  - For each day's data added, compute 140+ technical indicators using TA-Lib
  - Store in indicators_json table as wide-column format (one column per indicator)
  - Inactive symbols are NOT processed for new indicators

Usage:
    python3 daily_pipeline.py --mode daily       # Update today's prices
    python3 daily_pipeline.py --mode backfill --symbol RY --start 2020-01-01 --end 2024-12-31
    python3 daily_pipeline.py --mode indicators   # Calculate new indicators
    python3 daily_pipeline.py --mode status       # Show data freshness

Database:
    Uses db adapter layer (python/db/) — set DB_BACKEND=sqlite for testing.
    Config-driven via config.yaml (database.engine, database.host, etc.)
"""

import sys
import os
import json
import argparse
import time
import datetime
import logging

import numpy as np

# ── Path setup ──────────────────────────────────────────────────────────────
# Add python/ to path so we can import db/, config_loader, etc.
_PYTHON_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _PYTHON_DIR)

from config_loader import Config
from db import Database, MySQLAdapter, SQLiteAdapter

log = logging.getLogger(__name__)

# ── Optional dependencies ───────────────────────────────────────────────────
YFINANCE_AVAILABLE = False
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    pass

TALIB_AVAILABLE = False
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    pass


def _build_db():
    """
    Build the Database instance from config.yaml.
    Config-driven: set database.engine to 'mysql' or 'sqlite'.
    Can also override with DB_BACKEND env var (like db_connector.py did).
    """
    env_backend = os.environ.get('DB_BACKEND', '').lower()

    if env_backend == 'sqlite':
        db_path = os.environ.get('SQLITE_PATH',
                  os.path.join(_PYTHON_DIR, '..', 'data', 'ksf_stockmarket.db'))
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return Database(SQLiteAdapter(db_path))
    elif env_backend == 'mysql':
        cfg = Config(os.path.join(_PYTHON_DIR, '..', 'config.yaml'))
        db_cfg = cfg.data
        return Database(MySQLAdapter(
            host=getattr(db_cfg, 'db_host', 'ksfraser.ca'),
            user=getattr(db_cfg, 'db_user', 'ksfraser_stockmarket'),
            password=cfg.db_password,
            database=getattr(db_cfg, 'db_name', 'ksfraser_stock_market'),
            port=int(getattr(db_cfg, 'port', 3306)),
        ))
    else:
        # Fallback: load from vault via config_loader
        cfg = Config(os.path.join(_PYTHON_DIR, '..', 'config.yaml'))
        return Database(MySQLAdapter(
            host='ksfraser.ca', user='ksfraser_stockmarket',
            password=cfg.db_password, database='ksfraser_stock_market'
        ))


# ── Stage 1: Daily Price Download ──────────────────────────────────────────

class DailyPriceDownloader:
    """
    Downloads daily OHLCV data for all active symbols in symbol_master.
    Handles dividends, splits, and ensures no duplicate entries.

    Usage:
        db = _build_db()
        downloader = DailyPriceDownloader(db)
        downloader.run_daily_update()
    """

    def __init__(self, db: Database):
        self.db = db

    def get_active_symbols(self):
        """Get all active symbols from symbol_master (respects is_active flag)."""
        with self.db.connect() as conn:
            return conn.fetchall(
                "SELECT symbol, name, exchange FROM symbol_master "
                "WHERE is_active = 1 ORDER BY symbol"
            )

    def get_latest_date(self, symbol):
        """Get the most recent price date for a symbol."""
        with self.db.connect() as conn:
            row = conn.fetchone(
                "SELECT MAX(price_date) as latest FROM stockprices WHERE symbol = %s",
                (symbol,)
            )
            latest = row['latest'] if row else None
            # Handle both string and date types
            if latest is None:
                return None
            return str(latest) if not isinstance(latest, str) else latest

    def download_today(self, symbol):
        """
        Fetch latest data for a symbol from yfinance.
        Returns list of dicts: {date, open, high, low, close, volume}.
        """
        if not YFINANCE_AVAILABLE:
            log.warning(f"yfinance not available — cannot download {symbol}")
            return []

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                return []

            results = []
            for date_idx, row in hist.iterrows():
                date_str = date_idx.strftime('%Y-%m-%d')
                results.append({
                    'date': date_str,
                    'open': float(row['Open']) if not np.isnan(row['Open']) else 0,
                    'high': float(row['High']) if not np.isnan(row['High']) else 0,
                    'low': float(row['Low']) if not np.isnan(row['Low']) else 0,
                    'close': float(row['Close']) if not np.isnan(row['Close']) else 0,
                    'volume': int(row['Volume']) if not np.isnan(row['Volume']) else 0,
                })
            return results

        except Exception as e:
            log.error(f"Error downloading {symbol}: {e}")
            return []

    def download_dividends(self, symbol):
        """Fetch dividend history for a symbol."""
        if not YFINANCE_AVAILABLE:
            return []
        try:
            ticker = yf.Ticker(symbol)
            divs = ticker.dividends
            results = []
            for date_idx, amount in divs.items():
                results.append({
                    'date': date_idx.strftime('%Y-%m-%d'),
                    'amount': float(amount)
                })
            return results
        except Exception:
            return []

    def download_splits(self, symbol):
        """Fetch stock split history for a symbol."""
        if not YFINANCE_AVAILABLE:
            return []
        try:
            ticker = yf.Ticker(symbol)
            splits = ticker.splits
            results = []
            for date_idx, ratio in splits.items():
                results.append({
                    'date': date_idx.strftime('%Y-%m-%d'),
                    'ratio': float(ratio)
                })
            return results
        except Exception:
            return []

    def upsert_prices(self, symbol, prices):
        """
        Insert or update price rows for a symbol.
        Uses INSERT ... ON DUPLICATE KEY UPDATE.
        Returns number of new rows added.
        """
        if not prices:
            return 0

        with self.db.connect() as conn:
            # Check which dates already exist
            dates = [p['date'] for p in prices]
            placeholders = ','.join(['%s'] * len(dates))
            existing_rows = conn.fetchall(
                f"SELECT price_date FROM stockprices WHERE symbol = %s AND price_date IN ({placeholders})",
                [symbol] + dates
            )
            existing = set(str(r['price_date']) for r in existing_rows)

        new_prices = [p for p in prices if p['date'] not in existing]
        if not new_prices:
            return 0

        sql = (
            "INSERT INTO stockprices (symbol, price_date, open, high, low, close, volume) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE open=%s, high=%s, low=%s, close=%s, volume=%s"
        )

        with self.db.connect() as conn:
            for p in new_prices:
                conn.execute(sql, (
                    symbol, p['date'], p['open'], p['high'], p['low'], p['close'], p['volume'],
                    p['open'], p['high'], p['low'], p['close'], p['volume']
                ))

        return len(new_prices)

    def run_daily_update(self, verbose=True):
        """
        Main daily update: fetch today's prices for all active symbols.
        """
        symbols = self.get_active_symbols()
        total_new = 0
        errors = []

        if verbose:
            print(f"Daily price update: {len(symbols)} active symbols")
            print(f"Date: {datetime.date.today()}")

        for i, sym_row in enumerate(symbols):
            symbol = sym_row['symbol']

            # Rate limiting: sleep briefly every 10 symbols
            if i > 0 and i % 10 == 0:
                time.sleep(1)

            prices = self.download_today(symbol)
            n_new = self.upsert_prices(symbol, prices)
            total_new += n_new

            if verbose and n_new > 0:
                print(f"  [{i+1}/{len(symbols)}] {symbol}: +{n_new} new rows")
            elif verbose and i % 50 == 0:
                print(f"  [{i+1}/{len(symbols)}] {symbol}: up to date")

        if verbose:
            print(f"\nTotal: {total_new} new price rows added")

        return total_new, errors

    def backfill_symbol(self, symbol, start_date, end_date, verbose=True):
        """
        Backfill historical data for a symbol. Used when adding a new symbol.
        Inactive symbols can still be backfilled (admin override).
        """
        if not YFINANCE_AVAILABLE:
            print("yfinance not available")
            return 0

        if verbose:
            print(f"Backfilling {symbol}: {start_date} to {end_date}")

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"  No data returned for {symbol}")
                return 0

            prices = []
            for date_idx, row in hist.iterrows():
                date_str = date_idx.strftime('%Y-%m-%d')
                prices.append({
                    'date': date_str,
                    'open': float(row['Open']) if not np.isnan(row['Open']) else 0,
                    'high': float(row['High']) if not np.isnan(row['High']) else 0,
                    'low': float(row['Low']) if not np.isnan(row['Low']) else 0,
                    'close': float(row['Close']) if not np.isnan(row['Close']) else 0,
                    'volume': int(row['Volume']) if not np.isnan(row['Volume']) else 0,
                })

            n = self.upsert_prices(symbol, prices)
            if verbose:
                print(f"  Added {n} price rows for {symbol}")

            # Also download dividends and splits
            divs = self.download_dividends(symbol)
            splits = self.download_splits(symbol)
            if verbose:
                print(f"  Dividends: {len(divs)}, Splits: {len(splits)}")

            return n

        except Exception as e:
            print(f"  Error backfilling {symbol}: {e}")
            return 0

    def get_status(self):
        """
        Show update status: which symbols need data.
        Returns dict with status info.
        Uses a single query for all symbols (not N+1 queries).
        """
        today = datetime.date.today().strftime('%Y-%m-%d')
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        # Single query: get all active symbols with their latest price date
        with self.db.connect() as conn:
            rows = conn.fetchall("""
                SELECT sm.symbol, MAX(sp.price_date) as latest
                FROM symbol_master sm
                LEFT JOIN stockprices sp ON sm.symbol = sp.symbol
                WHERE sm.is_active = 1
                GROUP BY sm.symbol
                ORDER BY sm.symbol
            """)

        status = {
            'total_symbols': len(rows),
            'with_data': 0,
            'without_data': 0,
            'up_to_date': 0,
            'needs_update': 0,
            'details': []
        }

        for row in rows:
            symbol = row['symbol']
            latest = str(row['latest']) if row['latest'] else None

            if latest is None:
                status['without_data'] += 1
                status['details'].append({'symbol': symbol, 'status': 'no_data', 'latest': None})
            else:
                status['with_data'] += 1
                if latest >= yesterday:
                    status['up_to_date'] += 1
                    status['details'].append({'symbol': symbol, 'status': 'current', 'latest': latest})
                else:
                    status['needs_update'] += 1
                    status['details'].append({'symbol': symbol, 'status': 'stale', 'latest': latest})

        return status


# ── Stage 2: Indicator Calculation ──────────────────────────────────────────

class IndicatorCalculator:
    """
    Calculates technical indicators for symbols with new price data.
    Reads OHLCV from stockprices table, writes to indicators_json table.

    Indicator data format: wide-column (140+ columns, one per indicator).
    Each row = one date × one symbol. TA-Lib computed, stored per-column.

    Usage:
        db = _build_db()
        calc = IndicatorCalculator(db)
        calc.calculate_all_missing()
    """

    # ── Indicator column names (must match table columns) ──
    INDICATOR_COLUMNS = [
        # Overlap Studies
        'sma_5', 'sma_10', 'sma_20', 'sma_50', 'sma_100', 'sma_200',
        'ema_5', 'ema_10', 'ema_20', 'ema_50', 'ema_100', 'ema_200',
        'bb_10_2_0_upper', 'bb_10_2_0_mid', 'bb_10_2_0_lower',
        'bb_20_2_0_upper', 'bb_20_2_0_mid', 'bb_20_2_0_lower',
        'bb_10_2_5_upper', 'bb_10_2_5_mid', 'bb_10_2_5_lower',
        'bb_20_2_5_upper', 'bb_20_2_5_mid', 'bb_20_2_5_lower',
        # Momentum
        'rsi_7', 'rsi_14', 'rsi_21',
        'adx_7', 'adx_14', 'adx_21',
        'adxr_7', 'adxr_14', 'adxr_21',
        'macd', 'macd_signal', 'macd_hist',
        'apo_7', 'apo_14', 'apo_21',
        'aroonosc_7', 'aroonosc_14', 'aroonosc_21',
        'cci_7', 'cci_14', 'cci_21',
        'cmo_7', 'cmo_14', 'cmo_21',
        'mfi_7', 'mfi_14', 'mfi_21',
        'ppo_7', 'ppo_14', 'ppo_21',
        'roc_7', 'roc_14', 'roc_21',
        'rocp_7', 'rocp_14', 'rocp_21',
        'rocr_7', 'rocr_14', 'rocr_21',
        'rocr100_7', 'rocr100_14', 'rocr100_21',
        'trix_7', 'trix_14', 'trix_21',
        'willr_7', 'willr_14', 'willr_21',
        'stoch_k_14', 'stoch_d_14',
        'stoch_k_5', 'stoch_d_5',
        # Volume
        'ad', 'adosc', 'obv',
        # Volatility
        'atr_7', 'atr_14', 'atr_20',
        'natr_7', 'natr_14', 'natr_20',
        'trange',
        # Price Transform
        'avgprice', 'medprice', 'typprice', 'wclprice',
        # Cycle
        'ht_dcperiod', 'ht_dcphase',
        'ht_phasor_inphase', 'ht_phasor_quadrature',
        'ht_sine', 'ht_leadsine', 'ht_trendmode',
        # Candlestick (28 patterns from TA-Lib)
        'cdl_2crows', 'cdl_3blackcrows', 'cdl_3inside', 'cdl_3linestrike',
        'cdl_3outside', 'cdl_3starsinsouth', 'cdl_3whitesoldiers',
        'cdl_advancedblock', 'cdl_belthold', 'cdl_breakaway',
        'cdl_closingmarubozu', 'cdl_concealbabyswall', 'cdl_counterattack',
        'cdl_darkcloudcover', 'cdl_doji', 'cdl_dojistar',
        'cdl_dragonflydoji', 'cdl_engulfing', 'cdl_eveningdojistar',
        'cdl_eveningstar', 'cdl_gapsidesidewhite', 'cdl_gravestonedoji',
        'cdl_hammer', 'cdl_hangingman', 'cdl_harami', 'cdl_haramicross',
        'cdl_highwave', 'cdl_hikkake', 'cdl_hikkakemod',
        'cdl_homingpigeon', 'cdl_identical3crows', 'cdl_inneck',
        'cdl_invertedhammer', 'cdl_kicking', 'cdl_kickingbylength',
        'cdl_ladderbottom', 'cdl_longleggeddoji', 'cdl_longline',
        'cdl_marubozu', 'cdl_matchinglow', 'cdl_matin',
        'cdl_morningdojistar', 'cdl_morningstar', 'cdl_onneck',
        'cdl_piercing', 'cdl_rickshawman', 'cdl_risefall3methods',
        'cdl_separatinglines', 'cdl_shootingstar', 'cdl_shortline',
        'cdl_spinningtop', 'cdl_stalledpattern', 'cdl_sticksandwich',
        'cdl_takuri', 'cdl_tasukigap', 'cdl_thrusting',
        'cdl_tristar', 'cdl_unique3river', 'cdl_upsidegap2crows',
        'cdl_xsidegap3methods',
    ]

    def __init__(self, db: Database):
        self.db = db

    def get_symbols_needing_indicators(self, lookback_days=30):
        """
        Find symbols that have recent price data but missing indicator data.
        Only checks active symbols.
        """
        with self.db.connect() as conn:
            rows = conn.fetchall("""
                SELECT DISTINCT sp.symbol
                FROM stockprices sp
                INNER JOIN symbol_master sm ON sp.symbol = sm.symbol AND sm.is_active = 1
                LEFT JOIN indicators_json ij ON sp.symbol = ij.symbol AND sp.price_date = ij.price_date
                WHERE sp.price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                AND ij.id IS NULL
                ORDER BY sp.symbol
            """, (lookback_days,))
            return [r['symbol'] for r in rows]

    def load_ohlcv(self, symbol, limit_days=800):
        """
        Load OHLCV data for indicator calculation.
        Returns dict with numpy arrays: {dates, open, high, low, close, volume}
        Returns None if insufficient data.
        """
        with self.db.connect() as conn:
            rows = conn.fetchall("""
                SELECT price_date, open, high, low, close, volume
                FROM stockprices
                WHERE symbol = %s
                ORDER BY price_date DESC
                LIMIT %s
            """, (symbol, limit_days))

        if not rows or len(rows) < 250:
            return None

        # Oldest first for TA-Lib (queries return DESC, so reverse)
        rows.reverse()

        return {
            'dates': [str(r['price_date']) for r in rows],
            'open': np.array([float(r['open']) for r in rows]),
            'high': np.array([float(r['high']) for r in rows]),
            'low': np.array([float(r['low']) for r in rows]),
            'close': np.array([float(r['close']) for r in rows]),
            'volume': np.array([float(r['volume']) for r in rows]),
        }

    def calculate_all_indicators(self, ohlcv):
        """
        Calculate 140+ technical indicators using TA-Lib (or numpy fallback).
        Returns dict of {indicator_name: np.array}.
        """
        if not TALIB_AVAILABLE:
            return self._calculate_indicators_numpy(ohlcv)

        close = ohlcv['close']
        high = ohlcv['high']
        low = ohlcv['low']
        volume = ohlcv['volume']
        open_price = ohlcv['open']

        indicators = {}

        # ── Overlap Studies ──
        for period in [5, 10, 20, 50, 100, 200]:
            indicators[f'sma_{period}'] = talib.SMA(close, timeperiod=period)
            indicators[f'ema_{period}'] = talib.EMA(close, timeperiod=period)

        for period in [10, 20]:
            for std in [2.0, 2.5]:
                upper, mid, lower = talib.BBANDS(close, timeperiod=period, nbdevup=std, nbdevdn=std)
                indicators[f'bb_{period}_{str(std).replace(".", "_")}_upper'] = upper
                indicators[f'bb_{period}_{str(std).replace(".", "_")}_mid'] = mid
                indicators[f'bb_{period}_{str(std).replace(".", "_")}_lower'] = lower

        # ── Momentum Indicators ──
        for period in [7, 14, 21]:
            indicators[f'rsi_{period}'] = talib.RSI(close, timeperiod=period)
            indicators[f'adx_{period}'] = talib.ADX(high, low, close, timeperiod=period)
            indicators[f'adxr_{period}'] = talib.ADXR(high, low, close, timeperiod=period)

        indicators['macd'], indicators['macd_signal'], indicators['macd_hist'] = \
            talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

        for period in [7, 14, 21]:
            indicators[f'apo_{period}'] = talib.APO(close, fastperiod=period, slowperiod=period*2, matype=0)
            indicators[f'aroonosc_{period}'] = talib.AROONOSC(high, low, timeperiod=period)
            indicators[f'cci_{period}'] = talib.CCI(high, low, close, timeperiod=period)
            indicators[f'cmo_{period}'] = talib.CMO(close, timeperiod=period)
            indicators[f'mfi_{period}'] = talib.MFI(high, low, close, volume, timeperiod=period)
            indicators[f'ppo_{period}'] = talib.PPO(close, fastperiod=period, slowperiod=period*2, matype=0)
            indicators[f'roc_{period}'] = talib.ROC(close, timeperiod=period)
            indicators[f'rocp_{period}'] = talib.ROCP(close, timeperiod=period)
            indicators[f'rocr_{period}'] = talib.ROCR(close, timeperiod=period)
            indicators[f'rocr100_{period}'] = talib.ROCR100(close, timeperiod=period)
            indicators[f'trix_{period}'] = talib.TRIX(close, timeperiod=period)
            indicators[f'willr_{period}'] = talib.WILLR(high, low, close, timeperiod=period)

        slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
        indicators['stoch_k_14'] = slowk
        indicators['stoch_d_14'] = slowd
        slowk5, slowd5 = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3)
        indicators['stoch_k_5'] = slowk5
        indicators['stoch_d_5'] = slowd5

        # ── Volume ──
        indicators['ad'] = talib.AD(high, low, close, volume)
        indicators['adosc'] = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)
        indicators['obv'] = talib.OBV(close, volume)

        # ── Volatility ──
        for period in [7, 14, 20]:
            indicators[f'atr_{period}'] = talib.ATR(high, low, close, timeperiod=period)
            indicators[f'natr_{period}'] = talib.NATR(high, low, close, timeperiod=period)
        indicators['trange'] = talib.TRANGE(high, low, close)

        # ── Price Transform ──
        indicators['avgprice'] = talib.AVGPRICE(open_price, high, low, close)
        indicators['medprice'] = talib.MEDPRICE(high, low)
        indicators['typprice'] = talib.TYPPRICE(high, low, close)
        indicators['wclprice'] = talib.WCLPRICE(high, low, close)

        # ── Cycle ──
        indicators['ht_dcperiod'] = talib.HT_DCPERIOD(close)
        indicators['ht_dcphase'] = talib.HT_DCPHASE(close)
        inphase, quadrature = talib.HT_PHASOR(close)
        indicators['ht_phasor_inphase'] = inphase
        indicators['ht_phasor_quadrature'] = quadrature
        sine, leadsine = talib.HT_SINE(close)
        indicators['ht_sine'] = sine
        indicators['ht_leadsine'] = leadsine
        indicators['ht_trendmode'] = talib.HT_TRENDMODE(close)

        # ── Candlestick Patterns (63 total from TA-Lib) ──
        cdl_funcs = [
            ('2crows', talib.CDL2CROWS),
            ('3blackcrows', talib.CDL3BLACKCROWS),
            ('3inside', talib.CDL3INSIDE),
            ('3linestrike', talib.CDL3LINESTRIKE),
            ('3outside', talib.CDL3OUTSIDE),
            ('3starsinsouth', talib.CDL3STARSINSOUTH),
            ('3whitesoldiers', talib.CDL3WHITESOLDIERS),
            ('advancedblock', talib.CDLADVANCEBLOCK),
            ('belthold', talib.CDLBELTHOLD),
            ('breakaway', talib.CDLBREAKAWAY),
            ('closingmarubozu', talib.CDLCLOSINGMARUBOZU),
            ('concealbabyswall', talib.CDLCONCEALBABYSWALL),
            ('counterattack', talib.CDLCOUNTERATTACK),
            ('darkcloudcover', talib.CDLDARKCLOUDCOVER),
            ('doji', talib.CDLDOJI),
            ('dojistar', talib.CDLDOJISTAR),
            ('dragonflydoji', talib.CDLDRAGONFLYDOJI),
            ('engulfing', talib.CDLENGULFING),
            ('eveningdojistar', talib.CDLEVENINGDOJISTAR),
            ('eveningstar', talib.CDLEVENINGSTAR),
            ('gapsidesidewhite', talib.CDLGAPSIDESIDEWHITE),
            ('gravestonedoji', talib.CDLGRAVESTONEDOJI),
            ('hammer', talib.CDLHAMMER),
            ('hangingman', talib.CDLHANGINGMAN),
            ('harami', talib.CDLHARAMI),
            ('haramicross', talib.CDLHARAMICROSS),
            ('highwave', talib.CDLHIGHWAVE),
            ('hikkake', talib.CDLHIKKAKE),
            ('hikkakemod', talib.CDLHIKKAKEMOD),
            ('homingpigeon', talib.CDLHOMINGPIGEON),
            ('identical3crows', talib.CDLIDENTICAL3CROWS),
            ('inneck', talib.CDLINNECK),
            ('invertedhammer', talib.CDLINVERTEDHAMMER),
            ('kicking', talib.CDLKICKING),
            ('kickingbylength', talib.CDLKICKINGBYLENGTH),
            ('ladderbottom', talib.CDLLADDERBOTTOM),
            ('longleggeddoji', talib.CDLLONGLEGGEDDOJI),
            ('longline', talib.CDLLONGLINE),
            ('marubozu', talib.CDLMARUBOZU),
            ('matchinglow', talib.CDLMATCHINGLOW),
            ('matin', talib.CDLMATHOLD),
            ('morningdojistar', talib.CDLMORNINGDOJISTAR),
            ('morningstar', talib.CDLMORNINGSTAR),
            ('onneck', talib.CDLONNECK),
            ('piercing', talib.CDLPIERCING),
            ('rickshawman', talib.CDLRICKSHAWMAN),
            ('risefall3methods', talib.CDLRISEFALL3METHODS),
            ('separatinglines', talib.CDLSEPARATINGLINES),
            ('shootingstar', talib.CDLSHOOTINGSTAR),
            ('shortline', talib.CDLSHORTLINE),
            ('spinningtop', talib.CDLSPINNINGTOP),
            ('stalledpattern', talib.CDLSTALLEDPATTERN),
            ('sticksandwich', talib.CDLSTICKSANDWICH),
            ('takuri', talib.CDLTAKURI),
            ('tasukigap', talib.CDLTASUKIGAP),
            ('thrusting', talib.CDLTHRUSTING),
            ('tristar', talib.CDLTRISTAR),
            ('unique3river', talib.CDLUNIQUE3RIVER),
            ('upsidegap2crows', talib.CDLUPSIDEGAP2CROWS),
            ('xsidegap3methods', talib.CDLXSIDEGAP3METHODS),
        ]
        for name, func in cdl_funcs:
            try:
                indicators[f'cdl_{name}'] = func(open_price, high, low, close)
            except Exception:
                indicators[f'cdl_{name}'] = np.zeros(len(close))

        return indicators

    def _calculate_indicators_numpy(self, ohlcv):
        """Fallback: calculate basic indicators without TA-Lib."""
        close = ohlcv['close']
        high = ohlcv['high']
        low = ohlcv['low']
        volume = ohlcv['volume']
        indicators = {}

        for period in [5, 10, 20, 50, 100, 200]:
            if len(close) >= period:
                sma = np.convolve(close, np.ones(period)/period, mode='valid')
                padded = np.full(len(close), np.nan)
                padded[period-1:] = sma
                indicators[f'sma_{period}'] = padded

        for period in [7, 14, 21]:
            if len(close) > period:
                deltas = np.diff(close)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
                avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
                rs = avg_gain / np.where(avg_loss == 0, 1, avg_loss)
                rsi = 100 - (100 / (1 + rs))
                padded = np.full(len(close), np.nan)
                padded[period+1:] = rsi
                indicators[f'rsi_{period}'] = padded

        for period in [7, 14, 20]:
            if len(close) > 1:
                tr = np.maximum(high[1:] - low[1:],
                               np.maximum(np.abs(high[1:] - close[:-1]),
                                         np.abs(low[1:] - close[:-1])))
                atr = np.convolve(tr, np.ones(period)/period, mode='valid')
                padded = np.full(len(close), np.nan)
                padded[period:] = atr
                indicators[f'atr_{period}'] = padded

        obv = np.zeros(len(close))
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                obv[i] = obv[i-1] + volume[i]
            elif close[i] < close[i-1]:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]
        indicators['obv'] = obv

        return indicators

    def save_indicators(self, symbol, dates, indicators):
        """
        Save calculated indicators to indicators_json table.
        Wide-column format: one column per indicator (up to 140+ columns).

        Uses INSERT + DELETE pattern for cross-DB compatibility
        (works on both MySQL and SQLite).
        """
        if not dates or not indicators:
            return 0

        available_cols = [c for c in self.INDICATOR_COLUMNS if c in indicators]
        if not available_cols:
            return 0

        base_cols = ['symbol', 'price_date']
        all_cols = base_cols + available_cols
        col_str = ', '.join(all_cols)
        val_placeholders = ', '.join(['%s'] * len(all_cols))

        n_saved = 0
        batch = []

        for i, date_str in enumerate(dates):
            row_data = {'symbol': symbol, 'price_date': date_str}
            has_data = False

            for col in available_cols:
                arr = indicators[col]
                if i < len(arr):
                    val = arr[i]
                    if not np.isnan(val) and not np.isinf(val):
                        row_data[col] = round(float(val), 6)
                        has_data = True

            if has_data:
                batch.append(tuple(row_data.get(c) for c in all_cols))

        if not batch:
            return 0

        with self.db.connect() as conn:
            # Delete existing rows for these dates, then insert fresh
            date_list = [d for d in dates]
            placeholders = ','.join(['%s'] * len(date_list))
            conn.execute(
                f"DELETE FROM indicators_json WHERE symbol = %s AND price_date IN ({placeholders})",
                [symbol] + date_list
            )
            n_saved = conn.executemany(
                f"INSERT INTO indicators_json ({col_str}) VALUES ({val_placeholders})",
                batch
            )

        return n_saved

    def calculate_for_symbol(self, symbol, lookback_days=365):
        """Calculate indicators for a single symbol."""
        end_date = datetime.date.today().strftime('%Y-%m-%d')
        ohlcv = self.load_ohlcv(symbol, limit_days=lookback_days + 400)

        if ohlcv is None or len(ohlcv['close']) < 250:
            log.debug(f"Skipping {symbol}: insufficient data ({len(ohlcv['close']) if ohlcv else 0} rows)")
            return 0

        indicators = self.calculate_all_indicators(ohlcv)
        n = self.save_indicators(symbol, ohlcv['dates'], indicators)
        return n

    def calculate_all_missing(self, verbose=True):
        """Calculate indicators for all active symbols that need them."""
        symbols = self.get_symbols_needing_indicators()
        total = 0

        if verbose:
            print(f"Indicator calculation: {len(symbols)} symbols need processing")

        for i, symbol in enumerate(symbols):
            n = self.calculate_for_symbol(symbol)
            total += n

            if verbose and (i % 10 == 0 or n > 0):
                print(f"  [{i+1}/{len(symbols)}] {symbol}: {n} rows")

            if i > 0 and i % 50 == 0:
                time.sleep(0.5)

        if verbose:
            print(f"Total: {total} indicator rows saved")
        return total


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Daily data pipeline (Stage 1 & 2)')
    parser.add_argument('--mode', required=True,
                       choices=['daily', 'backfill', 'indicators', 'status'],
                       help='Operation mode')
    parser.add_argument('--symbol', help='Symbol for backfill mode')
    parser.add_argument('--start', help='Start date for backfill')
    parser.add_argument('--end', help='End date for backfill')
    parser.add_argument('--verbose', action='store_true', default=True)
    args = parser.parse_args()

    db = _build_db()

    if args.mode == 'daily':
        downloader = DailyPriceDownloader(db)
        total_new, errors = downloader.run_daily_update(verbose=args.verbose)

        calc = IndicatorCalculator(db)
        calc.calculate_all_missing(verbose=args.verbose)

    elif args.mode == 'backfill':
        if not args.symbol or not args.start or not args.end:
            print("Required: --symbol, --start, --end")
            sys.exit(1)

        downloader = DailyPriceDownloader(db)
        n_prices = downloader.backfill_symbol(args.symbol, args.start, args.end, args.verbose)

        if n_prices > 0:
            calc = IndicatorCalculator(db)
            n_ind = calc.calculate_for_symbol(args.symbol)
            print(f"Indicators: {n_ind} rows")

    elif args.mode == 'indicators':
        calc = IndicatorCalculator(db)
        calc.calculate_all_missing(verbose=args.verbose)

    elif args.mode == 'status':
        downloader = DailyPriceDownloader(db)
        status = downloader.get_status()

        print(f"\nData Status Report ({datetime.date.today()})")
        print(f"{'='*50}")
        print(f"Total active symbols: {status['total_symbols']}")
        print(f"With data:            {status['with_data']}")
        print(f"Without data:         {status['without_data']}")
        print(f"Up to date:           {status['up_to_date']}")
        print(f"Needs update:         {status['needs_update']}")

        if status['needs_update'] > 0:
            print(f"\nStale symbols:")
            for d in status['details']:
                if d['status'] == 'stale':
                    print(f"  {d['symbol']}: last data {d['latest']}")
