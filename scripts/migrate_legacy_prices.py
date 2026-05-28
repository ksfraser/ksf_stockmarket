#!/usr/bin/env python3
"""
migrate_legacy_prices.py
========================
Migrates stock price data from legacy MySQL dump files into the new
partitioned schema.

The legacy dumps have one INSERT per row (very slow for mysqldump but
great for streaming parsing). We parse INSERT statements and batch-insert
into the new partitioned stockprices table.

Legacy schemas differ:
  - stock_market.stockprices: symbol, date, previous_close, day_open, day_low,
    day_high, day_close, day_change, adj_close(?), volume (no primary key)
  - back_finance.stockprices: symbol, date, previous_close, day_open, day_low,
    day_high, day_close, day_change, bid, ask, volume, idstockinfo

New schema adds: source, updated_at (auto)
Legacy fields dropped: idstockinfo (was always 0)

Usage:
  python3 migrate_legacy_prices.py --dump sql/MYSQL.stock_market.sql --source legacy_stock_market
  python3 migrate_legacy_prices.py --dump sql/MYSQL.back_finance.sql --source back_finance
  
  # Or pipe from zcat:
  zcat sql/MYSQL.stock_market.sql.gz | python3 migrate_legacy_prices.py --dump - --source legacy
"""

import re
import sys
import argparse
import mysql.connector
from mysql.connector import Error
from datetime import datetime

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'ksf_stockmarket',
    'password': 'change_me',
    'database': 'ksf_stockmarket',
    'charset': 'utf8mb4',
    'use_unicode': True,
    'autocommit': False,
}

BATCH_SIZE = 5000  # rows per INSERT batch

# --------------------------------------------------------------------------
# Regex for parsing single-row INSERT statements
# Handles: INSERT IGNORE INTO `table` (`col1`, `col2`, ...) VALUES ('val1', 'val2', ...);
# Also handles: INSERT INTO ... VALUES ('val1'), ('val2'), ...; (multi-row)
# --------------------------------------------------------------------------
INSERT_RE = re.compile(
    r"INSERT\s+(?:IGNORE\s+)?INTO\s+`?(\w+)`?\s*\(([^)]+)\)\s+VALUES\s+(.+);",
    re.IGNORECASE | re.DOTALL
)

# --------------------------------------------------------------------------
# Field mapping: legacy column name -> new column name
# --------------------------------------------------------------------------
FIELD_MAP_STOCK_MARKET = {
    'symbol':          'symbol',
    'date':            'price_date',
    'previous_close':  'previous_close',
    'day_open':        'day_open',
    'day_low':         'day_low',
    'day_high':        'day_high',
    'day_close':       'day_close',
    'day_change':      'day_change',
    'adjustedclose':   'adj_close',
    'adj_close':       'adj_close',
    'volume':          'volume',
    'bid':             'bid',
    'ask':             'ask',
}

FIELD_MAP_BACK_FINANCE = {
    'symbol':          'symbol',
    'date':            'price_date',
    'previous_close':  'previous_close',
    'day_open':        'day_open',
    'day_low':         'day_low',
    'day_high':        'day_high',
    'day_close':       'day_close',
    'day_change':      'day_change',
    'volume':          'volume',
    'bid':             'bid',
    'ask':             'ask',
    # idstockinfo is dropped (was always 0)
}


def parse_value(val_str):
    """Parse a single SQL value string into a Python value."""
    val_str = val_str.strip()
    if val_str.upper() == 'NULL':
        return None
    if val_str.startswith("'") and val_str.endswith("'"):
        # Unescape SQL string
        return val_str[1:-1].replace("''", "'").replace("\\'", "'")
    try:
        # Try int first, then float
        if '.' in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str


