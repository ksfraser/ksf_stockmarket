"""
db_connector.py — Shared database connection module.

All Python modules (Flask API, TA calculator, scoring engine, etc.)
import from this module to get database connections.

Supports both MariaDB (production) and SQLite (dev/test).
Set DB_BACKEND=sqlite to force SQLite, or DB_BACKEND=mysql for MariaDB.
When MySQL is not available, automatically falls back to SQLite.

Usage:
    from python.db_connector import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    ...
"""

import os
import logging

logger = logging.getLogger(__name__)

DB_CONFIG = {}


def _init_config():
    """Detect and initialize the database backend."""
    global DB_CONFIG
    # Always re-read environment — tests may change env vars at runtime
    backend = os.environ.get('DB_BACKEND', 'auto').lower()

    if backend == 'sqlite':
        _init_sqlite()
    elif backend == 'mysql' or backend == 'mariadb':
        _init_mysql()
    else:
        # auto-detect: try MySQL first, fall back to SQLite
        try:
            _init_mysql()
            conn = _connect_mysql()
            conn.close()
            logger.info("DB backend: MariaDB/MySQL")
        except Exception as e:
            logger.info(f"MySQL not available ({e}), falling back to SQLite")
            _init_sqlite()


def _init_sqlite():
    """Configure SQLite backend."""
    global DB_CONFIG
    DB_CONFIG = {
        'backend': 'sqlite',
        'path': os.environ.get('SQLITE_PATH',
                  os.path.join(os.path.dirname(__file__), '..', 'data', 'ksf_stockmarket.db')),
    }
    os.makedirs(os.path.dirname(DB_CONFIG['path']), exist_ok=True)


def _init_mysql():
    """Configure MariaDB/MySQL backend."""
    global DB_CONFIG
    DB_CONFIG = {
        'backend': 'mysql',
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'ksf_stockmarket'),
        'password': os.environ.get('DB_PASS', 'change_me'),
        'database': os.environ.get('DB_NAME', 'ksf_stockmarket'),
        'charset': 'utf8mb4',
        'use_unicode': True,
        'autocommit': False,
        'pool_name': 'ksf_pool',
        'pool_size': 5,
    }


def _connect_mysql():
    """Create a MySQL connection."""
    import mysql.connector
    try:
        conn = mysql.connector.connect(**{k: v for k, v in DB_CONFIG.items()
                                          if k not in ('backend',)})
        return conn
    except Exception as e:
        raise RuntimeError(f'MariaDB connection failed: {e}') from e


class _SQLiteCompatConnection:
    """Wraps sqlite3.Connection to support cursor(dictionary=True)."""

    def __init__(self, sqlite_conn):
        object.__setattr__(self, '_conn', sqlite_conn)

    def cursor(self, *args, **kwargs):
        kwargs.pop('dictionary', None)
        real_cursor = self._conn.cursor(*args, **kwargs)
        return _SQLiteCompatCursor(real_cursor)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        if name == '_conn':
            object.__setattr__(self, name, value)
        else:
            setattr(self._conn, name, value)


class _SQLiteCompatCursor:
    """Wraps sqlite3.Cursor to translate %s → ? placeholders."""

    def __init__(self, real_cursor):
        object.__setattr__(self, '_cursor', real_cursor)

    def execute(self, sql, parameters=None):
        if isinstance(sql, str):
            sql = sql.replace('%s', '?')
        return self._cursor.execute(sql, parameters)

    def executemany(self, sql, parameters=None):
        if isinstance(sql, str):
            sql = sql.replace('%s', '?')
        return self._cursor.executemany(sql, parameters)

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def __setattr__(self, name, value):
        if name == '_cursor':
            object.__setattr__(self, name, value)
        else:
            setattr(self._cursor, name, value)

    def __iter__(self):
        return iter(self._cursor)


def get_connection():
    """Get a database connection (auto-detects backend)."""
    # Re-check env each time — tests may change DB_BACKEND/SQLITE_PATH
    if DB_CONFIG.get('backend') == 'sqlite' or os.environ.get('DB_BACKEND', '').lower() == 'sqlite':
        _init_config()
    elif not DB_CONFIG:
        _init_config()

    if DB_CONFIG.get('backend') == 'mysql':
        return _connect_mysql()
    else:
        # SQLite — return a wrapped connection
        import sqlite3
        path = DB_CONFIG['path']
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return _SQLiteCompatConnection(conn)


def get_dict_cursor(conn):
    """Get a cursor that returns dict-like rows (MySQL or SQLite)."""
    # If conn is our wrapper, it already handles dictionary=True
    # If conn is raw SQLite, ensure row_factory is set
    real_conn = conn._conn if isinstance(conn, _SQLiteCompatConnection) else conn
    if hasattr(real_conn, 'row_factory') and real_conn.row_factory is None:
        import sqlite3
        real_conn.row_factory = sqlite3.Row
    return conn.cursor()


def get_active_symbols(conn=None) -> list:
    """Get list of active symbols that have recent price data."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT symbol FROM stockprices
            WHERE price_date >= DATE('now', '-5 days')
            ORDER BY symbol
        """)
        symbols = [row[0] for row in cursor.fetchall()]
    except Exception:
        try:
            cursor.execute("SELECT DISTINCT symbol FROM stockprices ORDER BY symbol")
            symbols = [row[0] for row in cursor.fetchall()]
        except Exception:
            symbols = []

    if own_conn:
        conn.close()
    return symbols


def fetch_price_data(conn, symbol: str, lookback: int = 250):
    """Fetch OHLCV data for a symbol as a pandas DataFrame."""
    import pandas as pd

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT price_date, day_open, day_high, day_low, day_close, volume
            FROM stockprices WHERE symbol = ?
            ORDER BY price_date DESC LIMIT ?
        """, (symbol, lookback))
        rows = list(reversed(cursor.fetchall()))
    except Exception:
        rows = []

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=['price_date', 'day_open', 'day_high', 'day_low', 'day_close', 'volume'])
    df['price_date'] = pd.to_datetime(df['price_date'])
    df.set_index('price_date', inplace=True)
    for col in ['day_open', 'day_high', 'day_low', 'day_close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


# Initialize on import
_init_config()
