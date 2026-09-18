#!/usr/bin/env python3
"""
Import loaded2stockprices CSVs into stockprices via the central DAO.
"""
import os
import sys
import re
import glob
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Ensure python/src/ is importable so we can use the stockprice DAO
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / 'python' / 'src'))

from db.stockprice_dao import PriceRow, create_central_stockprice_dao  # noqa: E402

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
    # Create the central stockprice DAO (central DB write + optional exchange dual-write).
    dao = create_central_stockprice_dao()

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
        rows_batch: list[PriceRow] = []
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                row = parse_row(line)
                if row:
                    rows_batch.append(PriceRow(
                        symbol=symbol,
                        price_date=date.fromisoformat(row['price_date']),
                        open=Decimal(str(row['open'])) if row['open'] is not None else None,
                        high=Decimal(str(row['high'])) if row['high'] is not None else None,
                        low=Decimal(str(row['low'])) if row['low'] is not None else None,
                        close=Decimal(str(row['close'])),
                        volume=row['volume'],
                        adj_close=Decimal(str(row['adj_close'])) if row['adj_close'] is not None else None,
                        currency=currency,
                        dividend=Decimal('0'),
                        split_ratio=Decimal('1'),
                    ))
                    total_rows += 1

        if not rows_batch:
            continue

        # Insert batch via the DAO (INSERT ... ON DUPLICATE KEY UPDATE, idempotent).
        try:
            affected = dao.write_prices(rows_batch)
            imported += affected
            skipped += (len(rows_batch) - affected)
        except Exception as e:
            errors += 1
            print(f"  Error inserting {fpath}: {e}")

        if total_rows % 100000 == 0:
            print(f"  Progress: {total_rows} rows processed, {imported} imported, {skipped} skipped")

    print(f"Done. Total: {total_rows}, Imported: {imported}, Skipped: {skipped}, Errors: {errors}")

if __name__ == '__main__':
    main()
