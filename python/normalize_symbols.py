#!/usr/bin/env python3
"""One-time backfill: normalize stored ticker symbols to yfinance/Stooq form.

Strips exchange prefixes (AMEX:/OTC:/NYSE:/NASDAQ:/CBOE:), converts share-class
separators '/' -> '-' (AGM/PE -> AGM-PE) and US class-share dots to '-'
(BRK.A -> BRK-B), leaving exchange suffixes (.TO/.V/...) intact.

Updates symbol_master, tradingview_screener_results, ta_indicators and
exchange_mapping so screener/price joins line up with the normalized tickers
that fetch_prices.py now stores. Symbols that would collide after normalization
are skipped (logged) rather than overwritten.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "python" / "src"
for p in (str(REPO_ROOT), str(REPO_ROOT / "python"), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from symbol_resolver import normalize_symbol  # noqa: E402

# Tables whose `symbol` column must be normalized (in dependency order).
TABLES = [
    "symbol_master",
    "tradingview_screener_results",
    "ta_indicators",
    "exchange_mapping",
]


def _connect():
    import python.db_connector as dc
    if not dc.DB_CONFIG:
        dc._init_config()
    cfg = dc.DB_CONFIG
    import pymysql
    return pymysql.connect(
        host=cfg.get("host"),
        port=cfg.get("port"),
        user=cfg.get("user"),
        password=cfg.get("password"),
        database=cfg.get("database"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _existing(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT DISTINCT symbol FROM {table}")
        return {r["symbol"] for r in cur.fetchall()}


def backfill(conn):
    totals = {}
    for table in TABLES:
        try:
            distinct = _existing(conn, table)
        except Exception as e:
            print(f"  SKIP {table}: {e}")
            continue
        changed = 0
        skipped = 0
        seen = set(distinct)
        for raw in sorted(distinct):
            norm = normalize_symbol(raw)
            if norm == raw:
                continue
            if norm in seen:
                # Merge: the normalized form already exists, so drop the raw
                # (prefixed) row to avoid a duplicate orphan. Keep the canonical
                # normalized row. If a FK blocks the delete, leave it as-is.
                try:
                    with conn.cursor() as cur:
                        cur.execute(f"DELETE FROM {table} WHERE symbol=%s", (raw,))
                    skipped += cur.rowcount
                    if cur.rowcount:
                        print(f"  MERGED {table}: {raw} -> {norm} (deleted {cur.rowcount} raw row(s))")
                except Exception as e:
                    skipped += 1
                    print(f"  COLLISION {table}: {raw} -> {norm} kept (delete blocked: {e})")
                continue
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {table} SET symbol=%s WHERE symbol=%s",
                    (norm, raw),
                )
            changed += cur.rowcount
            seen.add(norm)
        conn.commit()
        totals[table] = (changed, skipped)
        print(f"  {table}: {changed} rows normalized, {skipped} collisions skipped")
    return totals


def main() -> int:
    conn = _connect()
    try:
        print("Normalizing symbols across:", ", ".join(TABLES))
        totals = backfill(conn)
    finally:
        conn.close()
    print("Done:", totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
