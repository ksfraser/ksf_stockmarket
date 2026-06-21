#!/usr/bin/env python3
"""Run the lifecycle queue worker continuously."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "python" / "src"
for candidate in (str(REPO_ROOT), str(SRC_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from python.src.queue_worker import LifecycleWorker
from python.db_connector import get_connection, DB_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _mysql_config() -> dict:
    backend = DB_CONFIG.get("backend") or "mysql"
    if backend != "mysql":
        raise RuntimeError(f"Queue worker requires mysql backend, got {backend}")
    return {
        "host": DB_CONFIG["host"],
        "port": int(DB_CONFIG.get("port", 3306)),
        "database": DB_CONFIG["database"],
        "user": DB_CONFIG["user"],
        "password": DB_CONFIG["password"],
        "charset": DB_CONFIG.get("charset", "utf8mb4"),
        "cursorclass": __import__("pymysql.cursors").cursors.DictCursor,
        "autocommit": False,
    }


def main() -> int:
    db = get_connection()
    config = _mysql_config()
    try:
        worker = LifecycleWorker(mysql_config=config, db=db)
        while True:
            worker.claim_once()
    except KeyboardInterrupt:
        logger.info("Stopping worker")
        return 0
    except Exception:
        logger.exception("Worker failed")
        return 1
    finally:
        try:
            db.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
