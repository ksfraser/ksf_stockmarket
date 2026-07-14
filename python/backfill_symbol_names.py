#!/usr/bin/env python3
"""
Backfill symbol_master names for symbols that are missing them.
Uses yfinance.info to get longName/shortName.
"""
import sys
import os
import time

# Ensure project root is importable
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

def get_missing_symbols(conn):
    """Return symbols that are in stockprices but have NULL/empty name in symbol_master."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT sp.symbol
            FROM (SELECT DISTINCT symbol FROM stockprices) sp
            LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
            WHERE sm.symbol IS NULL OR sm.name IS NULL OR TRIM(sm.name) = ''
            ORDER BY sp.symbol
        """)
        return [r['symbol'] for r in cur.fetchall()]

def get_name_from_yfinance(symbol):
    """Try to get company name from yfinance."""
    candidates = []
    try:
        tk = yf.Ticker(resolve_for_yfinance(symbol))
        info = tk.info
        candidates.append(info.get('longName'))
        candidates.append(info.get('shortName'))
    except Exception:
        pass
    
    # Fallback: try .TO suffix for Canadian stocks
    if not any(candidates) and not symbol.endswith('.TO'):
        try:
            tk = yf.Ticker(resolve_for_yfinance(symbol + '.TO'))
            info = tk.info
            candidates.append(info.get('longName'))
            candidates.append(info.get('shortName'))
        except Exception:
            pass
    
    for name in candidates:
        if name and isinstance(name, str) and name.strip():
            return name.strip()
    return None

def upsert_symbol_master(conn, symbol, name):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO symbol_master (symbol, name, is_active, pipeline_state, last_updated)
            VALUES (%s, %s, 1, 'unknown', NOW())
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                last_updated = NOW()
        """, (symbol, name))
    conn.commit()

def main():
    conn = pymysql.connect(**DB_CFG)
    missing = get_missing_symbols(conn)
    print(f"Missing names: {len(missing)}")
    
    done = 0
    failed = 0
    for sym in missing:
        name = get_name_from_yfinance(sym)
        if name:
            upsert_symbol_master(conn, sym, name)
            print(f"  {sym} -> {name}")
            done += 1
        else:
            print(f"  {sym} -> NO NAME FOUND")
            failed += 1
        time.sleep(0.3)  # be nice to yfinance
    
    conn.close()
    print(f"Done. Updated: {done}, Failed: {failed}")

if __name__ == '__main__':
    main()
