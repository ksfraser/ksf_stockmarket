#!/usr/bin/env python3
"""
Shared DB target for seg-fund seeders.

Philosophy (per user direction): **MySQL is the primary target**; the local
SQLite cache is retained as a historical/offline *fallback* only.

`get_conn()` returns ``(conn, backend)``:
  * backend == 'mysql'  -> production MariaDB via ``python.db_connector``
  * backend == 'sqlite' -> local cache DB (only when MySQL is unreachable)

Seeder SQL is written in **sqlite style** (``?`` placeholders,
``datetime('now')``). `run()`/`runmany()` transparently rewrite it for the
active backend (``?`` -> ``%s`` and ``datetime('now')`` -> ``CURRENT_TIMESTAMP``
on MySQL) so the same seeder code works against both.

Usage in a seeder::

    import segfund_db
    conn, backend = segfund_db.get_conn()
    def q(sql, params=()):
        return segfund_db.run(conn, backend, sql, params)
    rows = q("SELECT fund_id FROM funds WHERE carrier_id=?", (9,)).fetchall()
    q("UPDATE fund_series SET yr_2024=? WHERE fund_id=?", (4.3, fid))
    conn.commit()
"""
from __future__ import annotations

import os
import sys
import sqlite3

LOCAL_DB = os.environ.get("SEG_FUNDS_DB", "/root/.hermes/cache/seg_funds.db")

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from python.db_connector import get_connection as _mysql_get_connection  # type: ignore
except Exception:  # pragma: no cover - mysql connector optional in some envs
    _mysql_get_connection = None


def get_conn():
    """Return (conn, backend). Prefers MySQL, falls back to local SQLite."""
    if _mysql_get_connection is not None:
        try:
            conn = _mysql_get_connection()
            return conn, "mysql"
        except Exception as exc:  # MySQL unreachable -> keep local as fallback
            sys.stderr.write(
                f"[segfund_db] MySQL unavailable ({exc}); falling back to "
                f"local SQLite at {LOCAL_DB}\n"
            )
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def adapt_sql(sql: str, backend: str) -> str:
    """Rewrite sqlite-style SQL for the target backend."""
    if backend == "mysql":
        sql = sql.replace("?", "%s")
        sql = sql.replace("datetime('now')", "CURRENT_TIMESTAMP")
    return sql


def run(conn, backend: str, sql: str, params=()):
    """Execute one statement; return the cursor."""
    cur = conn.cursor()
    cur.execute(adapt_sql(sql, backend), tuple(params))
    return cur


def runmany(conn, backend: str, sql: str, rows):
    """Execute a parameterized statement for many rows."""
    cur = conn.cursor()
    cur.executemany(adapt_sql(sql, backend), [tuple(r) for r in rows])
    return cur
