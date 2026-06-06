#!/usr/bin/env python3
"""
import_to_temp.py — Import old SQL dumps into temp tables with 'old_' prefix.

Reads the SQL dump files and imports into the current DB with old_ prefixed table names.
"""
import sys
import os
import re
import pymysql

DB_CONFIG = {
    'host': 'ksfraser.ca',
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
    'max_allowed_packet': 64 * 1024 * 1024,
}

DUMP_MAIN = '/home/ksf_stockmarket/MYSQL.stock_market.sql'
DUMP_PER = '/home/ksf_stockmarket/MYSQL.stock_market_2.sql'


def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


def extract_table_statements(content, table_name):
    """Extract all SQL statements for a specific table."""
    statements = []
    lines = content.split('\n')
    current_lines = []
    in_table = False
    
    for line in lines:
        # Check if this line starts a block for our table
        if any(pattern in line for pattern in [
            f'TABLE `{table_name}`',
            f'TABLE IF NOT EXISTS `{table_name}`',
            f'INTO `{table_name}`',
            f'TABLES `{table_name}`',
        ]):
            in_table = True
        
        if in_table:
            current_lines.append(line)
            # End of block: empty line or new table section
            if line.strip().startswith('--') and 'Table structure' in line and table_name not in line:
                # Save current block (remove last line which is the next header)
                if len(current_lines) > 1:
                    statements.append('\n'.join(current_lines[:-1]))
                current_lines = []
                in_table = False
            elif line.strip().startswith('/*!'):
                # End of data block
                statements.append('\n'.join(current_lines))
                current_lines = []
                in_table = False
    
    # Don't forget last block
    if current_lines:
        statements.append('\n'.join(current_lines))
    
    return statements


