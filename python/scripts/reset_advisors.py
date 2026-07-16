#!/usr/bin/env python3
"""Reset all advisor portfolios, transactions, and runs."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "python" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from db_connector import get_connection  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = get_connection()
    try:
        with db.cursor() as cur:
            # advisor portfolio
            cur.execute("DELETE FROM portfolio WHERE strategy IN ('advisor', 'buffett')")
            logger.info("portfolio rows deleted: %d", cur.rowcount)
            # advisor transactions
            cur.execute("""
                DELETE FROM transactions
                WHERE source_file IN ('advisor', 'backfill_advisor', 'backfill_historical_fundamentals')
                   OR notes LIKE 'Advisor %'
                   OR notes LIKE 'Initial advisor backfill seed'
            """)
            logger.info("transactions rows deleted: %d", cur.rowcount)
            # advisor runs
            cur.execute("DELETE FROM advisor_runs")
            logger.info("advisor_runs rows deleted: %d", cur.rowcount)
        db.commit()
        logger.info("Advisor reset complete")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
