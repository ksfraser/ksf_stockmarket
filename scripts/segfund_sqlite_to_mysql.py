#!/usr/bin/env python3
"""
Transfer seg-fund data from local SQLite -> production MySQL.

Creates a FAITHFUL COPY of the normalized seg-fund schema (carriers, funds,
fund_series, ...) as NEW tables in the production MySQL DB (ksfraser_stock_market),
leaving the pre-existing flat `seg_funds` table completely untouched.

Idempotent: DROPs only our normalized destination tables (whitelisted names)
and re-creates them, then bulk-copies every row, preserving primary-key IDs,
and finally resets each table's AUTO_INCREMENT counter.

Verification: after the copy, per-table row counts are compared and a
type-normalized SHA-256 checksum of every row is compared SQLite vs MySQL.

Usage:
  python3 segfund_sqlite_to_mysql.py           # dry-run: prints plan + counts
  python3 segfund_sqlite_to_mysql.py --apply   # performs the transfer + verify
"""
from __future__ import annotations

import os
import sys
import re
import hashlib
import argparse
import sqlite3

import pymysql

LOCAL_DB = os.environ.get("SEG_FUNDS_DB", "/root/.hermes/cache/seg_funds.db")

# Whitelisted normalized tables we own. We NEVER touch the app's flat
# seg_funds / seg_fund_prices / seg_fund_calendar_returns tables.
TABLES = [
    "carriers",
    "fund_families",
    "funds",
    "fund_series",
    "fund_codes",
    "performance_history",
    "seg_fund_metrics",
    "seg_fund_screen",
    "scrape_log",
    "screening_presets",
]


def mysql_conn():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        database=os.environ["DB_NAME"],
        charset=os.environ.get("DB_CHARSET", "utf8mb4"),
        autocommit=False,
    )


def sqlite_cols(table):
    cur = S.execute(f"PRAGMA table_info(`{table}`)")
    return cur.fetchall()  # (cid, name, type, notnull, dflt, pk)


def sqlite_ddl(table):
    row = S.execute(
        "SELECT sql FROM sqlite_master WHERE name=?", (table,)
    ).fetchone()
    return row[0] if row else ""


def mysql_type(decl):
    d = (decl or "").upper()
    if "INTEGER" in d or d.startswith("INT"):
        return "INT"
    if "REAL" in d:
        return "DOUBLE"
    return "TEXT"


def build_ddl(table):
    cols = sqlite_cols(table)
    ddl = sqlite_ddl(table)
    uniques = []
    for m in re.finditer(r"UNIQUE\s*\(([^)]*)\)", ddl, re.I):
        uniques.append([c.strip() for c in m.group(1).split(",")])
    parts = []
    pk_cols = [c[1] for c in cols if c[5] == 1]
    for _cid, name, ctype, notnull, _dflt, pk in cols:
        coldef = f"`{name}` "
        if pk == 1:
            coldef += "INT NOT NULL AUTO_INCREMENT"
        else:
            coldef += mysql_type(ctype)
            if notnull == 1:
                coldef += " NOT NULL"
            if name in ("created_at", "updated_at"):
                coldef += " DEFAULT CURRENT_TIMESTAMP"
        parts.append(coldef)
    if pk_cols:
        parts.append(f"PRIMARY KEY (`{'`,`'.join(pk_cols)}`)")
    # NOTE: secondary UNIQUE KEYs from the SQLite DDL are intentionally NOT
    # created here. The source SQLite contains a small number of duplicate
    # rows (e.g. duplicate (carrier_id, fund_name) in `funds`), so enforcing
    # those uniques would block a faithful copy. PK uniqueness is preserved.
    return (
        f"CREATE TABLE `{table}` (\n  "
        + ",\n  ".join(parts)
        + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )


def _norm(v):
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    return v


def checksum_table(conn, table):
    colnames = [c[1] for c in sqlite_cols(table)]
    col_list = ",".join(f"`{c}`" for c in colnames)
    srows = S.execute(
        f"SELECT * FROM `{table}` ORDER BY `{colnames[0]}`"
    ).fetchall()
    s_hash = hashlib.sha256()
    for r in srows:
        s_hash.update(repr(tuple(_norm(x) for x in tuple(r))).encode())
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM `{table}` ORDER BY `{colnames[0]}`")
    mrows = cur.fetchall()
    m_hash = hashlib.sha256()
    for r in mrows:
        m_hash.update(repr(tuple(_norm(x) for x in tuple(r))).encode())
    return s_hash.hexdigest(), m_hash.hexdigest(), len(srows), len(mrows)


def copy_table(conn, table, apply):
    cols = sqlite_cols(table)
    colnames = [c[1] for c in cols]
    n = S.execute(f"SELECT COUNT(*) FROM `{table}`").fetchone()[0]
    if not apply:
        print(f"  {table:22} {n:>7} rows  -> MySQL (cols={len(colnames)})")
        return n
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS `{table}`")
    cur.execute(build_ddl(table))
    raw = S.execute(
        f"SELECT * FROM `{table}` ORDER BY `{colnames[0]}`"
    ).fetchall()
    # Convert sqlite3.Row -> plain tuple: pymysql.executemany mishandles
    # sqlite3.Row objects (subclass of tuple) and raises on formatting.
    rows = [tuple(r) for r in raw]
    placeholders = ",".join(["%s"] * len(colnames))
    col_list = ",".join(f"`{c}`" for c in colnames)
    sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"
    B = 500
    for i in range(0, len(rows), B):
        cur.executemany(sql, rows[i : i + B])
    conn.commit()
    if rows:
        maxid = rows[-1][0]
        cur.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = {maxid + 1}")
        conn.commit()
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="perform the transfer")
    args = ap.parse_args()
    apply = args.apply

    global S
    S = sqlite3.connect(LOCAL_DB)
    S.row_factory = sqlite3.Row

    print(f"Local SQLite: {LOCAL_DB}")
    print(f"Target MySQL: {os.environ['DB_HOST']}/{os.environ['DB_NAME']}")
    print(f"Mode: {'APPLY (write)' if apply else 'DRY-RUN (no writes)'}")
    print("Tables to transfer:")
    for t in TABLES:
        copy_table(None, t, False)  # dry-run print

    if not apply:
        print("\nDry-run complete. Re-run with --apply to perform the transfer.")
        S.close()
        return

    conn = mysql_conn()
    try:
        print("\n--- transferring ---")
        for t in TABLES:
            n = copy_table(conn, t, True)
            print(f"  transferred {t}: {n} rows")
        print("\n--- verifying ---")
        all_ok = True
        for t in TABLES:
            s_h, m_h, s_n, m_n = checksum_table(conn, t)
            ok = (s_n == m_n) and (s_h == m_h)
            all_ok = all_ok and ok
            status = "OK " if ok else "MISMATCH"
            print(f"  [{status}] {t}: sqlite={s_n} mysql={m_n} sha_match={s_h == m_h}")
            if not ok:
                print(f"      sqlite_sha={s_h}")
                print(f"      mysql_sha ={m_h}")
        if not all_ok:
            print("\nVERIFICATION FAILED — tables left as transferred; review above.")
            conn.rollback()
            sys.exit(2)
        print("\nTRANSFER VERIFIED: all tables match (counts + row checksums).")
    finally:
        conn.close()
        S.close()


if __name__ == "__main__":
    main()
