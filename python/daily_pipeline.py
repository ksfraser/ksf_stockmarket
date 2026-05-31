#!/usr/bin/env python3
"""
daily_pipeline.py — Stage 1 & 2 of the investment agent pipeline.

STAGE 1: Daily Price Download
  - For every symbol in symbol_master, fetch today's OHLCV from yfinance
  - Includes dividend actions, stock splits
  - Store in stockprices table

STAGE 2: Indicator Calculation
  - For each day's data added, compute 120+ technical indicators
  - Store in indicators_json table as JSON blob

Usage:
    python3 daily_pipeline.py --mode daily     # Update today's prices
    python3 daily_pipeline.py --mode backfill SYMBOL START_DATE END_DATE
    python3 daily_pipeline.py --mode status     # Show what's up to date
"""

import sys, os, json, argparse, time
import numpy as np
import pymysql
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

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


# ── Stage 1: Daily Price Download ──────────────────────────────────────────

class DailyPriceDownloader:
    """
    Downloads daily OHLCV data for all symbols in symbol_master.
    Handles dividends, splits, and ensures no duplicate entries.
    """

    def __init__(self):
        self.conn = pymysql.connect(**MYSQL)
        self.cursor = self.conn.cursor()

    def close(self):
        self.conn.close()

    def get_active_symbols(self):
        """Get all symbols from symbol_master table."""
        self.cursor.execute("SELECT symbol, name, exchange FROM symbol_master ORDER BY symbol")
        return self.cursor.fetchall()

    def get_latest_date(self, symbol):
        """Get the most recent price date for a symbol."""
        self.cursor.execute(
            "SELECT MAX(price_date) as latest FROM stockprices WHERE symbol = %s",
            (symbol,))
        row = self.cursor.fetchone()
        return row['latest'] if row and row['latest'] else None

    def download_today(self, symbol):
        """
        Fetch latest data for a symbol from yfinance.
        Returns list of (date, open, high, low, close, volume) tuples.
        """
        if not YFINANCE_AVAILABLE:
            print(f"  yfinance not available — cannot download {symbol}")
            return []

        try:
            ticker = yf.Ticker(symbol)
            # Get last 5 days of data (in case market was closed)
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
            print(f"  Error downloading {symbol}: {e}")
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
        except:
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
        except:
            return []

    def upsert_prices(self, symbol, prices):
        """
        Insert or update price rows for a symbol.
        Uses INSERT ... ON DUPLICATE KEY UPDATE.
        Returns number of new rows added.
        """
        if not prices:
            return 0

        # Check which dates already exist
        dates = [p['date'] for p in prices]
        placeholders = ','.join(['%s'] * len(dates))
        self.cursor.execute(
            f"SELECT price_date FROM stockprices WHERE symbol = %s AND price_date IN ({placeholders})",
            [symbol] + dates)
        existing = set(str(r['price_date']) for r in self.cursor.fetchall())

        new_prices = [p for p in prices if p['date'] not in existing]

        if not new_prices:
            return 0

        sql = ("INSERT INTO stockprices (symbol, price_date, open, high, low, close, volume) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s) "
               "ON DUPLICATE KEY UPDATE open=%s, high=%s, low=%s, close=%s, volume=%s")

        for p in new_prices:
            self.cursor.execute(sql, (
                symbol, p['date'], p['open'], p['high'], p['low'], p['close'], p['volume'],
                p['open'], p['high'], p['low'], p['close'], p['volume']
            ))

        self.conn.commit()
        return len(new_prices)

    def run_daily_update(self, verbose=True):
        """
        Main daily update: fetch today's prices for all symbols.
        """
        symbols = self.get_active_symbols()
        total_new = 0
        errors = []

        if verbose:
            print(f"Daily price update: {len(symbols)} symbols")
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

        # Also update dividends and splits for all symbols (monthly is fine)
        return total_new, errors

    def backfill_symbol(self, symbol, start_date, end_date, verbose=True):
        """
        Backfill historical data for a symbol.
        Used when adding a new symbol to the universe.
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
        """
        symbols = self.get_active_symbols()
        today = datetime.date.today().strftime('%Y-%m-%d')
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        status = {
            'total_symbols': len(symbols),
            'with_data': 0,
            'without_data': 0,
            'up_to_date': 0,
            'needs_update': 0,
            'details': []
        }

        for sym_row in symbols:
            symbol = sym_row['symbol']
            latest = self.get_latest_date(symbol)

            if latest is None:
                status['without_data'] += 1
                status['details'].append({'symbol': symbol, 'status': 'no_data', 'latest': None})
            else:
                status['with_data'] += 1
                latest_str = str(latest)
                if latest_str >= yesterday:
                    status['up_to_date'] += 1
                    status['details'].append({'symbol': symbol, 'status': 'current', 'latest': latest_str})
                else:
                    status['needs_update'] += 1
                    status['details'].append({'symbol': symbol, 'status': 'stale', 'latest': latest_str})

        return status


