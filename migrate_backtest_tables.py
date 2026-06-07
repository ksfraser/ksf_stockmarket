#!/usr/bin/env python3
"""Migrate backtest-related tables from SQLite to MariaDB."""
import pymysql
import sqlite3
import json

SQLITE_PATH = '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'

# MariaDB connection
mdb = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market')

# SQLite connection  
sq = sqlite3.connect(SQLITE_PATH)
sq.row_factory = sqlite3.Row

# Tables to migrate
TABLES = [
    'backtest_runs',
    'backtest_trades', 
    'backtest_runs_v2',
    'backtest_trades_v2',
    'pipeline_v2_results',
    'pipeline_v3_walkforward',
    'data_import_log',
    'strategy_performance',
    'full_correlation_results',
    'strategy_pipeline_results',
    'ta_indicators',
    'layer1_signals',
    'layer2_positions',
    'layer3_candidates',
    'layer3_portfolios',
]

def sqlite_type_to_mysql(t):
    """Convert SQLite type to MySQL type."""
    t = t.upper()
    if 'INTEGER' in t:
        return 'BIGINT'
    if 'TEXT' in t:
        return 'TEXT'
    if 'REAL' in t:
        return 'DOUBLE'
    return t

for table in TABLES:
    # Get SQLite schema
    sq_cur = sq.cursor()
    sq_cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
    result = sq_cur.fetchone()
    if not result:
        print(f"SKIP {table} - not found in SQLite")
        continue
    
    sqlite_sql = result[0]
    
    # Get column info
    sq_cur.execute(f"PRAGMA table_info({table})")
    columns = sq_cur.fetchall()
    
    # Build MySQL CREATE
    col_defs = []
    for col in columns:
        col_name = col[1]
        col_type = sqlite_type_to_mysql(col[2])
        nullable = 'NOT NULL' if col[3] == 1 else 'NULL'
        default = f" DEFAULT {col[4]}" if col[4] else ''
        col_defs.append(f"    {col_name} {col_type} {nullable}{default}")
    
    # MySQLify
    mysql_sql = sqlite_sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'BIGINT PRIMARY KEY AUTO_INCREMENT')
    mysql_sql = mysql_sql.replace(f'CREATE TABLE {table}', f'CREATE TABLE IF NOT EXISTS {table}')
    mysql_sql = mysql_sql.replace('CURRENT_TIMESTAMP', "CURRENT_TIMESTAMP")
    
    # Check if table exists in MariaDB
    mdb_cur = mdb.cursor()
    mdb_cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s", 
                    ('ksfraser_stock_market', table))
    if mdb_cur.fetchone()[0]:
        print(f"EXISTS {table} - skipping creation")
    else:
        print(f"CREATE {table}")
        mdb_cur.execute(mysql_sql)
        mdb.commit()

sq.close()
mdb.close()
print("Schema migration complete")