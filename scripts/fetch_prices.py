#!/usr/bin/env python3
"""
fetch_prices.py — Pull historical prices from yfinance into SQLite
===================================================================
Fetches OHLCV data for all portfolio symbols back to 2013.
Writes directly to the dev SQLite DB so analysis/backtesting can run
without MariaDB.

Usage:
  python3 fetch_prices.py                    # Fetch all 20 symbols
  python3 fetch_prices.py --symbols RY.TO,TD.TO  # Specific symbols
  python3 fetch_prices.py --start 2010-01-01     # Custom start date
"""

import argparse
import sqlite3
import sys
import time
import os
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'analysis_results.db')

# Portfolio symbols (from migrate)
PORTFOLIO_SYMBOLS = [
    'BPF.UN', 'CDZ', 'CEF', 'CM', 'CNR', 'FEZ', 'IEV', 'KEG.UN',
    'MTY', 'MX', 'PDC', 'PZA', 'RGLD', 'RUS', 'RY', 'SPEU',
    'SRV.UN', 'TFII', 'UL', 'WJX',
]


def ensure_tables(db):
    """Create price/indicator tables if they don't exist."""
    db.executescript("""
    CREATE TABLE IF NOT EXISTS stockprices (
        symbol TEXT NOT NULL,
        price_date TEXT NOT NULL,
        day_open REAL,
        day_high REAL,
        day_low REAL,
        day_close REAL,
        volume REAL,
        PRIMARY KEY (symbol, price_date)
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_sp_symbol_date
        ON stockprices(symbol, price_date);
    CREATE INDEX IF NOT EXISTS idx_sp_date
        ON stockprices(price_date);

    CREATE TABLE IF NOT EXISTS daily_indicators (
        symbol TEXT NOT NULL,
        price_date TEXT NOT NULL,
        daily_return REAL,
        gap_pct REAL,
        sma_20 REAL, sma_50 REAL, sma_200 REAL,
        volume_sma_20 INTEGER,
        PRIMARY KEY (symbol, price_date)
    );

    CREATE TABLE IF NOT EXISTS data_import_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        import_type TEXT NOT NULL,
        symbol TEXT,
        records_before INTEGER,
        records_after INTEGER,
        records_added INTEGER,
        status TEXT DEFAULT 'started',
        error_message TEXT,
        duration_ms INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)


def normalize_symbol(sym):
    """Ensure TSX symbols have .TO suffix for yfinance."""
    sym = sym.strip().upper()
    # Already has a suffix
    if '.' in sym:
        return sym
    # Known non-TSX symbols that don't need .TO
    non_tsx = {'CEF', 'RGLD', 'BPF.UN', 'SRV.UN', 'KEG.UN', 'IEV', 'SPEU', 'UL', 'PZA', 'RUS', 'CDZ', 'FEZ', 'PZF'}
    if sym in non_tsx:
        return sym
    # Default: add .TO for Canadian symbols
    return f"{sym}.TO"


def fetch_symbol(symbol, start_date, end_date):
    """Fetch OHLCV data for a symbol from yfinance."""
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date, end=end_date, auto_adjust=False)
    if df.empty:
        return None
    # Reset index to make date a column
    df.reset_index(inplace=True)
    # Normalize column names
    df.columns = [c.lower().replace(' ', '_') for c in df.columns]
    return df


def write_prices(db, symbol, df):
    """Write OHLCV rows to stockprices table."""
    rows = []
    for _, row in df.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
        rows.append((
            symbol,
            date_str,
            float(row.get('open', 0) or 0),
            float(row.get('high', 0) or 0),
            float(row.get('low', 0) or 0),
            float(row.get('close', 0) or 0),
            int(row.get('volume', 0) or 0),
        ))

    db.executemany("""
        INSERT OR REPLACE INTO stockprices
            (symbol, price_date, day_open, day_high, day_low, day_close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, rows)
    db.commit()
    return len(rows)


def compute_indicators(db, symbol):
    """Compute Tier 1 indicators (return, gap, SMA) for a symbol."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT price_date, day_open, day_high, day_low, day_close, volume
        FROM stockprices WHERE symbol = ? ORDER BY price_date ASC
    """, (symbol,))
    rows = cursor.fetchall()
    if len(rows) < 5:
        return 0

    closes = [r[4] for r in rows]
    opens = [r[1] for r in rows]
    volumes = [r[5] for r in rows]
    dates = [r[0] for r in rows]

    indicators = []
    for i in range(len(rows)):
        d_return = (closes[i] - closes[i-1]) / closes[i-1] if i > 0 and closes[i-1] else 0
        gap = (opens[i] - closes[i-1]) / closes[i-1] if i > 0 and closes[i-1] else 0
        sma_20 = sum(closes[max(0,i-19):i+1]) / min(20, i+1) if i >= 19 else None
        sma_50 = sum(closes[max(0,i-49):i+1]) / min(50, i+1) if i >= 49 else None
        sma_200 = sum(closes[max(0,i-199):i+1]) / min(200, i+1) if i >= 199 else None
        vol_sma = int(sum(volumes[max(0,i-19):i+1]) / min(20, i+1)) if i >= 19 else None

        indicators.append((symbol, dates[i], d_return, gap, sma_20, sma_50, sma_200, vol_sma))

    db.executemany("""
        INSERT OR REPLACE INTO daily_indicators
            (symbol, price_date, daily_return, gap_pct, sma_20, sma_50, sma_200, volume_sma_20)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, indicators)
    db.commit()
    return len(indicators)


def main():
    parser = argparse.ArgumentParser(description='Fetch historical prices from yfinance')
    parser.add_argument('--symbols', type=str, default=','.join(PORTFOLIO_SYMBOLS))
    parser.add_argument('--start', type=str, default='2013-01-01')
    parser.add_argument('--end', type=str, default=date.today().isoformat())
    parser.add_argument('--db', type=str, default=DB_PATH)
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(',')]
    db = sqlite3.connect(args.db)
    ensure_tables(db)

    total_rows = 0
    total_indicators = 0
    errors = []

    for i, symbol in enumerate(symbols):
        yf_symbol = normalize_symbol(symbol)
        print(f"[{i+1}/{len(symbols)}] Fetching {symbol} (yfinance: {yf_symbol})...")
        start_time = time.time()
        try:
            df = fetch_symbol(yf_symbol, args.start, args.end)
            if df is None or df.empty:
                print(f"  ⚠ No data returned for {symbol}")
                errors.append(symbol)
                continue
            rows = write_prices(db, symbol, df)
            ind_rows = compute_indicators(db, symbol)
            elapsed = time.time() - start_time
            total_rows += rows
            total_indicators += ind_rows
            print(f"  ✅ {rows} prices, {ind_rows} indicators ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ❌ Error: {e} ({elapsed:.1f}s)")
            errors.append(symbol)

    # Log import
    db.execute("""
        INSERT INTO data_import_log (import_type, records_after, status, duration_ms)
        VALUES ('yfinance_full', ?, 'complete', ?)
    """, (total_rows, int(time.time() * 1000)))
    db.commit()

    # Summary
    c = db.cursor()
    c.execute("SELECT symbol, COUNT(*) FROM stockprices GROUP BY symbol ORDER BY symbol")
    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE")
    print(f"{'='*60}")
    print(f"  Symbols fetched: {len(symbols) - len(errors)}/{len(symbols)}")
    print(f"  Total price rows: {total_rows:,}")
    print(f"  Total indicator rows: {total_indicators:,}")
    print(f"  DB location: {os.path.abspath(args.db)}")
    if errors:
        print(f"  Failed symbols: {', '.join(errors)}")
    print(f"{'='*60}")

    # Per-symbol summary
    print(f"\nPer-symbol row counts:")
    for row in c.fetchall():
        print(f"  {row[0]:10s}: {row[1]:>6,} rows")
    c.close()
    db.close()


if __name__ == '__main__':
    main()
