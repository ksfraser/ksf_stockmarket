"""
db/mysql_adapter.py — MySQL/MariaDB adapter using pymysql.

Usage:
    adapter = MySQLConnection(host='ksfraser.ca', user='test', password='secret', database='test')
    with adapter as conn:
        row = conn.fetchone("SELECT * FROM symbol_master WHERE is_active = 1 LIMIT 1")
        print(row['symbol'])
"""
import pymysql
import pymysql.cursors
from typing import Any, Dict, List, Optional
from db.adapter import DBConnection

MYSQL_DEFAULTS = dict(
    host='localhost',
    user='',
    password='',
    database='',
    port=3306,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False,
)


class MySQLConnection(DBConnection):
    """MySQL adapter — production database (ksfraser.ca)."""

    def __init__(self, **kwargs):
        config = {**MYSQL_DEFAULTS, **kwargs}
        self._config = config
        self._conn = None

    def _ensure_open(self):
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(**self._config)

    def execute(self, sql: str, params: Optional[tuple] = None) -> int:
        self._ensure_open()
        with self._conn.cursor() as cur:
            affected = cur.execute(sql, params or ())
        self._conn.commit()
        return affected

    def fetchone(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict]:
        self._ensure_open()
        with self._conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()

    def fetchall(self, sql: str, params: Optional[tuple] = None) -> List[Dict]:
        self._ensure_open()
        with self._conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    def executemany(self, sql: str, params_list: List[tuple]) -> int:
        self._ensure_open()
        with self._conn.cursor() as cur:
            total = cur.executemany(sql, params_list)
        self._conn.commit()
        return total

    def commit(self) -> None:
        if self._conn and self._conn.open:
            self._conn.commit()

    def close(self) -> None:
        if self._conn and self._conn.open:
            self._conn.close()

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            if self._conn and self._conn.open:
                self._conn.rollback()
        self.close()
        return False


# Short alias
MySQLAdapter = MySQLConnection
