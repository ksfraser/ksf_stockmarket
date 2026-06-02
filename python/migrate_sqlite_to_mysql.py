#!/usr/bin/env python3
"""
migrate_sqlite_to_mysql.py — Migrate analytics data from SQLite to MySQL.

Migrates tables that don't exist in MySQL yet:
  - evalsummary
  - ta_indicators (wide format — 120+ columns)
  - backtest_runs / backtest_trades
  - strategy_pipeline_results
  - pipeline_v2_results
  - pipeline_v3_walkforward
  - indicator_correlation
  - full_correlation_results

Raw stockprices data NOT migrated — MySQL already has everything SQLite has.
"""

import sqlite3
import pymysql
import sys
import time
from config_loader import Config

SQLITE_PATH = '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'

# Credentials loaded from Ansible Vault via config_loader
_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
_cfg = Config(_cfg_path) if os.path.exists(_cfg_path) else Config()
MYSQL = dict(
    host=_cfg.data.db_host,
    user=_cfg.data.db_user,
    password=_cfg.db_password,
    database=_cfg.data.db_name,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

TABLES = [
    'evalsummary',
    'ta_indicators',
    'backtest_runs',
    'backtest_trades',
    'backtest_runs_v2',
    'backtest_trades_v2',
    'strategy_pipeline_results',
    'pipeline_v2_results',
    'pipeline_v3_walkforward',
    'indicator_correlation',
    'full_correlation_results',
]


def get_sqlite_tables(conn):
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [r[0] for r in c.fetchall()]


def get_sqlite_columns(conn, table):
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in c.fetchall()]


def table_exists_mysql(conn, table):
    c = conn.cursor()
    c.execute("SHOW TABLES LIKE %s", (table,))
    return c.fetchone() is not None


def create_table_mysql(sqlite_conn, mysql_conn, table):
    """Create table in MySQL based on SQLite schema."""
    cols = get_sqlite_columns(sqlite_conn, table)

    # Map SQLite types to MySQL
    col_defs = []
    pk_cols = []
    for col in cols:
        if col == 'id':
            col_defs.append(f"`id` INT AUTO_INCREMENT PRIMARY KEY")
        elif col in ('created_at', 'completed_at', 'updated_at', 'mapped_at'):
            col_defs.append(f"`{col}` TIMESTAMP NULL DEFAULT NULL")
        elif col in ('trade_date', 'entry_date', 'exit_date', 'rebalance_date'):
            col_defs.append(f"`{col}` DATE NULL DEFAULT NULL")
        elif col == 'price_date':
            col_defs.append(f"`{col}` DATE NOT NULL")
        elif col == 'symbol':
            col_defs.append(f"`symbol` VARCHAR(20) NOT NULL")
        elif col == 'strategy':
            col_defs.append(f"`strategy` VARCHAR(50) NULL")
        elif 'json' in col.lower() or col.endswith('_json'):
            col_defs.append(f"`{col}` JSON NULL")
        elif col in ('parameters', 'config_name', 'combo_names', 'verdict', 'error_message'):
            col_defs.append(f"`{col}` TEXT NULL")
        else:
            # Default: try to detect from sample data
            col_defs.append(f"`{col}` DOUBLE NULL")

    create_sql = f"CREATE TABLE IF NOT EXISTS `{table}` (\n  {','.join(col_defs)}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

    c = mysql_conn.cursor()
    c.execute(create_sql)
    mysql_conn.commit()

    # Add useful indexes
    if 'symbol' in cols:
        try:
            c.execute(f"CREATE INDEX idx_{table}_symbol ON `{table}`(symbol)")
            mysql_conn.commit()
        except:
            pass  # May already exist


def migrate_table(sqlite_conn, mysql_conn, table, batch_size=5000):
    """Copy all rows from SQLite to MySQL."""
    s = sqlite_conn.cursor()
    m = mysql_conn.cursor()

    cols = get_sqlite_columns(sqlite_conn, table)
    col_list = ','.join(f'`{c}`' for c in cols)
    placeholders = ','.join(['%s'] * len(cols))

    # Check existing count
    try:
        m.execute(f"SELECT COUNT(*) as n FROM `{table}`")
        existing = m.fetchone()['n']
    except:
        existing = 0

    s.execute(f"SELECT COUNT(*) FROM `{table}`")
    total = s.fetchone()[0]

    if total == 0:
        print(f"  {table}: 0 rows in SQLite, skipping")
        return

    print(f"  {table}: {total} rows in SQLite, {existing} in MySQL", end='')

    if existing >= total:
        print(" (already complete)")
        return

    # Truncate if partial data
    if existing > 0:
        m.execute(f"TRUNCATE TABLE `{table}`")
        mysql_conn.commit()
        print(" (re-migrating)", end='')

    # Migrate in batches
    s.execute(f"SELECT * FROM `{table}`")
    batch = []
    migrated = 0

    insert_sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"

    for row in s:
        batch.append(tuple(row))
        if len(batch) >= batch_size:
            m.executemany(insert_sql, batch)
            mysql_conn.commit()
            migrated += len(batch)
            batch = []
            print(f"\r  {table}: {migrated}/{total}", end='', flush=True)

    if batch:
        m.executemany(insert_sql, batch)
        mysql_conn.commit()
        migrated += len(batch)

    print(f" — {migrated} rows migrated ✓")


def main():
    print("=" * 60)
    print("SQLite → MySQL Migration")
    print("=" * 60)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    mysql_conn = pymysql.connect(**MYSQL)

    available = get_sqlite_tables(sqlite_conn)
    print(f"SQLite tables: {available}")
    print(f"Tables to migrate: {TABLES}")

    for table in TABLES:
        if table not in available:
            print(f"  {table}: not found in SQLite, skipping")
            continue

        if not table_exists_mysql(mysql_conn, table):
            print(f"  {table}: creating in MySQL...")
            create_table_mysql(sqlite_conn, mysql_conn, table)
        else:
            print(f"  {table}: table exists in MySQL")

        migrate_table(sqlite_conn, mysql_conn, table)

    # Verify
    print("\n" + "=" * 60)
    print("Verification:")
    m = mysql_conn.cursor()
    for table in TABLES:
        try:
            m.execute(f"SELECT COUNT(*) as n FROM `{table}`")
            n = m.fetchone()['n']
            print(f"  {table}: {n} rows in MySQL")
        except:
            print(f"  {table}: ERROR")

    sqlite_conn.close()
    mysql_conn.close()
    print("=" * 60)
    print("Migration complete.")


if __name__ == '__main__':
    main()
