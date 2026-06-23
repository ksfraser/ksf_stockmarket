#!/usr/bin/env python3
"""
Bootstrap symbol lifecycle states from live price/TA coverage.

Reads symbol_master and updates each active symbol's pipeline_state based on
whether price history and TA indicators exist. This should be run once after
the new state machine is deployed.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "python" / "src"
for candidate in (str(REPO_ROOT), str(SRC_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from python.src.lifecycle.state import SymbolState
from python.src.lifecycle.repository import SymbolLifecycleRepository
from python.db.mysql_adapter import MySQLConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    db = MySQLConnection(
        host="ksfraser.ca",
        user="ksfraser_stockmarket",
        password=os.environ.get("DB_PASSWORD", "Zaqwsx9sm1@"),
        database="ksfraser_stock_market",
    )
    try:
        db._ensure_open()
        repository = SymbolLifecycleRepository(db)

        rows = db.fetchall(
            "SELECT symbol, latest_price_date, latest_indicator_date "
            "FROM symbol_master WHERE is_active = 1"
        )

        updated = 0
        total = len(rows)
        for idx, row in enumerate(rows, start=1):
            symbol = row.get("symbol") if isinstance(row, dict) else row[0]
            if not symbol:
                continue
            is_complete = bool(
                (row.get("latest_price_date") if isinstance(row, dict) else None)
                and (row.get("latest_indicator_date") if isinstance(row, dict) else None)
            )
            state = SymbolState.ANALYSIS_ELIGIBLE if is_complete else SymbolState.CANDIDATE

            try:
                repository.set_state(symbol, state)
                updated += 1
            except Exception:
                logger.exception("Failed to bootstrap state for %s", symbol)

            if idx % 200 == 0:
                logger.info("Bootstrapped %s/%s symbols", idx, total)

        db.commit()
        logger.info("Bootstrapped %s/%s symbols", updated, total)
        return 0
    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