# ── Stage 2: Indicator Calculation ──────────────────────────────────────────

class IndicatorCalculator:
    """
    Calculates technical indicators for symbols with new price data.
    Reads OHLCV from stockprices table, writes to indicators_json table.
    """

    def __init__(self):
        self.conn = pymysql.connect(**MYSQL)
        self.cursor = self.conn.cursor()

    def close(self):
        self.conn.close()

    def get_symbols_needing_indicators(self, lookback_days=30):
        """
        Find symbols that have recent price data but missing indicator data.
        """
        self.cursor.execute("""
            SELECT DISTINCT sp.symbol
            FROM stockprices sp
            LEFT JOIN indicators_json ij ON sp.symbol = ij.symbol AND sp.price_date = ij.price_date
            WHERE sp.price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            AND ij.id IS NULL
            ORDER BY sp.symbol
        """, (lookback_days,))
        return [r['symbol'] for r in self.cursor.fetchall()]

    def load_ohlcv(self, symbol, start_date, end_date):
        """Load OHLCV data for indicator calculation."""
        self.cursor.execute("""
            SELECT price_date, open, high, low, close, volume
            FROM stockprices
            WHERE symbol = %s AND price_date BETWEEN %s AND %s
            ORDER BY price_date
        """, (symbol, start_date, end_date))

        rows = self.cursor.fetchall()
        if not rows:
            return None

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
        Calculate 120+ technical indicators using TA-Lib.
        Returns dict of {indicator_name: [values...]}
        """
        if not TALIB_AVAILABLE:
            return self.calculate_indicators_numpy(ohlcv)

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
                indicators[f'bb_{period}_{std}_upper'] = upper
                indicators[f'bb_{period}_{std}_mid'] = mid
                indicators[f'bb_{period}_{std}_lower'] = lower

        # ── Momentum Indicators ──
        for period in [7, 14, 21]:
            indicators[f'rsi_{period}'] = talib.RSI(close, timeperiod=period)
            indicators[f'adx_{period}'] = talib.ADX(high, low, close, timeperiod=period)
            indicators[f'adxr_{period}'] = talib.ADXR(high, low, close, timeperiod=period)

        indicators['macd'], indicators['macd_signal'], indicators['macd_hist'] = \
            talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

        indicators['macd_12_26_9'] = indicators['macd']
        indicators['macd_signal_12_26_9'] = indicators['macd_signal']
        indicators['macd_hist_12_26_9'] = indicators['macd_hist']

        for fast, slow, sig in [(5, 35, 5), (10, 50, 10)]:
            m, ms, mh = talib.MACD(close, fastperiod=fast, slowperiod=slow, signalperiod=sig)
            indicators[f'macd_{fast}_{slow}_{sig}'] = m
            indicators[f'macd_signal_{fast}_{slow}_{sig}'] = ms
            indicators[f'macd_hist_{fast}_{slow}_{sig}'] = mh

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

        # Stochastic
        slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
        indicators['stoch_k_14'] = slowk
        indicators['stoch_d_14'] = slowd

        slowk5, slowd5 = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3)
        indicators['stoch_k_5'] = slowk5
        indicators['stoch_d_5'] = slowd5

        # ── Volume Indicators ──
        indicators['ad'] = talib.AD(high, low, close, volume)
        indicators['adosc'] = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)
        indicators['obv'] = talib.OBV(close, volume)

        # ── Volatility Indicators ──
        for period in [7, 14, 20]:
            indicators[f'atr_{period}'] = talib.ATR(high, low, close, timeperiod=period)
            indicators[f'natr_{period}'] = talib.NATR(high, low, close, timeperiod=period)

        indicators['trange'] = talib.TRANGE(high, low, close)

        # ── Price Transform ──
        indicators['avgprice'] = talib.AVGPRICE(open_price, high, low, close)
        indicators['medprice'] = talib.MEDPRICE(high, low)
        indicators['typprice'] = talib.TYPPRICE(high, low, close)
        indicators['wclprice'] = talib.WCLPRICE(high, low, close)

        # ── Cycle Indicators ──
        indicators['ht_dcperiod'] = talib.HT_DCPERIOD(close)
        indicators['ht_dcphase'] = talib.HT_DCPHASE(close)
        inphase, quadrature = talib.HT_PHASOR(close)
        indicators['ht_phasor_inphase'] = inphase
        indicators['ht_phasor_quadrature'] = quadrature
        sine, leadsine = talib.HT_SINE(close)
        indicators['ht_sine'] = sine
        indicators['ht_leadsine'] = leadsine
        indicators['ht_trendmode'] = talib.HT_TRENDMODE(close)

        return indicators

    def calculate_indicators_numpy(self, ohlcv):
        """
        Fallback: calculate basic indicators without TA-Lib.
        Used when TA-Lib is not installed.
        """
        close = ohlcv['close']
        high = ohlcv['high']
        low = ohlcv['low']
        volume = ohlcv['volume']

        indicators = {}

        # Simple Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            if len(close) >= period:
                sma = np.convolve(close, np.ones(period)/period, mode='valid')
                padded = np.full(len(close), np.nan)
                padded[period-1:] = sma
                indicators[f'sma_{period}'] = padded

        # RSI
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

        # ATR
        for period in [7, 14, 20]:
            if len(close) > 1:
                tr = np.maximum(high[1:] - low[1:],
                               np.maximum(np.abs(high[1:] - close[:-1]),
                                         np.abs(low[1:] - close[:-1])))
                atr = np.convolve(tr, np.ones(period)/period, mode='valid')
                padded = np.full(len(close), np.nan)
                padded[period:] = atr
                indicators[f'atr_{period}'] = padded

        # NATR
        for period in [7, 14, 20]:
            if f'atr_{period}' in indicators:
                atr = indicators[f'atr_{period}']
                natr = (atr / close) * 100
                indicators[f'natr_{period}'] = natr

        # OBV
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
        Each row = one date × one symbol, with JSON blob of all indicators.
        """
        if not dates or not indicators:
            return 0

        sql = ("INSERT INTO indicators_json (symbol, price_date, data) "
               "VALUES (%s, %s, %s) "
               "ON DUPLICATE KEY UPDATE data=%s")

        n_saved = 0
        for i, date_str in enumerate(dates):
            row_data = {}
            for ind_name, ind_values in indicators.items():
                if i < len(ind_values):
                    val = ind_values[i]
                    if not np.isnan(val) and not np.isinf(val):
                        row_data[ind_name] = round(float(val), 6)

            if row_data:
                json_str = json.dumps(row_data)
                self.cursor.execute(sql, (symbol, date_str, json_str, json_str))
                n_saved += 1

        self.conn.commit()
        return n_saved

    def calculate_for_symbol(self, symbol, lookback_days=365):
        """Calculate indicators for all dates for a symbol that need them."""
        end_date = datetime.date.today().strftime('%Y-%m-%d')
        start_date = (datetime.date.today() - datetime.timedelta(days=lookback_days)).strftime('%Y-%m-%d')

        # Need enough history — load extra for indicator warmup
        extended_start = (datetime.date.today() - datetime.timedelta(days=lookback_days + 400)).strftime('%Y-%m-%d')
        ohlcv = self.load_ohlcv(symbol, extended_start, end_date)

        if ohlcv is None or len(ohlcv['close']) < 250:
            return 0

        indicators = self.calculate_all_indicators(ohlcv)
        n = self.save_indicators(symbol, ohlcv['dates'], indicators)
        return n

    def calculate_all_missing(self, verbose=True):
        """Calculate indicators for all symbols that have prices but no indicators."""
        symbols = self.get_symbols_needing_indicators()
        total = 0

        if verbose:
            print(f"Indicator calculation: {len(symbols)} symbols need processing")

        for i, symbol in enumerate(symbols):
            n = self.calculate_for_symbol(symbol)
            total += n

            if verbose and (i % 10 == 0 or n > 0):
                print(f"  [{i+1}/{len(symbols)}] {symbol}: {n} date-rows of indicators")

            # Rate limiting
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

    if args.mode == 'daily':
        downloader = DailyPriceDownloader()
        total_new, errors = downloader.run_daily_update(verbose=args.verbose)

        # After downloading prices, calculate indicators for new data
        calc = IndicatorCalculator()
        calc.calculate_all_missing(verbose=args.verbose)
        calc.close()

        downloader.close()

    elif args.mode == 'backfill':
        if not args.symbol or not args.start or not args.end:
            print("Required: --symbol, --start, --end")
            sys.exit(1)

        downloader = DailyPriceDownloader()
        n_prices = downloader.backfill_symbol(args.symbol, args.start, args.end, args.verbose)
        downloader.close()

        if n_prices > 0:
            calc = IndicatorCalculator()
            n_ind = calc.calculate_for_symbol(args.symbol)
            print(f"Indicators: {n_ind} rows")
            calc.close()

    elif args.mode == 'indicators':
        calc = IndicatorCalculator()
        calc.calculate_all_missing(verbose=args.verbose)
        calc.close()

    elif args.mode == 'status':
        downloader = DailyPriceDownloader()
        status = downloader.get_status()

        print(f"\nData Status Report ({datetime.date.today()})")
        print(f"{'='*50}")
        print(f"Total symbols:      {status['total_symbols']}")
        print(f"With data:          {status['with_data']}")
        print(f"Without data:       {status['without_data']}")
        print(f"Up to date:         {status['up_to_date']}")
        print(f"Needs update:       {status['needs_update']}")

        if status['needs_update'] > 0:
            print(f"\nStale symbols:")
            for d in status['details']:
                if d['status'] == 'stale':
                    print(f"  {d['symbol']}: last data {d['latest']}")

        downloader.close()
