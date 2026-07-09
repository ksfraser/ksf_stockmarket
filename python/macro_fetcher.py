#!/usr/bin/env python3
"""
Fetch macro indicator data:
- Shiller P/E (CAPE) from Yale
- Buffett Indicator from FRED/Toledo or compute from market cap + GDP
"""
import sys
import os
import json
import io
from datetime import datetime
import pymysql

DB_CFG = {
    'host': 'ksfraser.ca',
    'port': 3306,
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

def upsert_shiller(conn, rows):
    if not rows:
        return
    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO shiller_pe (month, cape_value, source, fetched_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE cape_value = VALUES(cape_value), fetched_at = VALUES(fetched_at)
        """, [(r[0], r[1], r[2], datetime.now()) for r in rows])
    conn.commit()

def upsert_buffett(conn, rows):
    if not rows:
        return
    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO buffett_indicator (year, market_cap_usd, gdp_usd, indicator_value, source, fetched_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                market_cap_usd = VALUES(market_cap_usd),
                gdp_usd = VALUES(gdp_usd),
                indicator_value = VALUES(indicator_value),
                fetched_at = VALUES(fetched_at)
        """, [(r[0], r[1], r[2], r[3], r[4], datetime.now()) for r in rows])
    conn.commit()

def fetch_shiller():
    """Try to fetch Shiller CAPE from Yale's XLS, fallback to web extract."""
    import urllib.request
    url = 'https://www.econ.yale.edu/~shiller/data/ie_data.xls'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        # We need xlrd to read .xls, but it's not guaranteed installed.
        # Fallback: try to parse as CSV if it's actually text, or use an alternate source.
        print(f"Shiller: fetched {len(data)} bytes from {url}")
        return []
    except Exception as e:
        print(f"Shiller fetch failed: {e}")
        return []

def fetch_buffett():
    """Buffett Indicator = Total Market Cap / GDP. We can compute from our data + FRED GDP."""
    # Placeholder until we wire FRED + market cap computation
    return []

def main():
    conn = pymysql.connect(**DB_CFG)
    shiller_rows = fetch_shiller()
    if shiller_rows:
        upsert_shiller(conn, shiller_rows)
        print(f"Shiller: upserted {len(shiller_rows)} rows")
    else:
        print("Shiller: no data fetched")
    buffett_rows = fetch_buffett()
    if buffett_rows:
        upsert_buffett(conn, buffett_rows)
        print(f"Buffett: upserted {len(buffett_rows)} rows")
    else:
        print("Buffett: no data fetched")
    conn.close()

if __name__ == '__main__':
    main()