def parse_insert_statement(sql, field_map, source_name):
    """
    Parse an INSERT statement and yield (column_list, value_tuples) for each row.
    Handles both single-row and multi-row INSERT statements.
    """
    match = INSERT_RE.search(sql)
    if not match:
        return None, None, []

    table_name = match.group(1)
    columns_raw = match.group(2)
    values_raw = match.group(3)

    # Parse column names
    columns = []
    for col in columns_raw.split(','):
        col = col.strip().strip('`').lower()
        if col == 'idstockinfo':
            continue  # Skip legacy-only field
        mapped = field_map.get(col)
        if mapped:
            columns.append(mapped)

    if not columns:
        return None, None, []

    # Parse value tuples — handle nested parentheses carefully
    rows = []
    depth = 0
    current = []
    token = ""
    in_string = False
    string_char = None
    i = 0
    values_section = values_raw.strip()

    while i < len(values_section):
        ch = values_section[i]

        if in_string:
            if ch == string_char:
                # Check for escaped quote
                if i + 1 < len(values_section) and values_section[i + 1] == string_char:
                    token += ch
                    i += 2
                    continue
                in_string = False
            token += ch
        elif ch in ("'", '"'):
            in_string = True
            string_char = ch
            token += ch
        elif ch == '(':
            if depth == 0:
                token = ""
            else:
                token += ch
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                current.append(token.strip())
                # Parse values
                vals = []
                for v in current:
                    vals.append(parse_value(v))
                if len(vals) == len(columns):
                    rows.append(tuple(vals))
                current = []
                token = ""
            else:
                token += ch
        elif ch == ',' and depth == 1:
            current.append(token.strip())
            token = ""
        elif depth >= 1:
            token += ch

        i += 1

    return table_name, columns, rows


