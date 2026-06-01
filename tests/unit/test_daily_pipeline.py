"""
tests/unit/test_daily_pipeline.py — Unit tests for the refactored daily_pipeline.py.

Uses SQLite adapter so tests run fast without MySQL.
"""
import os
import sys
import pytest
import tempfile
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'python'))

from db.sqlite_adapter import SQLiteAdapter
from db.adapter import Database
from daily_pipeline import DailyPriceDownloader, IndicatorCalculator


@pytest.fixture
def db():
    """Create a temporary SQLite database with schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    adapter = SQLiteAdapter(db_path)
    with adapter as conn:
        # Create test tables (mimicking the real schema)
        conn.execute("""
            CREATE TABLE symbol_master (
                symbol VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100),
                exchange VARCHAR(10),
                is_active TINYINT DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE stockprices (
                symbol VARCHAR(20) NOT NULL,
                price_date DATE NOT NULL,
                open FLOAT,
                high FLOAT,
                low FLOAT,
                close FLOAT,
                volume BIGINT,
                PRIMARY KEY (symbol, price_date)
            )
        """)
        conn.execute("""
            CREATE TABLE indicators_json (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol VARCHAR(20) NOT NULL,
                price_date DATE NOT NULL,
                sma_20 FLOAT,
                sma_50 FLOAT,
                sma_200 FLOAT,
                rsi_14 FLOAT,
                macd FLOAT,
                macd_signal FLOAT,
                macd_hist FLOAT,
                UNIQUE(symbol, price_date)
            )
        """)

    yield Database(SQLiteAdapter(db_path))
    os.unlink(db_path)


@pytest.fixture
def populated_db(db):
    """Database with sample symbols and price data."""
    with db.connect() as conn:
        conn.executemany(
            "INSERT INTO symbol_master (symbol, name, exchange, is_active) VALUES (%s, %s, %s, %s)",
            [
                ('RY', 'Royal Bank', 'TSX', 1),
                ('CM', 'CIBC', 'TSX', 1),
                ('KEG.UN', 'Keg Royalties', None, 0),  # inactive
            ]
        )
        # Generate 260 days of price data for RY
        base_date = datetime.date(2025, 6, 1)
        rows = []
        for i in range(260):
            d = base_date + datetime.timedelta(days=i)
            price = 150.0 + i * 0.1 + (i % 7) * 0.5
            rows.append((
                'RY', str(d),
                price - 0.5, price + 1.0, price - 1.0, price,
                1000000 + i * 1000
            ))
        conn.executemany(
            "INSERT INTO stockprices (symbol, price_date, open, high, low, close, volume) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            rows
        )
        # 100 days for CM
        for i in range(100):
            d = base_date + datetime.timedelta(days=i)
            price = 65.0 + i * 0.05
            rows.append(('CM', str(d), price - 0.3, price + 0.5, price - 0.5, price, 500000))
        conn.executemany(
            "INSERT INTO stockprices (symbol, price_date, open, high, low, close, volume) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            rows[260:]
        )
    return db


class TestDailyPriceDownloader:
    """Test the refactored DailyPriceDownloader (uses DB adapter)."""

    def test_get_active_symbols_excludes_inactive(self, populated_db):
        """Active symbols should exclude inactive ones."""
        downloader = DailyPriceDownloader(populated_db)
        symbols = downloader.get_active_symbols()
        symbol_names = [s['symbol'] for s in symbols]
        assert 'RY' in symbol_names
        assert 'CM' in symbol_names
        assert 'KEG.UN' not in symbol_names  # inactive

    def test_get_active_symbols_count(self, populated_db):
        downloader = DailyPriceDownloader(populated_db)
        symbols = downloader.get_active_symbols()
        assert len(symbols) == 2

    def test_get_latest_date(self, populated_db):
        downloader = DailyPriceDownloader(populated_db)
        latest = downloader.get_latest_date('RY')
        assert latest is not None
        # Should be ~259 days after 2025-06-01

    def test_get_latest_date_nonexistent(self, populated_db):
        downloader = DailyPriceDownloader(populated_db)
        latest = downloader.get_latest_date('ZZZZ')
        assert latest is None


class TestIndicatorCalculator:
    """Test the refactored IndicatorCalculator."""

    def test_get_symbols_needing_indicators(self, populated_db):
        calc = IndicatorCalculator(populated_db)
        symbols = calc.get_symbols_needing_indicators(lookback_days=365)
        # Should find RY and CM (have prices but no indicators)
        assert 'RY' in symbols
        assert 'CM' in symbols
        # KEG.UN should NOT appear (inactive, filtered out)
        assert 'KEG.UN' not in symbols

    def test_load_ohlcv(self, populated_db):
        calc = IndicatorCalculator(populated_db)
        ohlcv = calc.load_ohlcv('RY')
        assert ohlcv is not None
        assert len(ohlcv['close']) == 260
        assert len(ohlcv['dates']) == 260

    def test_load_ohlcv_insufficient_data(self, populated_db):
        calc = IndicatorCalculator(populated_db)
        ohlcv = calc.load_ohlcv('CM')
        assert ohlcv is None  # Only 100 rows, needs 250+

    def test_save_and_retrieve_indicators(self, populated_db):
        """Test the wide-column indicator save format."""
        calc = IndicatorCalculator(populated_db)

        # Create simple indicator data
        dates = ['2025-06-01', '2025-06-02', '2025-06-03']
        indicators = {
            'sma_20': [150.0, 150.1, 150.2],
            'rsi_14': [55.0, 56.0, 57.0],
            'macd': [0.5, 0.6, 0.7],
        }

        n = calc.save_indicators('RY', dates, indicators)
        assert n == 3

        # Verify they were saved
        with populated_db.connect() as conn:
            rows = conn.fetchall(
                "SELECT * FROM indicators_json WHERE symbol = %s ORDER BY price_date",
                ('RY',)
            )
            assert len(rows) == 3
            assert rows[0]['sma_20'] == 150.0
            assert rows[0]['rsi_14'] == 55.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
