#!/usr/bin/env python3
"""
apply_migration.py — Apply pending SQL migration files to production MariaDB.
Usage:
  python3 apply_migration.py sql/signal_validation.sql
  python3 apply_migration.py sql/signal_validation.sql sql/advisors.sql

Reads DB credentials from config.yaml via config_loader.
"""
import sys
import mysql.connector

sys.path.insert(0, '.')
from config_loader import Config


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 apply_migration.py <sql_file> [<sql_file> ...]")
        sys.exit(1)

    cfg = Config('config.yaml')
    db_cfg = cfg.data
    conn = mysql.connector.connect(
        host=getattr(db_cfg, 'db_host', 'ksfraser.ca'),
        user=getattr(db_cfg, 'db_user', 'ksfraser_stockmarket'),
        password=cfg.db_password,
        database=getattr(db_cfg, 'db_name', 'ksfraser_stock_market'),
        port=int(getattr(db_cfg, 'port', 3306)),
        charset='utf8mb4',
        autocommit=False,
    )
    cur = conn.cursor()

    for path in sys.argv[1:]:
        sql = open(path).read()
        stmts = [s.strip() for s in sql.split(';') if s.strip()]
        for stmt in stmts:
            try:
                cur.execute(stmt)
                print(f"  OK: {stmt[:60]}...")
            except mysql.connector.Error as e:
                print(f"  WARN: {e} | {stmt[:60]}")

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete.")


if __name__ == '__main__':
    main()
