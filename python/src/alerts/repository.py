"""Alert repository / DAO.

Production writes now go to the local SQLite staging DB first;
the monitor promotes completed alerts into MariaDB.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import pymysql
from .config_mysql import MYSQL
from .dto import Alert, DetectionResult
from .sqlite_staging import write_alert_staging, fetch_pending_staging, mark_completed_staging, promote_to_mariadb

logger = logging.getLogger(__name__)


def _conn() -> pymysql.connections.Connection:
    return pymysql.connect(**MYSQL)


def fetch_pending(limit: int = 50) -> Iterable[Dict]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, alert_type, symbol, severity, payload, status,
                   request_llm_analysis, created_at
            FROM alert_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (limit,),
        )
        cols = [c[0] for c in cur.description]
        for row in cur.fetchall():
            yield dict(zip(cols, row))
    finally:
        conn.close()


def mark_completed(alert_id: str) -> None:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE alert_queue SET status = 'completed', completed_at = NOW() WHERE id = %s",
            (alert_id,),
        )
        conn.commit()
    finally:
        conn.close()


def write_alert(detection: DetectionResult) -> bool:
    """Stage detection in local SQLite instead of hammering MariaDB directly."""
    return write_alert_staging(detection)
