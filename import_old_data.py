#!/usr/bin/env python3
"""
import_old_data.py — Transform and import old per-symbol data into new unified schema.

Reads MYSQL.stock_market_2.sql and imports:
- SYMBOL_prices → stockprices table
- SYMBOL_technical → indicators_json table  
- SYMBOL_fundamentals → fundamentals table
- SYMBOL_analysis → analysis table
"""
import sys
import os
import re
import pymysql
import json
from datetime import datetime

DB_CONFIG = {
    'host': 'ksfraser.ca',
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4'
}

OLD_DB = '/home/ksf_stockmarket/MYSQL.stock_market_2.sql'

def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def parse_sql_file(filepath):
    """Parse a MySQL dump file and yield (table_name, columns, values) tuples."""
    with open(filepath, 'r', encoding='utf8', errors='replace') as f:
        content = f.read()

    # Find all INSERT INTO ... VALUES blocks
    # Pattern: INSERT INTO `table` (cols) VALUES (vals), (vals), ...;
    pattern = r'INSERT\s+(?:IGNORE\s+)?INTO\s+`(\w+)`\s*\(([^)]+)\)\s*VALUES\s+(.+?);'
    for match in re.finditer(pattern, content, re.DOTALL):
        table = match.group(1)
        cols = [c.strip().strip('`') for c in match.group(2).split(',')]
        values_str = match.group(3)
        
        # Parse value tuples
        # Handle multi-line values like (1,2,3),(4,5,6)
        val_tuples = re.findall(r'\(([^)]+)\)', values_str)
        for val_str in val_tuples:
            vals = []
            for v in val_str.split(','):
                v = v.strip()
                if v.startswith("'") and v.endswith("'"):
                    vals.append(v[1:-1])  # strip quotes
                elif v == 'NULL':
                    vals.append(None)
                else:
                    try:
                        vals.append(int(v))
                    except ValueError:
                        try:
                            vals.append(float(v))
                        except ValueError:
                            vals.append(v)
            yield table, cols, vals

def import_prices(db, table, cols, vals):
    """Import a row from SYMBOL_prices into stockprices."""
    row = dict(zip(cols, vals))
    symbol = table.replace('_prices', '')
    
    # Map old columns to new
    date = row.get('date')
    if not date or date == '0000-00-00':
        return 0
    
    open_p = row.get('open_price', 0) or 0
    high_p = row.get('high_price', 0) or 0
    low_p = row.get('low_price', 0) or 0
    close_p = row.get('close_price', 0) or 0
    volume = row.get('volume', 0) or 0
    
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO stockprices (symbol, price_date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE open=%s, high=%s, low=%s, close=%s, volume=%s
            """, (symbol, date, open_p, high_p, low_p, close_p, volume,
                  open_p, high_p, low_p, close_p, volume))
        db.commit()
        return 1
    except Exception as e:
        db.rollback()
        print(f"  ERROR {symbol} {date}: {e}")
        return 0

def import_technical(db, table, cols, vals):
    """Import a row from SYMBOL_technical into indicators_json."""
    row = dict(zip(cols, vals))
    symbol = table.replace('_technical', '')
    date = row.get('date')
    if not date or date == '0000-00-00':
        return 0
    
    # Build JSON blob from all indicator columns
    indicators = {}
    skip_cols = {'id', 'date', 'created_at', 'updated_at'}
    for col, val in row.items():
        if col not in skip_cols and val is not None:
            try:
                indicators[col] = float(val)
            except (ValueError, TypeError):
                pass
    
    if not indicators:
        return 0
    
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO indicators_json (symbol, price_date, data)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE data=%s
            """, (symbol, date, json.dumps(indicators), json.dumps(indicators)))
        db.commit()
        return 1
    except Exception as e:
        db.rollback()
        print(f"  ERROR {symbol} {date}: {e}")
        return 0

def import_fundamentals(db, table, cols, vals):
    """Import a row from SYMBOL_fundamentals."""
    row = dict(zip(cols, vals))
    symbol = table.replace('_fundamentals', '')
    report_date = row.get('report_date')
    if not report_date or report_date == '0000-00-00':
        return 0
    
    # Map old columns to new fundamentals table
    mapping = {
        'market_cap': 'market_cap',
        'enterprise_value': 'enterprise_value',
        'pe_ratio': 'trailing_pe',
        'forward_pe': 'forward_pe',
        'peg_ratio': 'peg_ratio',
        'price_to_book': 'price_to_book',
        'price_to_sales': 'price_to_sales',
        'ev_to_revenue': 'ev_to_revenue',
        'ev_to_ebitda': 'ev_to_ebitda',
        'gross_margin': 'gross_margin',
        'operating_margin': 'operating_margin',
        'net_margin': 'profit_margin',
        'return_on_equity': 'roe',
    }
    
    fields = []
    values = []
    for old_col, new_col in mapping.items():
        if old_col in row and row[old_col] is not None:
            fields.append(new_col)
            values.append(row[old_col])
    
    if not fields:
        return 0
    
    fields.append('symbol')
    fields.append('report_date')
    values.append(symbol)
    values.append(report_date)
    
    placeholders = ','.join(['%s'] * len(fields))
    col_names = ','.join(fields)
    
    try:
        with db.cursor() as cur:
            cur.execute(f"""
                INSERT INTO fundamentals ({col_names})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {','.join(f'{f}=VALUES({f})' for f in fields[:-2])}
            """, values)
        db.commit()
        return 1
    except Exception as e:
        db.rollback()
        # Table might not exist yet
        if "doesn't exist" in str(e):
            return -1
        print(f"  ERROR {symbol} {report_date}: {e}")
        return 0

