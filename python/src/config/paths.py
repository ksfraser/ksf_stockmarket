"""Master path configuration for the stockmarket app.

Set APP_ROOT once; everything else derives from it.
Used by Python cron jobs, PHP scripts, and the repo test suite.
"""

from __future__ import annotations

import os
from pathlib import Path

# Prefer explicit override, fall back to repo root when imported as package,
# finally fall back to cwd for ad-hoc cron invocations.
_guessed = Path(__file__).resolve().parents[3]  # python/src/config/ → repo root
APP_ROOT = Path(os.environ.get("APP_ROOT", _guessed))
APP_ROOT.mkdir(parents=True, exist_ok=True)

# App-relative data store (SQLite / temp artefacts)
DATA_DIR = APP_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite databases
ANALYTICS_DB = DATA_DIR / "analysis_results.db"
INTRADAY_PRICE_DB = DATA_DIR / "analysis_results.db"  # price_intraday table
ALERT_STAGING_DB = DATA_DIR / "alert_staging.db"
DETECTION_ALERT_DB = DATA_DIR / "analysis_results.db"  # alert_queue table (detection_triggers)

# MariaDB target
MARIADB_NAME = "ksfraser_stock_market"
MARIADB_USER = "ksfraser_stockmarket"
MARIADB_HOST = "ksfraser.ca"

# Logs (rotate externally)
LOG_DIR = APP_ROOT / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Public asset roots (for PHP / HTML)
PUBLIC_HTML = APP_ROOT / "public_html"
TEMPLATES_DIR = APP_ROOT / "templates"
