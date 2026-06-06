#!/usr/bin/env python3
"""
Import MYSQL.stock_market_2.sql into temp tables with 'old_' prefix.
Reads the dump, transforms table names, and executes against MariaDB.
"""
import re
import sys
import pymysql

# DB connection
DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_USER = 'stock_user'
DB_PASS = 'stock_pass'
DB_NAME = 'stock_market'

SQL_FILE = '/home/ksf_stockmarket/MYSQL.stock_market_2.sql'

def get_connection():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_NAME,
        charset='utf8mb4',
        autocommit=False
    )

def transform_sql(raw):
    """Transform the SQL dump to use old_ prefixed table names in our DB."""
    # Remove CREATE DATABASE and USE statements
    raw = re.sub(r'CREATE DATABASE.*?;', '', raw, flags=re.DOTALL)
    raw = re.sub(r'USE\s+`?\w+`?\s*;', '', raw)
    
    # Replace table names: `SYMBOL_tablename` -> `old_SYMBOL_tablename`
    # Match backtick-quoted table names
    def replace_table(match):
        name = match.group(1)
        # Don't double-prefix
        if name.startswith('old_'):
            return match.group(0)
        return f'`old_{name}`'
    
    # Replace in CREATE TABLE, DROP TABLE, ALTER TABLE, LOCK TABLES, etc.
    raw = re.sub(r'`([A-Za-z0-9_]+)`', replace_table, raw)
    
    return raw

def split_statements(sql):
    """Split SQL into individual statements, handling delimiters properly."""
    statements = []
    current = []
    in_string = False
    string_char = None
    escaped = False
    
    for char in sql:
        if escaped:
            current.append(char)
            escaped = False
            continue
        
        if char == '\\':
            current.append(char)
            escaped = True
            continue
        
        if in_string:
            current.append(char)
            if char == string_char:
                in_string = False
            continue
        
        if char in ("'", '"', '`'):
            in_string = True
            string_char = char
            current.append(char)
            continue
        
        if char == ';':
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            continue
        
        current.append(char)
    
    # Don't forget last statement without semicolon
    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)
    
    return statements

def main():
    print(f"Reading {SQL_FILE}...")
    with open(SQL_FILE, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()
    
    print(f"Read {len(raw):,} bytes")
    
    print("Transforming SQL...")
    transformed = transform_sql(raw)
    
    print("Splitting into statements...")
    statements = split_statements(transformed)
    print(f"Found {len(statements):,} statements")
    
    # Filter out empty/comment-only statements
    executable = []
    for s in statements:
        stripped = s.strip()
        if not stripped or stripped.startswith('--') or stripped.startswith('/*'):
            continue
        # Skip SET statements that might cause issues
        if stripped.upper().startswith('SET ') and ('@OLD_' in stripped.upper() or 'CHARACTER_SET' in stripped.upper() or 'TIME_ZONE' in stripped.upper() or 'UNIQUE_CHECKS' in stripped.upper() or 'FOREIGN_KEY' in stripped.upper() or 'SQL_MODE' in stripped.upper() or 'SQL_NOTES' in stripped.upper()):
            continue
        executable.append(stripped)
    
    print(f"Executable statements: {len(executable):,}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Disable keys and checks for speed
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
    cursor.execute("SET UNIQUE_CHECKS=0;")
    cursor.execute("SET AUTOCOMMIT=0;")
    
    success = 0
    errors = 0
    error_log = []
    
    for i, stmt in enumerate(executable):
        try:
            cursor.execute(stmt)
            success += 1
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i+1}/{len(executable)} ({success} ok, {errors} errors)")
                conn.commit()
        except Exception as e:
            errors += 1
            err_msg = str(e)[:200]
            error_log.append(f"#{i}: {err_msg}\n  SQL: {stmt[:150]}...")
            if errors <= 20:
                print(f"  ERROR #{i}: {err_msg}")
        
        # Commit every 500 statements
        if (i + 1) % 500 == 0:
            conn.commit()
    
    conn.commit()
    
    # Re-enable checks
    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    cursor.execute("SET UNIQUE_CHECKS=1;")
    
    cursor.close()
    conn.close()
    
    print(f"\n=== DONE ===")
    print(f"Success: {success:,}")
    print(f"Errors:  {errors:,}")
    
    if error_log:
        print(f"\nFirst 20 errors:")
        for e in error_log[:20]:
            print(f"  {e}")

if __name__ == '__main__':
    main()
