"""
tests/conftest.py — Shared pytest fixtures.

Add project root to sys.path so tests can import from python/.
Provides test database helpers for unit tests.
"""
import sys
import os
import tempfile
import sqlite3

# Add python/ to import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

# ── Test database helpers ───────────────────────────────────────────────────

_test_db_path = None


def setup_test_database():
    """Create a fresh SQLite test database with schema."""
    global _test_db_path
    _test_db_path = tempfile.mktemp(suffix='.db', prefix='ksf_test_')

    conn = sqlite3.connect(_test_db_path)
    conn.row_factory = sqlite3.Row

    # Create tables matching the production schema
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS symbol_master (
            symbol VARCHAR(20) PRIMARY KEY,
            name VARCHAR(100),
            exchange VARCHAR(10),
            is_active INTEGER DEFAULT 1,
            is_portfolio INTEGER DEFAULT 0,
            is_watchlist INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS stockprices (
            symbol VARCHAR(20) NOT NULL,
            price_date DATE NOT NULL,
            open FLOAT,
            high FLOAT,
            low FLOAT,
            close FLOAT,
            volume INTEGER,
            PRIMARY KEY (symbol, price_date)
        );

        CREATE TABLE IF NOT EXISTS indicators (
            symbol VARCHAR(20) NOT NULL,
            price_date DATE NOT NULL,
            sma_20 FLOAT,
            sma_50 FLOAT,
            sma_200 FLOAT,
            ema_12 FLOAT,
            ema_26 FLOAT,
            rsi_14 FLOAT,
            macd FLOAT,
            macd_signal FLOAT,
            macd_hist FLOAT,
            atr_14 FLOAT,
            adx_14 FLOAT,
            stoch_k FLOAT,
            stoch_d FLOAT,
            cci_14 FLOAT,
            willr_14 FLOAT,
            PRIMARY KEY (symbol, price_date)
        );

        CREATE TABLE IF NOT EXISTS indicators_json (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(20) NOT NULL,
            price_date DATE NOT NULL,
            data TEXT,
            sma_20 FLOAT,
            sma_50 FLOAT,
            sma_200 FLOAT,
            rsi_14 FLOAT,
            macd FLOAT,
            macd_signal FLOAT,
            macd_hist FLOAT,
            UNIQUE(symbol, price_date)
        );

        CREATE TABLE IF NOT EXISTS evalsummary (
            symbol VARCHAR(20) PRIMARY KEY,
            last_eval_date DATE,
            direction VARCHAR(20),
            strength FLOAT,
            consensus_pct FLOAT,
            consensus_score FLOAT,
            ga_signal VARCHAR(20),
            nn_signal VARCHAR(20),
            rl_signal VARCHAR(20),
            blended_signal VARCHAR(20),
            target_weight FLOAT,
            current_weight FLOAT,
            recommended_action VARCHAR(50),
            urgency VARCHAR(20),
            reason TEXT
        );

        CREATE TABLE IF NOT EXISTS signal_weights (
            agent VARCHAR(20) PRIMARY KEY,
            weight FLOAT,
            confidence FLOAT,
            total_signals INTEGER DEFAULT 0,
            correct_signals INTEGER DEFAULT 0,
            accuracy FLOAT DEFAULT 0.5
        );

        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(20) NOT NULL,
            account_type VARCHAR(20),
            shares FLOAT,
            cost_basis FLOAT,
            strategy VARCHAR(50),
            entry_date DATE,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS analyst_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(20) NOT NULL,
            firm VARCHAR(100),
            rating VARCHAR(20),
            target_price FLOAT,
            rating_date DATE
        );
    """)

    conn.commit()
    conn.close()


def get_test_db():
    """Get a connection to the test database."""
    global _test_db_path
    if _test_db_path is None:
        setup_test_database()
    conn = sqlite3.connect(_test_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def seed_test_prices(symbol='RY', days=260, base_price=150.0):
    """Seed test price data for a symbol."""
    import datetime
    conn = get_test_db()
    base_date = datetime.date(2025, 6, 1)
    for i in range(days):
        d = base_date + datetime.timedelta(days=i)
        price = base_price + i * 0.1 + (i % 7) * 0.5
        conn.execute(
            "INSERT OR REPLACE INTO stockprices (symbol, price_date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (symbol, str(d), price - 0.5, price + 1.0, price - 1.0, price, 1000000 + i * 1000)
        )
    conn.commit()
    conn.close()


def seed_test_indicators(symbol='RY'):
    """Seed test indicator data."""
    import datetime, random
    conn = get_test_db()
    base_date = datetime.date(2025, 6, 1)
    for i in range(260):
        d = base_date + datetime.timedelta(days=i)
        conn.execute(
            "INSERT OR REPLACE INTO indicators "
            "(symbol, price_date, sma_20, sma_50, sma_200, rsi_14, macd, atr_14, adx_14) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, str(d),
             150.0 + i * 0.1, 148.0 + i * 0.08, 145.0 + i * 0.05,
             50.0 + random.uniform(-20, 20),
             random.uniform(-2, 2),
             1.5 + random.uniform(-0.5, 0.5),
             25.0 + random.uniform(-10, 10))
        )
    conn.commit()
    conn.close()


def seed_test_evalsummary():
    """Seed test evaluation summary data."""
    conn = get_test_db()
    conn.execute(
        "INSERT OR REPLACE INTO evalsummary "
        "(symbol, direction, strength, consensus_pct, consensus_score, recommended_action) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ('RY', 'BUY', 75.0, 85.0, 0.8, 'HOLD')
    )
    conn.commit()
    conn.close()


def seed_test_signal_weights():
    """Seed test signal weights for agents."""
    conn = get_test_db()
    weights = [
        ('GA', 0.33, 0.55, 100, 55, 0.55),
        ('NN', 0.34, 0.53, 100, 53, 0.53),
        ('RL', 0.33, 0.51, 100, 51, 0.51),
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO signal_weights "
        "(agent, weight, confidence, total_signals, correct_signals, accuracy) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        weights
    )
    conn.commit()
    conn.close()


def cleanup_test_db():
    """Remove the test database file."""
    global _test_db_path
    if _test_db_path and os.path.exists(_test_db_path):
        os.unlink(_test_db_path)
        _test_db_path = None
