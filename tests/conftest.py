"""
tests/conftest.py — Shared pytest fixtures.

Tests use the production database tables directly (with cleanup of seeded
test rows). A table_prefix parameter in advisor config is supported for
future prefixed deployments but defaults to empty string (prod tables).
"""
from __future__ import annotations

import sys
import os

import pymysql
import pymysql.cursors

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python', 'src'))

from config_provider import get_provider  # type: ignore

PROVIDER = get_provider()
_DB_CONFIG = PROVIDER.get_db_config()
_DB_CONFIG['cursorclass'] = pymysql.cursors.DictCursor

# Symbols used by advisor unit tests; cleaned up after each test.
_TEST_SYMBOLS = ('AAPL', 'MSFT', 'RY', 'BAD')


def _get_test_conn() -> pymysql.connections.Connection:
    return pymysql.connect(**_DB_CONFIG)


def get_test_db() -> pymysql.connections.Connection:
    return _get_test_conn()


def cleanup_test_db() -> None:
    """No-op kept for backward compatibility."""
    pass


def cleanup_test_data(db: pymysql.connections.Connection) -> None:
    """Remove seeded rows for advisor test symbols from production tables."""
    with db.cursor() as cur:
        for table in ('fundamentals', 'stockprices', 'dividends'):
            try:
                cur.execute(
                    f"DELETE FROM {table} WHERE symbol IN %s",
                    (_TEST_SYMBOLS,),
                )
            except Exception as exc:
                print(f"cleanup_test_data failed on {table}: {exc}")
    db.commit()


# Backward-compat path used by some older GA/NN tests.
TEST_DB_PATH = None


def setup_test_database() -> None:
    """Legacy compatibility: no-op for tests now using production tables."""
    pass


def seed_test_prices(db, symbol: str = 'TEST', days: int = 300, base_price: float = 100.0):
    """Legacy compatibility: seed directly into production stockprices with a unique symbol."""
    import datetime as _dt
    base_date = _dt.date(2025, 1, 1)
    rows = []
    for i in range(days):
        d = base_date + _dt.timedelta(days=i)
        rows.append((
            symbol, str(d), base_price, base_price + 1, base_price - 1, base_price + 0.5, 1_000_000
        ))
    with db.cursor() as cur:
        cur.executemany(
            "REPLACE INTO stockprices (symbol, price_date, open, high, low, close, volume) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
    db.commit()


def seed_test_indicators(db, symbol: str = 'TEST'):
    raise NotImplementedError(
        "Legacy seed_test_indicators removed; advisors package no longer uses indicators table directly."
    )


def seed_test_evalsummary(db):
    raise NotImplementedError(
        "Legacy seed_test_evalsummary removed; use production data or rewrite tests for MariaDB."
    )


def seed_test_signal_weights(db):
    raise NotImplementedError(
        "Legacy seed_test_signal_weights removed; use production data or rewrite tests for MariaDB."
    )
