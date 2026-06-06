#!/usr/bin/env python3
"""
Import MYSQL.stock_market_2.sql per-symbol PRICE data into unified stockprices table.
"""
import re
import pymysql

DB_HOST = 'ksfraser.ca'
DB_PORT = 3306
DB_USER = 'ksfraser_stockmarket'
DB_PASS = 'Zaqwsx9sm1@'
DB_NAME = 'ksfraser_stock_market'
SQL_FILE = '/home/ksf_stockmarket/MYSQL.stock_market_2.sql'

def get_connection():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset='utf8mb4', autocommit=False
    )

def convert_value(v):
    v = v.strip()
    if v == 'NULL':
        return None
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    try:
        return float(v) if '.' in v else int(v)
    except ValueError:
        return v

def parse_insert_line(line):
    """Parse a single INSERT INTO ... VALUES (...) line.
    Returns (table_name, list_of_row_tuples) or None.
    """
    m = re.match(r"INSERT\s+.*INTO\s+`(\w+)`\s+.*?VALUES\s+(.*)", line, re.IGNORECASE)
    if not m:
        return None
    
    table_name = m.group(1)
    values_str = m.group(2).rstrip(';').strip()
    
    # Parse tuples: (val1, val2, ...), (val1, val2, ...)
    rows = []
    i = 0
    length = len(values_str)
    
    while i < length:
        # Skip to next (
        while i < length and values_str[i] != '(':
            i += 1
        if i >= length:
            break
        i += 1  # skip (
        
        # Parse values until matching )
        depth = 1
        in_str = False
        esc = False
        cur = []
        vals = []
        
        while i < length and depth > 0:
            ch = values_str[i]
            if esc:
                if in_str:
                    cur.append(ch)
                esc = False
                i += 1
                continue
            if ch == '\\':
                esc = True
                i += 1
                continue
            if ch == "'":
                in_str = not in_str
                i += 1
                continue
            if in_str:
                cur.append(ch)
                i += 1
                continue
            if ch == '(':
                depth += 1
                cur.append(ch)
                i += 1
                continue
            if ch == ')':
                depth -= 1
                if depth == 0:
                    vs = ''.join(cur).strip()
                    if vs:
                        vals.append(convert_value(vs))
                    if vals:
                        rows.append(vals)
                    i += 1
                    break
                cur.append(ch)
                i += 1
                continue
            if ch == ',' and depth == 1:
                vs = ''.join(cur).strip()
                vals.append(convert_value(vs))
                cur = []
                i += 1
                continue
            cur.append(ch)
            i += 1
    
    return table_name, rows

def main():
    print("=" * 60)
    print("Import Old System Prices → Unified stockprices")
    print("=" * 60)
    
    # Read file line by line, extract INSERT statements from *_prices tables
    print(f"Reading {SQL_FILE}...")
    price_inserts = {}  # symbol -> list of (table_name, rows)
    other_inserts = {}  # for technical, fundamentals, analysis
    
    with open(SQL_FILE, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line.upper().startswith('INSERT'):
                continue
            
            result = parse_insert_line(line)
            if not result:
                continue
            
            table_name, rows = result
            if not rows:
                continue
            
            # Categorize
            if table_name.endswith('_prices'):
                sym = table_name[:-7]  # strip _prices
                if sym not in price_inserts:
                    price_inserts[sym] = []
                price_inserts[sym].append((table_name, rows))
            elif table_name.endswith(('_technical', '_fundamentals', '_analysis')):
                sym = table_name.rsplit('_', 1)[0]
                if sym not in other_inserts:
                    other_inserts[sym] = []
                other_inserts[sym].append((table_name, rows))
    
    print(f"Found price data for {len(price_inserts)} symbols")
    print(f"Found other data for {len(other_inserts)} symbols")
    
    # Connect to DB
    print(f"\nConnecting to {DB_NAME}@{DB_HOST}...")
    conn = get_connection()
    cur = conn.cursor()
    print("Connected!")
    
    # Get existing symbols
    cur.execute("SELECT DISTINCT symbol FROM stockprices")
    existing = {r[0] for r in cur.fetchall()}
    print(f"Existing symbols in stockprices: {len(existing)}")
    
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("SET UNIQUE_CHECKS=0")
    
    total_inserted = 0
    total_skipped = 0
    errors = 0
    
    for sym in sorted(price_inserts.keys()):
        # Check existing
        if sym in existing:
            cur.execute("SELECT COUNT(*) FROM stockprices WHERE symbol = %s", (sym,))
            count = cur.fetchone()[0]
            if count > 100:
                total_skipped += 1
                continue
        
        sym_rows = price_inserts[sym]
        inserted = 0
        
        for table_name, rows in sym_rows:
            for row in rows:
                try:
                    # Old: (id, date, open_price, high_price, low_price, close_price, adj_close_price, volume, split_coefficient, dividend_amount, data_source, created_at, updated_at)
                    if len(row) < 8:
                        continue
                    
                    date_val = row[1]
                    open_val = row[2]
                    high_val = row[3]
                    low_val = row[4]
                    close_val = row[5]
                    adj_close_val = row[6]
                    volume_val = row[7] if row[7] is not None else 0
                    split_val = row[8] if len(row) > 8 and row[8] is not None else 1.0
                    dividend_val = row[9] if len(row) > 9 and row[9] is not None else 0.0
                    
                    if date_val is None or open_val is None or close_val is None:
                        continue
                    
                    cur.execute("""
                        INSERT IGNORE INTO stockprices 
                        (symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (sym, date_val, open_val, high_val, low_val, close_val,
                          volume_val, adj_close_val, dividend_val, split_val))
                    
                    if cur.rowcount > 0:
                        inserted += 1
                        total_inserted += 1
                        
                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        print(f"  ERROR {sym}: {e}")
        
        conn.commit()
        
        if inserted > 0 or total_skipped % 50 == 0:
            print(f"  {sym}: +{inserted} rows (total new: {total_inserted:,}, skipped: {total_skipped})")
    
    cur.execute("SET FOREIGN_KEY_CHECKS=1")
    cur.execute("SET UNIQUE_CHECKS=1")
    
    cur.execute("SELECT COUNT(*) FROM stockprices")
    final = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE")
    print(f"{'='*60}")
    print(f"Symbols with price data: {len(price_inserts)}")
    print(f"Symbols skipped (existing): {total_skipped}")
    print(f"New rows inserted: {total_inserted:,}")
    print(f"Errors: {errors}")
    print(f"Total stockprices rows: {final:,}")

if __name__ == '__main__':
    main()
