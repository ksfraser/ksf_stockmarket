#!/usr/bin/env python3
"""
retry_failed_symbols.py — Re-fetch symbols that failed during backfill.
Uses individual yfinance calls with proper NaN handling.
Processes symbols that have zero price data in symbol_master.
"""
import sys
import os
import time
import datetime
import subprocess

_PYTHON_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_PYTHON_DIR, 'python'))

import yfinance as yf
import numpy as np
from config_loader import Config
from db import Database, MySQLAdapter

LOG_FILE = os.path.join(_PYTHON_DIR, 'data_fetch_progress.log')
SLEEP_BETWEEN = 2  # seconds between requests
MAX_RETRIES = 3
START_DATE = "2013-01-01"
END_DATE = "2026-05-31"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_db():
    cfg = Config(os.path.join(_PYTHON_DIR, 'config.yaml'))
    return Database(MySQLAdapter(
        host='ksfraser.ca', user='ksfraser_stockmarket',
        password=cfg.db_password, database='ksfraser_stock_market'
    ))

def get_failed_symbols(db):
    """Get active symbols with zero price data."""
    with db.connect() as conn:
        rows = conn.fetchall("""
            SELECT sm.symbol FROM symbol_master sm
            LEFT JOIN stockprices sp ON sm.symbol = sp.symbol
            WHERE sm.is_active = 1 AND sp.symbol IS NULL
            ORDER BY sm.symbol
        """)
    return [r['symbol'] for r in rows]

def _safe(val, cast=float, default=0):
    try:
        if val is None:
            return default
        v = cast(val)
        if isinstance(v, float) and np.isnan(v):
            return default
        return v
    except (TypeError, ValueError, OverflowError):
        return default

def upsert_prices(db, symbol, df):
    if df is None or df.empty:
        return 0
    rows = []
    for date_idx, row in df.iterrows():
        date_str = date_idx.strftime('%Y-%m-%d') if hasattr(date_idx, 'strftime') else str(date_idx)[:10]
        rows.append((
            symbol, date_str,
            _safe(row.get('Open'), float),
            _safe(row.get('High'), float),
            _safe(row.get('Low'), float),
            _safe(row.get('Close'), float),
            _safe(row.get('Volume'), int),
        ))
    if not rows:
        return 0
    with db.connect() as conn:
        dates = [r[1] for r in rows]
        placeholders = ','.join(['%s'] * len(dates))
        existing = conn.fetchall(
            f"SELECT price_date FROM stockprices WHERE symbol = %s AND price_date IN ({placeholders})",
            [symbol] + dates
        )
        existing_dates = set(str(r['price_date']) for r in existing)
    new_rows = [r for r in rows if r[1] not in existing_dates]
    if not new_rows:
        return 0
    sql = ("INSERT INTO stockprices (symbol, price_date, open, high, low, close, volume) "
           "VALUES (%s,%s,%s,%s,%s,%s,%s) "
           "ON DUPLICATE KEY UPDATE open=%s,high=%s,low=%s,close=%s,volume=%s")
    with db.connect() as conn:
        for r in new_rows:
            conn.execute(sql, (*r, *r[2:]))
    return len(new_rows)

def download_symbol(symbol, start, end):
    """Download OHLCV for a single symbol. Returns DataFrame or None."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start, end=end, auto_adjust=False)
        if hist.empty:
            return None
        # Drop rows where ALL values are NaN
        hist = hist.dropna(how='all')
        if hist.empty:
            return None
        return hist
    except Exception as e:
        log(f"  Download error for {symbol}: {e}")
        return None

def main():
    db = get_db()
    symbols = get_failed_symbols(db)
    total = len(symbols)
    log(f"Symbols to retry: {total}")
    if not total:
        log("No symbols to retry. Exiting.")
        return

    success = 0
    fail = 0
    total_rows = 0
    failed_symbols = []
    start_time = time.time()

    for i, sym in enumerate(symbols):
        log(f"[{i+1}/{total}] {sym}...")
        df = None
        for attempt in range(1, MAX_RETRIES + 1):
            df = download_symbol(sym, START_DATE, END_DATE)
            if df is not None and not df.empty:
                break
            if attempt < MAX_RETRIES:
                time.sleep(3 * attempt)

        if df is not None:
            try:
                n = upsert_prices(db, sym, df)
                total_rows += n
                success += 1
                log(f"  OK: +{n} rows")
            except Exception as e:
                fail += 1
                failed_symbols.append(sym)
                log(f"  FAIL (upsert): {e}")
        else:
            fail += 1
            failed_symbols.append(sym)
            log(f"  FAIL: no data")

        # Progress update every 25 symbols
        if (i + 1) % 25 == 0:
            elapsed = (time.time() - start_time) / 60
            log(f"--- Progress: {success} OK, {fail} FAIL, {elapsed:.1f} min ---")

        time.sleep(SLEEP_BETWEEN)

    elapsed = (time.time() - start_time) / 60
    log("=" * 60)
    log(f"RETRY COMPLETE: {success} OK, {fail} FAIL, {total_rows:,} rows, {elapsed:.1f} min")
    if failed_symbols:
        log(f"Failed: {', '.join(failed_symbols)}")
    log("=" * 60)

if __name__ == "__main__":
    main()
