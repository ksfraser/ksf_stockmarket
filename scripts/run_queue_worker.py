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
from python.config_loader import Config
from python.db.mysql_adapter import MySQLConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _mysql_config() -> dict:
    cfg = Config(str(REPO_ROOT / 'config.yaml'))
    return {
        'host': cfg.data.db_host,
        'port': int(getattr(cfg.data, 'db_port', 3306)),
        'database': cfg.data.db_name,
        'user': cfg.data.db_user,
        'password': cfg.db_password,
    }


def main() -> int:
    config = _mysql_config()
    conn = MySQLConnection(**config)
    try:
        worker = LifecycleWorker(mysql_config=config, db=conn)
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
            conn.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
