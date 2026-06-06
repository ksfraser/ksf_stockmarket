#!/usr/bin/env python3
"""
Migrate ALL data from analysis_results.db (SQLite) to MySQL (ksfraser_stock_market).
After verification, the SQLite DB can be deleted to free ~275MB.
"""
import sqlite3
import pymysql
import sys

SQLITE_PATH = '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'
MYSQL_HOST = 'ksfraser.ca'
MYSQL_PORT = 3306
MYSQL_USER = 'ksfraser_stockmarket'
MYSQL_PASS = 'Zaqwsx9sm1@'
MYSQL_DB = 'ksfraser_stock_market'

# Tables to migrate (skip stockprices — MySQL already has it)
TABLES = [
    'daily_indicators',
    'data_import_log',
    'backtest_runs',
    'backtest_trades',
    'evalsummary',
    'backtest_runs_v2',
    'backtest_trades_v2',
    'strategy_pipeline_results',
    'pipeline_v2_results',
    'pipeline_v3_walkforward',
    'layer1_signals',
    'layer2_positions',
    'layer3_portfolios',
    'layer3_candidates',
    'strategy_performance',
    'indicator_correlation',
    'ta_indicators',
    'full_correlation_results',
]

def sqlite_type_to_mysql(sqlite_type):
    t = sqlite_type.upper()
    if 'INT' in t:
        return 'BIGINT NULL'
    if 'REAL' in t or 'FLOAT' in t or 'DOUBLE' in t:
        return 'DOUBLE NULL'
    if 'TEXT' in t or 'CHAR' in t or 'CLOB' in t:
        return 'TEXT NULL'
    if 'BLOB' in t:
        return 'BLOB NULL'
    if 'DATE' in t:
        return 'DATE NULL'
    if 'TIME' in t:
        return 'TIMESTAMP NULL'
    return 'TEXT NULL'

def main():
    print("=" * 60)
    print("SQLite → MySQL Migration")
    print("=" * 60)
    
    # Connect
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    mysql_conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB, charset='utf8mb4',
        autocommit=False
    )
    mysql_cur = mysql_conn.cursor()
    mysql_cur.execute("SET FOREIGN_KEY_CHECKS=0")
    mysql_cur.execute("SET UNIQUE_CHECKS=0")
    
    total_migrated = 0
    
    for table in TABLES:
        # Check SQLite has data
        sqlite_cur = sqlite_conn.cursor()
        sqlite_cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        sqlite_count = sqlite_cur.fetchone()[0]
        
        if sqlite_count == 0:
            print(f"  {table}: empty in SQLite, skipping")
            continue
        
        # Get SQLite schema
        sqlite_cur.execute(f"PRAGMA table_info(`{table}`)")
        columns = sqlite_cur.fetchall()
        col_names = [c[1] for c in columns]
        col_types = [c[2] for c in columns]
        
        # Check if MySQL table exists
        mysql_cur.execute(f"SHOW TABLES LIKE '{table}'")
        exists = mysql_cur.fetchone() is not None
        
        if not exists:
            # Create table
            col_defs = []
            for name, stype in zip(col_names, col_types):
                if name == 'id':
                    col_defs.append(f"`id` INT AUTO_INCREMENT PRIMARY KEY")
                else:
                    mysql_type = sqlite_type_to_mysql(stype)
                    col_defs.append(f"`{name}` {mysql_type}")
            
            create_sql = f"CREATE TABLE `{table}` ({', '.join(col_defs)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            try:
                mysql_cur.execute(create_sql)
                print(f"  {table}: created in MySQL")
            except Exception as e:
                print(f"  {table}: CREATE ERROR: {e}")
                continue
        else:
            # Check existing row count
            mysql_cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            existing = mysql_cur.fetchone()[0]
            if existing > 0:
                print(f"  {table}: MySQL already has {existing} rows, skipping")
                continue
        
        # Migrate data in batches
        sqlite_cur.execute(f"SELECT * FROM `{table}`")
        rows = sqlite_cur.fetchall()
        
        if not rows:
            continue
        
        placeholders = ', '.join(['%s'] * len(col_names))
        insert_sql = f"INSERT INTO `{table}` ({', '.join(f'`{c}`' for c in col_names)}) VALUES ({placeholders})"
        
        batch_size = 1000
        migrated = 0
        errors = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            for row in batch:
                try:
                    mysql_cur.execute(insert_sql, tuple(row))
                    migrated += 1
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"    ERROR: {e}")
            mysql_conn.commit()
        
        total_migrated += migrated
        print(f"  {table}: migrated {migrated:,} rows ({errors} errors)")
    
    mysql_cur.execute("SET FOREIGN_KEY_CHECKS=1")
    mysql_cur.execute("SET UNIQUE_CHECKS=1")
    
    # Verify
    print(f"\n--- Verification ---")
    for table in TABLES:
        mysql_cur.execute(f"SHOW TABLES LIKE '{table}'")
        if mysql_cur.fetchone():
            mysql_cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            cnt = mysql_cur.fetchone()[0]
            print(f"  {table}: {cnt:,} rows in MySQL")
    
    mysql_cur.close()
    mysql_conn.close()
    sqlite_conn.close()
    
    print(f"\nTotal rows migrated: {total_migrated:,}")
    print("SQLite DB can now be safely deleted to free ~275MB")

if __name__ == '__main__':
    main()
