"""
tests/conftest.py — Pytest configuration and test helpers for ksf_stockmarket
==============================================================================
This file serves dual purpose:
1. Pytest conftest.py — provides fixtures (test_db, seeded_db)
2. Test helpers — database setup, data seeding, cleanup

All tests import fixtures from here via pytest's conftest mechanism.
Direct imports use: from tests.conftest import setup_test_database
"""

import pytest
import sqlite3
import json
import os
import numpy as np

# ===========================================================================
# SQLite → MySQL compatibility shim for tests
# ===========================================================================

def _patch_sqlite_cursor():
    """Monkeypatch sqlite3 to accept cursor(dictionary=True) like MySQL."""
    _orig_cursor = sqlite3.Connection.cursor

    def _patched_cursor(self, *args, **kwargs):
        kwargs.pop('dictionary', None)
        return _orig_cursor(self, *args, **kwargs)

    sqlite3.Connection.cursor = _patched_cursor


def _patch_sqlite_execute():
    """Monkeypatch sqlite3 to translate %s placeholders to ? for parameterized queries."""
    _orig_execute = sqlite3.Cursor.execute
    _orig_executemany = sqlite3.Cursor.executemany

    def _patched_execute(self, sql, params=None):
        if isinstance(sql, str):
            sql = sql.replace('%s', '?')
        return _orig_execute(self, sql, params)

    def _patched_executemany(self, sql, params=None):
        if isinstance(sql, str):
            sql = sql.replace('%s', '?')
        return _orig_executemany(self, sql, params)

    sqlite3.Cursor.execute = _patched_execute
    sqlite3.Cursor.executemany = _patched_executemany

# ===========================================================================
# Configuration
# ===========================================================================

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_data.db')


# ===========================================================================
# Database Setup & Teardown
# ===========================================================================

def get_test_db():
    """Get a fresh SQLite connection to the test database."""
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
    return sqlite3.connect(TEST_DB_PATH)


