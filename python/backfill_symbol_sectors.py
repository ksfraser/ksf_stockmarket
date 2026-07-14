#!/usr/bin/env python3
"""
Backfill sector for symbols where sector is still NULL.
Uses yfinance `sector`, then falls back to `category` for ETFs.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import yfinance as yf
from symbol_resolver import resolve_for_yfinance

DB_CFG = {
    'host': 'ksfraser.ca',
    'port': 3306,
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

def fetch_sector_via_yfinance(symbol):
    tickers = [symbol]
    if symbol.endswith('.TO') and not symbol.endswith('.TO.TO'):
        tickers.append(symbol + '.TO')
    if not symbol.endswith('.TO'):
        tickers.append(symbol + '.TO')

    for tk_sym in tickers:
        try:
            info = yf.Ticker(resolve_for_yfinance(tk_sym)).info or {}
            sector = info.get('sector')
            if sector and str(sector).strip():
                return str(sector).strip()
            category = info.get('category')
            if category and str(category).strip():
                return str(category).strip()
        except Exception:
            pass
    return None

def main():
    conn = pymysql.connect(**DB_CFG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT symbol, name
            FROM symbol_master
            WHERE sector IS NULL OR TRIM(sector)=''
            ORDER BY symbol
        """)
        missing = cur.fetchall()

    print(f"Symbols still missing sector: {len(missing)}")

    updated = 0
    failed = 0
    for row in missing:
        sym = row['symbol']
        sec = fetch_sector_via_yfinance(sym)
        if sec:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE symbol_master SET sector=%s, last_updated=NOW() WHERE symbol=%s
                """, (sec, sym))
            conn.commit()
            print(f"  {sym} -> {sec}")
            updated += 1
        else:
            print(f"  {sym} -> NO SECTOR")
            failed += 1
        time.sleep(0.3)

    conn.close()
    print(f"Done. Updated: {updated}, Failed: {failed}")

if __name__ == '__main__':
    main()
