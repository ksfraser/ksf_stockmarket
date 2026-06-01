"""
tests/unit/test_db_adapter.py — Unit tests for the database adapter layer.

Tests run against SQLite (fast, no MySQL needed). The adapter interface
is the same for MySQL — integration tests cover that.
"""
import os
import pytest
import tempfile

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'python'))

from db.sqlite_adapter import SQLiteAdapter
from db.adapter import Database


@pytest.fixture
def db():
    """Create a temporary SQLite database for each test."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    adapter = SQLiteAdapter(db_path)
    # Create schema
    with adapter as conn:
        # Create test tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stockprices (
                symbol VARCHAR(20) NOT NULL,
                price_date DATE NOT NULL,
                close FLOAT,
                volume BIGINT,
                PRIMARY KEY (symbol, price_date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS symbol_master (
                symbol VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100),
                exchange VARCHAR(10),
                is_active TINYINT DEFAULT 1
            )
        """)

    yield Database(SQLiteAdapter(db_path))

    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def populated_db(db):
    """Database with sample data."""
    with db.connect() as conn:
        # Insert test data with %s placeholders (MySQL style — adapter converts)
        conn.executemany(
            "INSERT INTO symbol_master (symbol, name, exchange, is_active) VALUES (%s, %s, %s, %s)",
            [
                ('RY', 'Royal Bank', 'TSX', 1),
                ('CM', 'CIBC', 'TSX', 1),
                ('KEG.UN', 'Keg Royalties', None, 0),  # inactive
            ]
        )
        conn.executemany(
            "INSERT INTO stockprices (symbol, price_date, close, volume) VALUES (%s, %s, %s, %s)",
            [
                ('RY', '2026-06-01', 150.25, 1000000),
                ('RY', '2026-05-31', 149.80, 950000),
                ('CM', '2026-06-01', 65.40, 500000),
            ]
        )
    return db


class TestSQLiteAdapter:
    """Test the SQLite adapter."""

    def test_creates_db_file(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            db = Database(SQLiteAdapter(db_path))
            with db.connect() as conn:
                conn.execute("CREATE TABLE t (id INT)")
            assert os.path.exists(db_path)
        finally:
            os.unlink(db_path)

    def test_execute_insert(self, populated_db):
        with populated_db.connect() as conn:
            affected = conn.execute(
                "INSERT INTO symbol_master (symbol, name, exchange, is_active) VALUES (%s, %s, %s, %s)",
                ('TD', 'TD Bank', 'TSX', 1)
            )
            assert affected == 1

    def test_fetchone(self, populated_db):
        with populated_db.connect() as conn:
            row = conn.fetchone(
                "SELECT * FROM symbol_master WHERE symbol = %s", ('RY',)
            )
            assert row is not None
            assert row['symbol'] == 'RY'
            assert row['exchange'] == 'TSX'
            assert row['is_active'] == 1

    def test_fetchone_returns_none_for_missing(self, populated_db):
        with populated_db.connect() as conn:
            row = conn.fetchone(
                "SELECT * FROM symbol_master WHERE symbol = %s", ('ZZZZ',)
            )
            assert row is None

    def test_fetchall_active_symbols(self, populated_db):
        """Simulate what daily_pipeline.get_active_symbols() does."""
        with populated_db.connect() as conn:
            rows = conn.fetchall(
                "SELECT symbol, name, exchange FROM symbol_master WHERE is_active = 1 ORDER BY symbol"
            )
            assert len(rows) == 2  # RY and CM, KEG.UN is inactive
            symbols = [r['symbol'] for r in rows]
            assert 'KEG.UN' not in symbols

    def test_fetchall(self, populated_db):
        with populated_db.connect() as conn:
            rows = conn.fetchall("SELECT * FROM stockprices ORDER BY symbol, price_date")
            assert len(rows) == 3

    def test_executemany_batch_insert(self, db):
        with db.connect() as conn:
            conn.execute("""
                CREATE TABLE prices (symbol VARCHAR(10), price_date DATE, close FLOAT)
            """)
            data = [
                ('A', '2026-01-01', 100.0),
                ('A', '2026-01-02', 101.0),
                ('A', '2026-01-03', 99.5),
                ('B', '2026-01-01', 50.0),
            ]
            affected = conn.executemany(
                "INSERT INTO prices (symbol, price_date, close) VALUES (%s, %s, %s)",
                data
            )
            assert affected == 4

    def test_placeholder_conversion(self, db):
        """Test that %s placeholders are converted to ? for SQLite."""
        with db.connect() as conn:
            conn.execute("CREATE TABLE t (a VARCHAR(10), b INT)")
            conn.execute("INSERT INTO t (a, b) VALUES (%s, %s)", ('hello', 42))
            row = conn.fetchone("SELECT * FROM t WHERE a = %s AND b = %s", ('hello', 42))
            assert row['a'] == 'hello'
            assert row['b'] == 42


class TestDatabaseFactory:
    """Test Database.from_config() factory."""

    def test_from_config_sqlite(self, tmp_path):
        import yaml
        config = {'database': {'engine': 'sqlite', 'path': str(tmp_path / 'test.db')}}
        config_file = tmp_path / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        db = Database.from_config(str(config_file))
        assert isinstance(db._adapter, SQLiteAdapter)

    def test_from_config_invalid_engine(self, tmp_path):
        import yaml
        config = {'database': {'engine': 'oracle'}}
        config_file = tmp_path / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with pytest.raises(ValueError, match="Unknown database engine"):
            Database.from_config(str(config_file))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
