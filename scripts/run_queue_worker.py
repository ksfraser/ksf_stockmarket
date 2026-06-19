#!/usr/bin/env python3
"""Run the lifecycle queue worker continuously."""

from __future__ import annotations

import logging
import sys

from python.db_connector import get_connection
from python.src.lifecycle.state import SymbolState
from python.src.lifecycle.repository import SymbolLifecycleRepository
from python.src.lifecycle.worker_app import run_forever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    db = get_connection()
    worker = LifecycleWorker(MYSQL, db)
    try:
        worker.run_forever(poll_seconds=30)
    except KeyboardInterrupt:
        logger.info("Stopping worker")
        return 0
    except Exception:
        logger.exception("Worker failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
