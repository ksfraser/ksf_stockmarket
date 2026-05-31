#!/usr/bin/env python3
"""
fetch_prices.py — Download OHLCV price data from yfinance for all 404 symbols.

Respects 500MB disk budget by fetching incrementally and inserting into
partitioned MySQL stockprices table. Skips symbols already in DB.

Usage:
    python3 fetch_prices.py [--max 100] [--start-from SYMBOL]
"""
import pymysql, yfinance as yf, pandas as pd
import sys, os, time, argparse
from datetime import date

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def get_existing_symbols(c):
    c.execute("SELECT DISTINCT symbol FROM stockprices")
    return set(r['symbol'] for r in c.fetchall())


def get_pending_symbols(c, existing):
    c.execute("SELECT symbol FROM symbol_master ORDER BY symbol")
    all_syms = set(r['symbol'] for r in c.fetchall())
    return sorted(all_syms - existing)


def fetch_symbol(sym, start='2014-01-01', end='2025-05-30'):
    """Fetch 10 years of daily OHLCV from yfinance. Returns DataFrame or None."""
    try:
        hist = yf.Ticker(sym).history(start=start, end=end, auto_adjust=False)
        if hist.empty or len(hist) < 50:
            return None
        return hist
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def insert_prices(c, sym, hist):
    """Insert OHLCV rows into stockprices. Skip existing."""
    rows = []
    for idx, row in hist.iterrows():
        d = idx.strftime('%Y-%m-%d')
        rows.append((
            sym, d,
            float(row['Open']) if pd.notna(row['Open']) else None,
            float(row['High']) if pd.notna(row['High']) else None,
            float(row['Low']) if pd.notna(row['Low']) else None,
            float(row['Close']),
            int(row['Volume']) if pd.notna(row['Volume']) else None,
            float(row['Close']) if 'Adj Close' in row and pd.isna(row.get('Adj Close')) else float(row['Adj Close']) if 'Adj Close' in row and pd.notna(row.get('Adj Close')) else float(row['Close']),
            float(row.get('Dividends', 0)) if pd.notna(row.get('Dividends', 0)) else 0,
            float(row.get('Stock Splits', 1)) if pd.notna(row.get('Stock Splits', 1)) else 1,
        ))
    if not rows:
        return 0
    c.executemany(
        "INSERT IGNORE INTO stockprices (symbol,price_date,open,high,low,close,volume,adj_close,dividend,split_ratio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=None, help='Max symbols to fetch')
    parser.add_argument('--start-from', default=None, help='Start from this symbol')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()

    existing = get_existing_symbols(c)
    print(f"Already have price data for: {len(existing)} symbols")

    pending = get_pending_symbols(c, existing)
    if args.start_from:
        pending = [s for s in pending if s >= args.start_from]
    if args.max:
        pending = pending[:args.max]

    print(f"Fetching: {len(pending)} symbols")

    ok, fail, total_rows = 0, 0, 0
    for i, sym in enumerate(pending):
        hist = fetch_symbol(sym)
        if hist is None:
            fail += 1
            if args.verbose:
                print(f"  [{i+1}/{len(pending)}] {sym}: NO DATA")
            time.sleep(1)
            continue

        n = insert_prices(c, sym, hist)
        conn.commit()
        ok += 1
        total_rows += n
        elapsed = (i + 1) * 1.5  # rough time estimate
        start_d = str(hist.index[0])[:10]
        end_d = str(hist.index[-1])[:10]
        print(f"  [{i+1}/{len(pending)}] {sym}: {n} rows ({start_d} -> {end_d})")

        # Rate limit: max ~100/hour
        time.sleep(1.5)

        # Batch update symbol_master
        c.execute("UPDATE symbol_master SET data_start=%s, last_updated=CURRENT_TIMESTAMP WHERE symbol=%s",
                  (hist.index[0].date().isoformat(), sym))
        conn.commit()

    print(f"\n✓ Fetched {ok} symbols, {fail} failed, {total_rows:,} total rows")

    c.execute("SELECT COUNT(DISTINCT symbol) as cnt FROM stockprices")
    print(f"  Total symbols with prices: {c.fetchone()['cnt']}")

    conn.close()


if __name__ == '__main__':
    main()