def import_dump_sql(db, filepath, label):
    """Import SQL dump by replacing table names with old_ prefixed versions."""
    print(f"\nProcessing {label}: {filepath}")
    
    with open(filepath, 'r', encoding='latin1', errors='replace') as f:
        content = f.read()
    
    # Get all table names from CREATE TABLE statements
    tables = set(re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`(\w+)`', content))
    print(f"  Found {len(tables)} unique tables")
    
    # For each table, extract and transform its statements
    total_executed = 0
    total_errors = 0
    
    for table_name in sorted(tables):
        old_table = f'old_{table_name}'
        
        # Extract statements for this table
        blocks = extract_table_statements(content, table_name)
        if not blocks:
            continue
        
        # Transform: replace table name with old_ prefixed version
        transformed = []
        joined = '\n'.join(blocks)
        s = joined
        s = re.sub(rf'`{re.escape(table_name)}`', f'`{old_table}`', s)
        # Handle LOCK TABLES / UNLOCK TABLES
        s = re.sub(r'LOCK\s+TABLES\s+\S+', '', s)
        s = re.sub(r'UNLOCK\s+TABLES', '', s)
        s = re.sub(r'/\*!\d+\s+ALTER\s+.*?\*/', '', s)
        if s.strip():
            transformed.append(s)
        
        sql = '\n'.join(transformed)
        if not sql.strip():
            continue
        
        # Execute
        cursor = db.cursor()
        try:
            # Execute the whole block
            cursor.execute(sql)
            db.commit()
            # Count rows affected
            rows = cursor.rowcount
            total_executed += 1
            print(f"  {table_name} → {old_table}: OK (last rowcount={rows})")
        except Exception as e:
            db.rollback()
            total_errors += 1
            # Try executing line by line
            line_ok = 0
            line_err = 0
            for stmt in sql.split(';'):
                stmt = stmt.strip()
                if not stmt or stmt.startswith('--') or stmt.startswith('/*'):
                    continue
                try:
                    cursor.execute(stmt)
                    line_ok += 1
                except:
                    line_err += 1
            db.commit()
            print(f"  {table_name} → {old_table}: PARTIAL (ok={line_ok}, err={line_err})")
    
    print(f"Done: {total_executed} tables OK, {total_errors} had errors")
    return total_executed


def simple_import(db, filepath, label):
    """Simple approach: read file, do global table name replacement, execute statements."""
    print(f"\n{'='*60}")
    print(f"Importing {label}")
    print(f"{'='*60}")
    
    with open(filepath, 'r', encoding='latin1', errors='replace') as f:
        content = f.read()
    
    # Get all table names
    tables = sorted(set(re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`(\w+)`', content)))
    print(f"Tables to import: {len(tables)}")
    
    # Build rename map: original → old_ prefix, but not for system tables
    rename_map = {}
    for t in tables:
        old_name = f'old_{t}'
        rename_map[t] = old_name
    
    # Replace table names in the SQL
    modified = content
    for orig, new in rename_map.items():
        # Use word boundary to avoid partial matches
        modified = re.sub(rf'\b`{re.escape(orig)}`', f'`{new}`', modified)
    
    # Remove problematic statements
    lines = modified.split('\n')
    clean_lines = []
    for line in lines:
        s = line.strip()
        # Skip database-level commands
        if any(s.upper().startswith(x) for x in [
            'CREATE DATABASE', 'DROP DATABASE', 'USE ', 
            'LOCK TABLES', 'UNLOCK TABLES',
            'SET NAMES', 'SET CHARACTER', 'SET COLLATION',
            'SET TIME_ZONE', 'SET UNIQUE_CHECKS', 
            'SET FOREIGN_KEY_CHECKS', 'SET SQL_MODE', 'SET SQL_NOTES',
            'SET @OLD', 'SET SQL_LOG_BIN',
        ]):
            continue
        # Skip empty comment blocks
        if s == '/*!40101' or s == '*/;':
            continue
        clean_lines.append(line)
    
    clean_sql = '\n'.join(clean_lines)
    
    # Execute statement by statement
    cursor = db.cursor()
    statements = []
    current = ''
    for char in clean_sql:
        current += char
        if char == ';':
            stmt = current.strip()
            if stmt and len(stmt) > 10:  # skip tiny fragments
                statements.append(stmt)
            current = ''
    
    print(f"Total statements to execute: {len(statements)}")
    
    ok = 0
    err = 0
    err_samples = []
    
    for i, stmt in enumerate(statements):
        try:
            cursor.execute(stmt)
            ok += 1
        except Exception as e:
            err += 1
            if len(err_samples) < 10:
                err_samples.append(f"  {str(e)[:120]}")
        
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1}/{len(statements)} ({ok} ok, {err} err)")
    
    db.commit()
    
    print(f"\nResults: {ok} OK, {err} errors")
    if err_samples:
        print(f"Sample errors:")
        for e in err_samples[:5]:
            print(e)
    
    return ok, err


def verify(db):
    """Check what was imported."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT table_name, table_rows, 
               ROUND(data_length/1024/1024, 2) as data_mb
        FROM information_schema.tables 
        WHERE table_schema = 'ksfraser_stock_market' 
        AND table_name LIKE 'old_%'
        ORDER BY data_length DESC
    """)
    rows = cursor.fetchall()
    
    print(f"\n{'='*60}")
    print(f"VERIFICATION: {len(rows)} old_* tables")
    print(f"{'='*60}")
    total = 0
    for row in rows:
        print(f"  {row['table_name']:45s} rows={str(row['table_rows']):>10s}  {row['data_mb'] or 0} MB")
        total += row['table_rows'] or 0
    print(f"  {'TOTAL':45s} rows={total:>10,}")
    return rows


def main():
    db = get_db()
    
    # Import main dump
    simple_import(db, DUMP_MAIN, "Main dump (19 tables)")
    
    # Import per-symbol dump
    simple_import(db, DUMP_PER, "Per-symbol dump (245 symbols × 6 types)")
    
    # Verify
    verify(db)
    
    db.close()


if __name__ == "__main__":
    main()
