"""
db_connector.py — Shared database connection module.

All Python modules (Flask API, TA calculator, scoring engine, etc.)
import from this module to get MariaDB connections.

Usage:
    from python.db_connector import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    ...
"""

import os
import mysql.connector
from mysql.connector import Error as MySQLError

DB_CONFIG = {
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


def get_connection():
    """Get a MariaDB connection from the pool."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except MySQLError as e:
        raise RuntimeError(f'Database connection failed: {e}') from e


def get_active_symbols(conn=None) -> list:
    """Get list of active symbols that have recent price data."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT symbol FROM stockprices
        WHERE price_date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
        ORDER BY symbol
    """)
    symbols = [row[0] for row in cursor.fetchall()]
    cursor.close()

    if own_conn:
        conn.close()

    return symbols


def fetch_price_data(conn, symbol: str, lookback: int = 250):
    """
    Fetch OHLCV data for a symbol as a pandas DataFrame.
    Returns DataFrame with columns: day_open, day_high, day_low, day_close, volume
    indexed by price_date.
    """
    import pandas as pd

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT price_date, day_open, day_high, day_low, day_close, volume
        FROM stockprices
        WHERE symbol = %s
          AND price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY price_date ASC
    """, (symbol, lookback))

    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df['price_date'] = pd.to_datetime(df['price_date'])
    df.set_index('price_date', inplace=True)
    for col in ['day_open', 'day_high', 'day_low', 'day_close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df