def migrate_dump(dump_file, source_name, db_config):
    """
    Stream-parse a MySQL dump file and insert into the new partitioned schema.
    """
    field_map = FIELD_MAP_STOCK_MARKET if 'stock_market' in source_name \
        else FIELD_MAP_BACK_FINANCE

    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Get existing symbols for dedup
        cursor.execute("SELECT COUNT(*) FROM stockprices")
        existing_before = cursor.fetchone()[0]
        print(f"Existing price rows: {existing_before}")

        insert_sql = """
            INSERT IGNORE INTO stockprices
            (symbol, price_date, previous_close, day_open, day_low, day_high,
             day_close, day_change, adj_close, volume, bid, ask, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        batch = []
        total_inserted = 0
        total_parsed = 0
        errors = 0
        line_buffer = ""

        # Determine if reading from file or stdin
        fh = open(dump_file, 'r', encoding='utf-8', errors='replace') \
            if dump_file != '-' else sys.stdin

        print(f"Processing dump: {dump_file or 'stdin'} (source: {source_name})")

        for line in fh:
            line = line.strip()
            if not line or line.startswith('--') or line.startswith('/*'):
                continue

            line_buffer += " " + line

            # Check if we have a complete INSERT statement
            if line_buffer.rstrip().endswith(';'):
                try:
                    table, columns, rows = parse_insert_statement(
                        line_buffer, field_map, source_name
                    )
                    if table and table.lower() in ('stockprices', 'prices') and rows:
                        for row in rows:
                            # Pad or trim row to match expected columns
                            # Expected: symbol, price_date, previous_close, day_open,
                            #   day_low, day_high, day_close, day_change, adj_close,
                            #   volume, bid, ask = 12 fields + source
                            if len(row) >= 10:
                                # Build complete row
                                row_dict = dict(zip(columns, row))
                                ordered = [
                                    row_dict.get('symbol'),
                                    row_dict.get('price_date'),
                                    row_dict.get('previous_close'),
                                    row_dict.get('day_open'),
                                    row_dict.get('day_low'),
                                    row_dict.get('day_high'),
                                    row_dict.get('day_close'),
                                    row_dict.get('day_change'),
                                    row_dict.get('adj_close'),
                                    row_dict.get('volume'),
                                    row_dict.get('bid'),
                                    row_dict.get('ask'),
                                    source_name,
                                ]
                                batch.append(tuple(ordered))
                                total_parsed += 1

                                if len(batch) >= BATCH_SIZE:
                                    cursor.executemany(insert_sql, batch)
                                    conn.commit()
                                    total_inserted += len(batch)
                                    print(f"  Inserted {total_inserted:,} rows...")
                                    batch = []

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"  Parse error: {e}")
                        print(f"  Line buffer: {line_buffer[:200]}")

                line_buffer = ""

        # Flush remaining batch
        if batch:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            total_inserted += len(batch)

        if dump_file != '-':
            fh.close()

        # Final stats
        cursor.execute("SELECT COUNT(*) FROM stockprices")
        existing_after = cursor.fetchone()[0]

        print(f"\n{'='*60}")
        print(f"Migration complete for: {source_name}")
        print(f"  Rows parsed from dump:  {total_parsed:,}")
        print(f"  Rows inserted (IGNORE): {total_inserted:,}")
        print(f"  Parse errors:           {errors}")
        print(f"  Table before:           {existing_before:,}")
        print(f"  Table after:            {existing_after:,}")
        print(f"{'='*60}")

        cursor.close()

    except Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            conn.close()


def migrate_stockinfo(dump_file, source_name, db_config):
    """Migrate stockinfo table from legacy dump."""
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    insert_sql = """
        INSERT IGNORE INTO stockinfo
        (stocksymbol, exchange, corporatename, `52high`, `52low`, sector, industry, market_cap)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            corporatename = VALUES(corporatename),
            sector = COALESCE(VALUES(sector), sector),
            industry = COALESCE(VALUES(industry), industry),
            market_cap = COALESCE(VALUES(market_cap), market_cap)
    """

    batch = []
    total = 0
    line_buffer = ""
    fh = open(dump_file, 'r', encoding='utf-8', errors='replace') \
        if dump_file != '-' else sys.stdin

    for line in fh:
        line = line.strip()
        if not line or line.startswith('--') or line.startswith('/*') \
                or not line.upper().startswith('INSERT'):
            continue

        line_buffer += " " + line
        if line_buffer.rstrip().endswith(';'):
            # Parse stockinfo INSERTs
            match = re.search(
                r"INSERT.*?INTO\s+`?stockinfo`?\s*\(([^)]+)\)\s+VALUES\s+(.+);",
                line_buffer, re.IGNORECASE | re.DOTALL
            )
            if match:
                cols = [c.strip().strip('`').lower() for c in match.group(1).split(',')]
                vals_section = match.group(2)

                # Simple single-row parser for stockinfo
                row_match = re.search(r"\((.+)\)", vals_section, re.DOTALL)
                if row_match:
                    vals = [parse_value(v) for v in row_match.group(1).split(',')]
                    if len(vals) >= 3:
                        # Map to new schema - pad with NULLs
                        row = (
                            vals[0] if len(vals) > 0 else None,  # stocksymbol
                            vals[1] if len(vals) > 1 else None,  # exchange
                            vals[2] if len(vals) > 2 else None,  # corporatename
                            vals[3] if len(vals) > 3 else None,  # 52high
                            vals[4] if len(vals) > 4 else None,  # 52low
                            vals[5] if len(vals) > 5 else None,  # sector
                            vals[6] if len(vals) > 6 else None,  # industry
                            vals[7] if len(vals) > 7 else None,  # market_cap
                        )
                        batch.append(row)
                        if len(batch) >= 1000:
                            cursor.executemany(insert_sql, batch)
                            conn.commit()
                            total += len(batch)
                            batch = []
            line_buffer = ""

    if batch:
        cursor.executemany(insert_sql, batch)
        conn.commit()
        total += len(batch)

    if dump_file != '-':
        fh.close()

    print(f"Migrated {total:,} stockinfo rows")
    cursor.close()
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate legacy MySQL dumps to partitioned schema')
    parser.add_argument('--dump', required=True, help='Path to MySQL dump file (or - for stdin)')
    parser.add_argument('--source', required=True, choices=['legacy_stock_market', 'back_finance'],
                        help='Source system identifier')
    parser.add_argument('--table', default='stockprices',
                        choices=['stockprices', 'stockinfo', 'dividends', 'portfolio'],
                        help='Table to migrate')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--user', default='ksf_stockmarket')
    parser.add_argument('--password', default='change_me')
    parser.add_argument('--database', default='ksf_stockmarket')

    args = parser.parse_args()

    db_config = {
        **DB_CONFIG,
        'host': args.host,
        'user': args.user,
        'password': args.password,
        'database': args.database,
    }

    if args.table == 'stockprices':
        migrate_dump(args.dump, args.source, db_config)
    elif args.table == 'stockinfo':
        migrate_stockinfo(args.dump, args.source, db_config)
    else:
        print(f"Migration for {args.table} not yet implemented")
