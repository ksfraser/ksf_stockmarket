#!/usr/bin/env python3
"""
apply_migration.py — Apply pending SQL migration files to production MariaDB.
Uses a simple SQL-aware splitter that skips semicolons inside string literals.

Usage:
  python3 apply_migration.py <sql_file> [<sql_file> ...]
"""
import sys
import re
import mysql.connector

sys.path.insert(0, 'python')
from config_loader import Config


def split_sql(text: str):
    """
    Split SQL text into individual statements, respecting semicolons
    inside string literals.
    """
    stmts = []
    current = []
    in_string = None
    i = 0
    while i < len(text):
        ch = text[i]
        if in_string:
            current.append(ch)
            if ch == '\\' and i + 1 < len(text):
                i += 1
                current.append(text[i])
            elif ch == in_string:
                in_string = None
        elif ch in ("'", '"'):
            in_string = ch
            current.append(ch)
        elif ch == ';':
            stmt = ''.join(current).strip()
            if stmt:
                stmts.append(stmt)
            current = []
        else:
            current.append(ch)
        i += 1
    tail = ''.join(current).strip()
    if tail:
        stmts.append(tail)
    return stmts


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 apply_migration.py <sql_file> [<sql_file> ...]")
        sys.exit(1)

    cfg = Config('config.yaml')
    db_cfg = cfg.data
    password = cfg.secrets.get('db_password') or getattr(cfg, 'db_password', None)
    if not password:
        print("ERROR: Could not obtain DB password (check vault decryption)")
        sys.exit(1)

    conn = mysql.connector.connect(
        host=getattr(db_cfg, 'db_host', 'ksfraser.ca'),
        user=getattr(db_cfg, 'db_user', 'ksfraser_stockmarket'),
        password=password,
        database=getattr(db_cfg, 'db_name', 'ksfraser_stock_market'),
        port=int(getattr(db_cfg, 'port', 3306)),
        charset='utf8mb4',
        autocommit=False,
        connection_timeout=15,
    )
    cur = conn.cursor()

    for path in sys.argv[1:]:
        sql = open(path).read()
        stmts = split_sql(sql)
        for stmt in stmts:
            if not stmt or stmt.startswith('--'):
                continue
            try:
                cur.execute(stmt)
                print(f"  OK: {stmt[:70]}")
            except mysql.connector.Error as e:
                print(f"  WARN: {str(e)[:80]} | {stmt[:50]}")

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete.")


if __name__ == '__main__':
    main()
