"""
db/sqlite_adapter.py — SQLite adapter for local testing (DEPRECATED)

Note: MariaDB is now the primary database. For MariaDB connections, use:
  python/src/database.py or python/db/mysql_adapter.py

This file is kept for potential local testing scenarios but should not be used
in production. Always use MariaDB backend (ksfraser_stock_market) for live data.
"""
import sqlite3
import re
from typing import Any, Dict, List, Optional
from db.adapter import DBConnection


class SQLiteConnection(DBConnection):
    """SQLite adapter — for testing and local dev only. MariaDB preferred."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = None

    def _ensure_open(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")

    def _convert_sql(self, sql: str) -> str:
        """Convert %s placeholders to ? for SQLite."""
        return re.sub(r'%s', '?', sql)

    def _row_to_dict(self, row) -> Optional[Dict]:
        if row is None:
            return None
        return dict(row)

    def execute(self, sql: str, params: Optional[tuple] = None) -> int:
        self._ensure_open()
        sql = self._convert_sql(sql)
        cur = self._conn.execute(sql, params or ())
        self._conn.commit()
        return cur.rowcount

    def fetchone(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict]:
        self._ensure_open()
        sql = self._convert_sql(sql)
        cur = self._conn.execute(sql, params or ())
        return self._row_to_dict(cur.fetchone())

    def fetchall(self, sql: str, params: Optional[tuple] = None) -> List[Dict]:
        self._ensure_open()
        sql = self._convert_sql(sql)
        cur = self._conn.execute(sql, params or ())
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def executemany(self, sql: str, params_list: List[tuple]) -> int:
        self._ensure_open()
        sql = self._convert_sql(sql)
        cur = self._conn.executemany(sql, params_list)
        self._conn.commit()
        return cur.rowcount

    def commit(self) -> None:
        if self._conn:
            self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None  # Allow reconnect

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            if self._conn:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
        self.close()
        return False


# Short alias
SQLiteAdapter = SQLiteConnection