def import_analysis(db, table, cols, vals):
    """Import a row from SYMBOL_analysis."""
    row = dict(zip(cols, vals))
    symbol = table.replace('_analysis', '')
    analysis_date = row.get('analysis_date')
    if not analysis_date or analysis_date == '0000-00-00':
        return 0
    
    # Store as JSON in a new analysis_json table
    data = {}
    skip_cols = {'id', 'analysis_date', 'llm_analysis', 'llm_reasoning', 'llm_model', 'llm_tokens_used'}
    for col, val in row.items():
        if col not in skip_cols and val is not None:
            try:
                data[col] = float(val) if isinstance(val, (int, float)) else str(val)
            except:
                pass
    
    if not data:
        return 0
    
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO analysis_json (symbol, analysis_date, data)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE data=%s
            """, (symbol, analysis_date, json.dumps(data), json.dumps(data)))
        db.commit()
        return 1
    except Exception as e:
        db.rollback()
        if "doesn't exist" in str(e):
            return -1
        print(f"  ERROR {symbol} {analysis_date}: {e}")
        return 0

def ensure_tables(db):
    """Create new tables if they don't exist."""
    with db.cursor() as cur:
        # analysis_json table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analysis_json (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                analysis_date DATE NOT NULL,
                data JSON,
                UNIQUE KEY uk_symbol_date (symbol, analysis_date),
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # fundamentals table (extended)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fundamentals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                report_date DATE,
                market_cap BIGINT,
                enterprise_value BIGINT,
                trailing_pe DECIMAL(8,2),
                forward_pe DECIMAL(8,2),
                peg_ratio DECIMAL(8,2),
                price_to_book DECIMAL(8,2),
                price_to_sales DECIMAL(8,2),
                ev_to_revenue DECIMAL(8,2),
                ev_to_ebitda DECIMAL(8,2),
                gross_margin DECIMAL(8,4),
                operating_margin DECIMAL(8,4),
                profit_margin DECIMAL(8,4),
                roe DECIMAL(8,4),
                UNIQUE KEY uk_symbol_date (symbol, report_date),
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    db.commit()

def main():
    db = get_db()
    ensure_tables(db)
    
    # Counters
    stats = {
        'prices': {'ok': 0, 'err': 0},
        'technical': {'ok': 0, 'err': 0},
        'fundamentals': {'ok': 0, 'err': 0, 'no_table': 0},
        'analysis': {'ok': 0, 'err': 0, 'no_table': 0},
    }
    
    total_rows = 0
    
    print(f"Parsing {OLD_DB}...")
    for table, cols, vals in parse_sql_file(OLD_DB):
        total_rows += 1
        
        if table.endswith('_prices'):
            n = import_prices(db, table, cols, vals)
            if n > 0:
                stats['prices']['ok'] += 1
            elif n < 0:
                stats['prices']['err'] += 1
        elif table.endswith('_technical'):
            n = import_technical(db, table, cols, vals)
            if n > 0:
                stats['technical']['ok'] += 1
            elif n < 0:
                stats['technical']['err'] += 1
        elif table.endswith('_fundamentals'):
            n = import_fundamentals(db, table, cols, vals)
            if n > 0:
                stats['fundamentals']['ok'] += 1
            elif n == -1:
                stats['fundamentals']['no_table'] += 1
            else:
                stats['fundamentals']['err'] += 1
        elif table.endswith('_analysis'):
            n = import_analysis(db, table, cols, vals)
            if n > 0:
                stats['analysis']['ok'] += 1
            elif n == -1:
                stats['analysis']['no_table'] += 1
            else:
                stats['analysis']['err'] += 1
        
        if total_rows % 1000 == 0:
            print(f"  Processed {total_rows} rows...")
    
    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE")
    print(f"{'='*60}")
    print(f"Total rows parsed: {total_rows}")
    for table_type, counts in stats.items():
        print(f"  {table_type}: {counts}")
    
    # Verify
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM stockprices")
        print(f"\nTotal stockprices rows: {cur.fetchone()['cnt']:,}")
        cur.execute("SELECT COUNT(*) as cnt FROM indicators_json")
        print(f"Total indicators_json rows: {cur.fetchone()['cnt']:,}")
        cur.execute("SELECT COUNT(DISTINCT symbol) as cnt FROM stockprices")
        print(f"Symbols with prices: {cur.fetchone()['cnt']}")
    
    db.close()

if __name__ == "__main__":
    main()