def setup_test_database():
    """Create all tables needed for testing. Mirrors MariaDB schema."""
    db = get_test_db()
    c = db.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS stockprices (
        symbol TEXT NOT NULL, price_date TEXT NOT NULL,
        day_open REAL, day_high REAL, day_low REAL, day_close REAL, volume REAL,
        PRIMARY KEY (symbol, price_date)
    );
    CREATE TABLE IF NOT EXISTS daily_indicators (
        symbol TEXT NOT NULL, price_date TEXT NOT NULL,
        daily_return REAL, gap_pct REAL, sma_20 REAL, sma_50 REAL, sma_200 REAL,
        volume_sma_20 INTEGER,
        PRIMARY KEY (symbol, price_date)
    );
    CREATE TABLE IF NOT EXISTS daily_tier2 (
        symbol TEXT NOT NULL, price_date TEXT NOT NULL,
        bb_middle REAL, bb_upper REAL, bb_lower REAL, bb_width REAL, bb_pct REAL,
        atr_14 REAL, atr_pct REAL, vol_ratio_20 REAL, vol_ratio_50 REAL,
        trend_50_200 TEXT, signal_strength INTEGER, signal_reasons TEXT,
        calc_method TEXT DEFAULT 'python',
        PRIMARY KEY (symbol, price_date)
    );
    CREATE TABLE IF NOT EXISTS ta_values (
        symbol TEXT NOT NULL, price_date TEXT NOT NULL, indicator TEXT NOT NULL,
        value REAL, signal TEXT, source TEXT DEFAULT 'ta_lib',
        PRIMARY KEY (symbol, price_date, indicator)
    );
    CREATE TABLE IF NOT EXISTS signal_weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL, signal_type TEXT NOT NULL,
        weight REAL DEFAULT 1.0, default_weight REAL DEFAULT 1.0,
        win_rate REAL, n_trades INTEGER, avg_return REAL,
        avg_lead_days REAL, is_pre_indicator INTEGER DEFAULT 0,
        correlation REAL, correlates_with TEXT, weight_boosted REAL,
        boost_condition TEXT, last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_by TEXT DEFAULT 'manual',
        UNIQUE (symbol, signal_type)
    );
    CREATE TABLE IF NOT EXISTS evalsummary (
        symbol TEXT PRIMARY KEY, totalscore INTEGER, marginsafety REAL,
        ratioscore INTEGER, iplacecalcscore INTEGER, managementscore INTEGER,
        financialscore INTEGER, businessscore INTEGER, mf_score INTEGER,
        ip_score INTEGER, tenet_score INTEGER, value_score INTEGER,
        llm_summary TEXT, llm_confidence REAL, llm_recommendation TEXT,
        last_eval_date TEXT
    );
    CREATE TABLE IF NOT EXISTS agent_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_type TEXT NOT NULL, run_name TEXT, priority INTEGER DEFAULT 5,
        machine_id TEXT, status TEXT DEFAULT 'queued', symbol_target TEXT,
        region TEXT, started_at TEXT, completed_at TEXT, duration_sec INTEGER,
        reward_score REAL, result_json TEXT, error_message TEXT,
        parent_run_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS nn_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL, prediction_date TEXT NOT NULL, model_version TEXT,
        agent_run_id INTEGER, direction TEXT NOT NULL, confidence REAL NOT NULL,
        predicted_return_5d REAL, predicted_return_20d REAL,
        raw_weight REAL, user_cap_weight REAL, feature_json TEXT,
        actual_return_5d REAL, actual_return_20d REAL, was_correct INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (symbol, prediction_date, model_version)
    );
    CREATE TABLE IF NOT EXISTS rl_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL, signal_date TEXT NOT NULL, model_version TEXT,
        agent_run_id INTEGER, action TEXT NOT NULL, target_weight REAL,
        current_weight REAL, confidence REAL, expected_reward REAL,
        state_json TEXT, realized_pnl REAL, reward_signal REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (symbol, signal_date, model_version)
    );
    CREATE TABLE IF NOT EXISTS ga_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_run_id INTEGER, symbol TEXT NOT NULL, generation INTEGER NOT NULL,
        weights_json TEXT NOT NULL, fitness_sharpe REAL, fitness_return REAL,
        fitness_maxdd REAL, fitness_composite REAL, is_best INTEGER DEFAULT 0,
        backtest_trades INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS portfolio_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_date TEXT NOT NULL, agent_run_id INTEGER, blender_run_id INTEGER,
        symbol TEXT NOT NULL, action TEXT NOT NULL, target_shares INTEGER,
        target_weight REAL, trade_shares INTEGER, estimated_price REAL,
        estimated_cost REAL, ga_signal TEXT, nn_signal TEXT, rl_signal TEXT,
        consensus_pct REAL, status TEXT DEFAULT 'pending', approved_by TEXT,
        executed_at TEXT, executed_price REAL, actual_pnl REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS agent_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_type TEXT NOT NULL, config_key TEXT NOT NULL,
        config_value TEXT NOT NULL, value_type TEXT DEFAULT 'string',
        description TEXT, is_active INTEGER DEFAULT 1, version INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (agent_type, config_key, is_active)
    );
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, symbol TEXT NOT NULL, shares REAL DEFAULT 0,
        cost_basis REAL DEFAULT 0, cost_total REAL DEFAULT 0,
        account_type TEXT DEFAULT 'RRSP', acquisition_date TEXT,
        is_active INTEGER DEFAULT 1, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (user_id, symbol, account_type)
    );
    CREATE TABLE IF NOT EXISTS user_position_caps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cap_type TEXT NOT NULL DEFAULT 'symbol', cap_target TEXT NOT NULL,
        max_position_pct REAL NOT NULL, is_active INTEGER DEFAULT 1,
        notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (cap_type, cap_target)
    );
    """)

    db.commit()

    # Seed configs
    configs = [
        ('ga', 'population_size', '50', 'int'),
        ('ga', 'num_generations', '10', 'int'),
        ('ga', 'mutation_rate', '0.15', 'float'),
        ('ga', 'crossover_rate', '0.8', 'float'),
        ('nn', 'sequence_length', '30', 'int'),
        ('nn', 'hidden_size', '32', 'int'),
        ('nn', 'num_layers', '1', 'int'),
        ('nn', 'dropout', '0.2', 'float'),
        ('nn', 'learning_rate', '0.001', 'float'),
        ('nn', 'batch_size', '16', 'int'),
        ('nn', 'epochs', '5', 'int'),
        ('rl', 'algorithm', 'PPO', 'string'),
        ('rl', 'max_episodes', '50', 'int'),
        ('blender', 'ga_weight', '0.30', 'float'),
        ('blender', 'nn_weight', '0.35', 'float'),
        ('blender', 'rl_weight', '0.35', 'float'),
        ('blender', 'consensus_threshold', '60.0', 'float'),
    ]
    for agent_type, key, value, vtype in configs:
        c.execute("INSERT OR IGNORE INTO agent_configs (agent_type, config_key, config_value, value_type) VALUES (?,?,?,?)",
                  (agent_type, key, value, vtype))

    # Seed position caps
    for ctype, target, pct in [
        ('global', 'default', 0.10), ('region', 'CDN', 0.15),
        ('region', 'USA', 0.15), ('region', 'EURO', 0.08),
        ('region', 'EMERGING', 0.05), ('account', 'TFSA', 0.10),
        ('account', 'RRSP', 0.10),
    ]:
        c.execute("INSERT OR IGNORE INTO user_position_caps (cap_type, cap_target, max_position_pct) VALUES (?,?,?)",
                  (ctype, target, pct))

    db.commit()
    db.close()


def cleanup_test_db():
    """Remove the test database file."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


# ===========================================================================
# Data Seeding
# ===========================================================================

def generate_test_prices(symbol='TEST.TO', days=300, start_price=50.0,
                          trend=0.0002, volatility=0.015, seed=42):
    """Generate realistic OHLCV price data for testing."""
    np.random.seed(seed)
    prices = []
    current_price = start_price
    base_date = __import__('datetime').date.today() - __import__('datetime').timedelta(days=days)

    for i in range(days):
        daily_return = np.random.normal(trend, volatility)
        open_price = current_price
        close_price = current_price * (1 + daily_return)
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
        volume = int(np.random.lognormal(mean=np.log(1e6), sigma=0.5))
        prices.append((
            (base_date + __import__('datetime').timedelta(days=i)).isoformat(),
            round(open_price, 2), round(high_price, 2),
            round(low_price, 2), round(close_price, 2), volume,
        ))
        current_price = close_price
    return prices


