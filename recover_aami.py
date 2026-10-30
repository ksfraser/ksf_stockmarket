#!/usr/bin/env python3
"""
recover_aami.py — Recover AAMI 2026-09-09 from indicators_json id=5256469.

The buggy migration run scrambled AAMI's indicators row (parameter ordering
was wrong: values list had field values first, but SQL expected symbol+date
first, shifting all parameters). 

This script:
1. Reads the JSON from indicators_json (still intact).
2. Parses it into the DTO.
3. Drops the 180 bogus 'set_*' columns (from the even-earlier buggy run).
4. Re-upsert AAMI 2026-09-09 with CORRECT parameter ordering.
5. Re-reads and confirms DTO == DB.
6. Deletes the JSON row.
"""
from __future__ import annotations

import sys, os, json, argparse
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

import yaml
import pymysql

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, 'config.yaml')
if not os.path.exists(CONFIG_PATH):
    raise SystemExit(f"config.yaml not found at {CONFIG_PATH}")
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)
data_cfg = cfg.get('data', {})

DB_HOST = data_cfg.get('db_host', 'ksfraser.ca')
DB_PORT = int(data_cfg.get('db_port', 3306))
DB_NAME = os.environ.get('DB_NAME') or data_cfg.get('db_name', 'ksfraser_stock_market')
DB_USER = os.environ.get('DB_USER') or data_cfg.get('db_user', 'ksfraser_stockmarket')
DB_PASS = os.environ.get('DB_PASS') or data_cfg.get('db_password', '')
if not DB_PASS:
    raise SystemExit("No DB password found.")

TOLERANCE = Decimal('0.0001')


def connect():
    print("Connecting to MySQL ...", flush=True)
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME,
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
        autocommit=False, connect_timeout=10,
    )
    print("Connected.", flush=True)
    return conn


def coerce(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return round(float(v), 4)
    if isinstance(v, Decimal):
        return v.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    if isinstance(v, str):
        try:
            return Decimal(v).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        except Exception:
            return None
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Show steps without executing ALTER/INSERT/DELETE')
    parser.add_argument('--keep-set-cols', action='store_true',
                        help='Do NOT drop the bogus set_* columns')
    args = parser.parse_args()

    conn = connect()
    try:
        cur = conn.cursor()

        # 1. Fetch the JSON
        cur.execute("SELECT id, symbol, price_date, data FROM indicators_json WHERE id=5256469")
        json_row = cur.fetchone()
        if not json_row:
            print("[ERROR] JSON row 5256469 not found — cannot recover")
            return
        row_id = json_row['id']
        sym = json_row['symbol']
        jdate = json_row['price_date']
        data = json.loads(json_row['data'])
        print(f"\nJSON row: id={row_id} sym={sym} date={jdate} keys={len(data)}")

        # 2. Filter to only indicator values (exclude structural + non-numeric)
        indicator_data = {}
        for k, v in data.items():
            if k in ('symbol', 'price_date'):
                continue
            c = coerce(v)
            if c is not None:
                indicator_data[k] = c
        print(f"Indicator values to write: {len(indicator_data)}")

        # 3. Drop the 180 bogus 'set_*' columns (unless --keep-set-cols)
        if not args.keep_set_cols:
            print(f"\n--- Dropping bogus set_* columns ---")
            cur.execute("SHOW COLUMNS FROM indicators")
            all_cols = [r['Field'] for r in cur.fetchall()]
            set_cols = [c for c in all_cols if c.startswith('set_')]
            print(f"  Found {len(set_cols)} set_* columns to drop")
            if not args.dry_run:
                for c in set_cols:
                    try:
                        cur.execute(f"ALTER TABLE indicators DROP COLUMN `{c}`")
                        print(f"    DROPPED: {c}")
                    except Exception as e:
                        print(f"    ERROR dropping {c}: {e}")
            else:
                print(f"  (dry_run=True: not executing)")
                for c in set_cols[:10]:
                    print(f"    WOULD DROP: {c}")
                if len(set_cols) > 10:
                    print(f"    ... and {len(set_cols)-10} more")
        else:
            print(f"\n  --keep-set-cols: keeping {180} set_* columns")

        # 4. Build upsert — CORRECT parameter ordering
        # INSERT INTO indicators (symbol, price_date, col1, col2, ...)
        # VALUES (%s, %s, %s, %s, ...)
        # ON DUPLICATE KEY UPDATE col1=VALUES(col1), col2=VALUES(col2), ...
        sorted_cols = sorted(indicator_data.keys())
        col_list = ', '.join(f'`{c}`' for c in sorted_cols)
        placeholders = ', '.join(['%s'] * (len(sorted_cols) + 2))  # sym + date + fields
        update_clause = ', '.join(f'`{c}` = VALUES(`{c}`)' for c in sorted_cols)

        upsert_sql = (
            f"INSERT INTO indicators (symbol, price_date, {col_list}) "
            f"VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {update_clause}"
        )

        values = [sym, jdate]
        for c in sorted_cols:
            values.append(coerce(indicator_data[c]))

        print(f"\n--- Upserting {len(sorted_cols)} fields for {sym} {jdate} ---")
        for i, c in enumerate(sorted_cols):
            print(f"  [{i+3:3d}] {c:35s} = {values[i+2]!r}")

        if not args.dry_run:
            try:
                cur.execute(upsert_sql, values)
                print(f"\n  -> Executed (rows affected: {cur.rowcount})")
            except Exception as e:
                print(f"\n  [ERROR] Upsert failed: {e}")
                conn.rollback()
                return
        else:
            print(f"\n  (dry_run=True: not executing)")
            print(f"  SQL: {upsert_sql[:200]}...")

        # 5. Re-read and confirm
        print(f"\n--- Value comparison: DTO vs DB (after upsert) ---")
        if not args.dry_run:
            cur.execute(
                "SELECT * FROM indicators WHERE symbol = %s AND price_date = %s",
                (sym, jdate),
            )
            db_row = cur.fetchone()
        else:
            db_row = None

        if db_row:
            checked = 0
            mismatches = 0
            for col in sorted_cols:
                checked += 1
                dto_v = indicator_data[col]
                db_v = db_row.get(col)
                if db_v is None:
                    mismatches += 1
                    print(f"  {col:35s} DTO={dto_v!r:15s} DB=NULL  MISMATCH")
                else:
                    diff = abs(Decimal(str(dto_v)) - Decimal(str(db_v)))
                    if diff > TOLERANCE:
                        mismatches += 1
                        print(f"  {col:35s} DTO={dto_v!r:15s} DB={db_v!r:15s} diff={diff} MISMATCH")
            print(f"  Checked {checked} fields, {mismatches} mismatches > {TOLERANCE}")
        else:
            print(f"  [WARN] Row not found after upsert (dry run)")

        # 6. Delete JSON row
        print(f"\n--- Deleting indicators_json id={row_id} ---")
        if not args.dry_run:
            cur.execute("DELETE FROM indicators_json WHERE id = %s", (row_id,))
            print(f"  -> Deleted (rows affected: {cur.rowcount})")
        else:
            print(f"  (dry_run=True: not deleting)")

    finally:
        conn.commit()
        conn.close()

    print(f"\n{'='*70}")
    print(f"RECOVERY COMPLETE")
    print(f"JSON row 5256469: {'DELETED' if not args.dry_run else 'KEPT (dry run)'}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
