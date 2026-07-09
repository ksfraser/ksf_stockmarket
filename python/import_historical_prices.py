#!/usr/bin/env python3
"""
Import loaded2stockprices CSVs into stockprices with IGNORE guards for deduplication.
"""
import os
import sys
import re
import glob
import pymysql
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_CFG = {
    'host': 'ksfraser.ca',
    'port': 3306,
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

CSV_DIR = '/home/ksf_stockmarket/ksf_stockmarket/currentdata/loaded2stockprices'

def parse_symbol_from_filename(fname):
    """Extract symbol from filenames like AAPL.2011119-20130109.csv or ADRE.2011119-20130109.csv"""
    base = os.path.basename(fname)
    # Remove the date suffix
    m = re.match(r'^([A-Za-z0-9_\-\.]+)\.\d+.*\.csv$', base)
    if m:
        return m.group(1)
    return None

def parse_row(line):
    """Parse a CSV line: Date,Open,High,Low,Close,Volume,Adj Close"""
    line = line.strip()
    if not line:
        return None
    parts = line.split(',')
    if len(parts) < 7:
        return None
    date_str = parts[0].strip()
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None
    try:
        o = float(parts[1])
        h = float(parts[2])
        l = float(parts[3])
        c = float(parts[4])
        v = int(float(parts[5]))
        adj = float(parts[6])
    except (ValueError, IndexError):
        return None
    return {
        'price_date': date_str,
        'open': o,
        'high': h,
        'low': l,
        'close': c,
        'volume': v,
        'adj_close': adj,
    }

def determine_currency(symbol):
    if symbol.endswith('.TO') or symbol.endswith('.UN.TO') or symbol.endswith('-UN.TO'):
        return 'CAD'
    if '.HK' in symbol or symbol.endswith('.HK'):
        return 'HKD'
    if '.L' in symbol:
        return 'GBP'
    if symbol.endswith('.OB') or symbol.endswith('.PK') or symbol.endswith('.BE'):
        return 'USD'
    # Default: US equities are USD, others depend
    # For this app, most active symbols are US/CA
    return 'USD'

def main():
    conn = pymysql.connect(**DB_CFG)
    csv_files = sorted(glob.glob(os.path.join(CSV_DIR, '*.csv')))
    print(f"Found {len(csv_files)} CSV files")

    total_rows = 0
    skipped = 0
    imported = 0
    errors = 0

    for fpath in csv_files:
        symbol = parse_symbol_from_filename(fpath)
        if not symbol:
            continue

        currency = determine_currency(symbol)
        rows_batch = []
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                row = parse_row(line)
                if row:
                    row['symbol'] = symbol
                    row['currency'] = currency
                    row['split_ratio'] = 1.0
                    row['dividend'] = 0.0
                    rows_batch.append(row)
                    total_rows += 1

        if not rows_batch:
            continue

        # Insert batch
        try:
            with conn.cursor() as cur:
                sql = """
                    INSERT IGNORE INTO stockprices
                        (symbol, price_date, open, high, low, close, volume, adj_close, currency, dividend, split_ratio)
                    VALUES
                        (%(symbol)s, %(price_date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, %(adj_close)s, %(currency)s, %(dividend)s, %(split_ratio)s)
                """
                cur.executemany(sql, rows_batch)
                affected = cur.rowcount
                imported += affected
                skipped += (len(rows_batch) - affected)
            conn.commit()
        except Exception as e:
            errors += 1
            print(f"  Error inserting {fpath}: {e}")
            conn.rollback()

        if total_rows % 100000 == 0:
            print(f"  Progress: {total_rows} rows processed, {imported} imported, {skipped} skipped")

    conn.close()
    print(f"Done. Total: {total_rows}, Imported: {imported}, Skipped: {skipped}, Errors: {errors}")

if __name__ == '__main__':
    main()