def seed_test_prices(db, symbols=None, days=300):
    """Insert test price data into the database."""
    symbols = symbols or ['TEST.TO', 'RY.TO', 'TD.TO', 'ENB.TO', 'BMO.TO']
    c = db.cursor()
    for symbol in symbols:
        prices = generate_test_prices(symbol=symbol, days=days,
                                       start_price=np.random.uniform(20, 200))
        c.executemany("INSERT OR REPLACE INTO stockprices VALUES (?,?,?,?,?,?,?)",
                      [(symbol, *p) for p in prices])
    db.commit()


def seed_test_indicators(db, symbols=None):
    """Generate realistic indicator data based on prices."""
    symbols = symbols or ['TEST.TO', 'RY.TO', 'TD.TO', 'ENB.TO', 'BMO.TO']
    c = db.cursor()
    for symbol in symbols:
        c.execute("SELECT price_date, day_open, day_high, day_low, day_close, volume FROM stockprices WHERE symbol = ? ORDER BY price_date ASC", (symbol,))
        rows = c.fetchall()
        if len(rows) < 20:
            continue
        closes = [r[4] for r in rows]
        volumes = [r[5] for r in rows]
        indicators = []
        for i, row in enumerate(rows):
            d_return = (closes[i] - closes[i-1]) / closes[i-1] if i > 0 else 0
            gap = (row[1] - closes[i-1]) / closes[i-1] if i > 0 else 0
            sma_20 = np.mean(closes[max(0,i-19):i+1]) if i >= 19 else None
            sma_50 = np.mean(closes[max(0,i-49):i+1]) if i >= 49 else None
            sma_200 = np.mean(closes[max(0,i-199):i+1]) if i >= 199 else None
            vol_sma = np.mean(volumes[max(0,i-19):i+1]) if i >= 19 else None
            indicators.append((symbol, row[0], d_return, gap, sma_20, sma_50, sma_200, int(vol_sma or 0)))
        c.executemany("INSERT OR REPLACE INTO daily_indicators VALUES (?,?,?,?,?,?,?,?)", indicators)
    db.commit()


def seed_test_evalsummary(db, symbols=None):
    """Seed evalsummary with realistic scoring data."""
    symbols = symbols or ['TEST.TO', 'RY.TO', 'TD.TO', 'ENB.TO', 'BMO.TO']
    c = db.cursor()
    for symbol in symbols:
        np.random.seed(hash(symbol) % 2**32)
        c.execute("""
            INSERT OR REPLACE INTO evalsummary (symbol, totalscore, marginsafety, ratioscore,
                iplacecalcscore, managementscore, financialscore, businessscore,
                mf_score, ip_score, tenet_score, value_score)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (symbol, int(np.random.randint(10, 30)), round(np.random.uniform(-10, 30), 2),
              int(np.random.randint(2, 8)), int(np.random.randint(2, 10)),
              int(np.random.randint(3, 9)), int(np.random.randint(1, 4)),
              int(np.random.randint(1, 5)), int(np.random.randint(0, 7)),
              int(np.random.randint(0, 15)), int(np.random.randint(40, 100)),
              int(np.random.randint(5, 20))))
    db.commit()


def seed_test_signal_weights(db, symbols=None):
    """Seed signal_weights with realistic GA-optimized weights."""
    symbols = symbols or ['TEST.TO', 'RY.TO', 'TD.TO']
    c = db.cursor()
    weight_keys = [f'w_{i}' for i in range(22)]
    for symbol in symbols:
        for key in weight_keys:
            c.execute("INSERT OR REPLACE INTO signal_weights (symbol, signal_type, weight) VALUES (?,?,?)",
                      (symbol, key, round(np.random.uniform(-2, 3), 4)))
    db.commit()


# ===========================================================================
# Pytest Fixtures
# ===========================================================================

def pytest_configure(config):
    # Point SQLite at the test database
    os.environ['DB_BACKEND'] = 'sqlite'
    os.environ['SQLITE_PATH'] = TEST_DB_PATH
    # Clear any cached config so it re-initializes
    import python.db_connector as _db
    _db.DB_CONFIG = {}
    setup_test_database()


def pytest_unconfigure(config):
    cleanup_test_db()


@pytest.fixture
def test_db():
    """Provide a fresh database connection for each test."""
    db = get_test_db()
    yield db
    db.close()


@pytest.fixture
def seeded_db(test_db):
    """Provide a database with test data pre-seeded."""
    seed_test_prices(test_db, symbols=['TEST.TO', 'RY.TO', 'TD.TO'], days=300)
    seed_test_indicators(test_db)
    seed_test_evalsummary(test_db)
    seed_test_signal_weights(test_db)
    return test_db
