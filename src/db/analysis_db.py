"""Analysis database module — SQLite-backed stub.

Replaces the original ``analysis_db.get_db() -> None`` stub so cron/standalone
scripts that call ``get_db()`` receive a working SQLite connection wired to the
project's ``data/analysis_results.db`` file.
"""

from __future__ import annotations

import os
import sqlite3

# ── Path setup ───────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
# analysis_db.py is at src/db/analysis_db.py → db → src → project root via 2 dirname calls
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
_DB_PATH = os.path.join(_PROJECT_ROOT, "data", "analysis_results.db")
_DB_PATH = os.environ.get("ANALYSIS_DB", _DB_PATH)

# Minimal inline schema matching weight_optimizer.SCHEMA_SQL (subset needed
# by the daily monitor: signal_weights table + its index).
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS signal_weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0.0,
    default_weight REAL NOT NULL DEFAULT 0.0,
    n_updates INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, signal_type)
);
CREATE INDEX IF NOT EXISTS idx_weights_ticker ON signal_weights(ticker);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    # executescript() allows multiple statements (unlike execute()).
    conn.executescript(_SCHEMA_SQL)
    conn.commit()
    return conn


def get_db() -> sqlite3.Connection:
    """Return the analysis database connection (open each call — sqlite safe)."""
    return _connect()
