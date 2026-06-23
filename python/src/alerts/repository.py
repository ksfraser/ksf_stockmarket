"""Alert repository / DAO.

All MariaDB access for alert_queue lives here.  Higher-level code
should call write_alert(detection_result) or fetch_pending() rather
than constructing SQL ad hoc.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import pymysql
from .config_mysql import MYSQL
from .dto import Alert, DetectionResult

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
    if detection.skipped or detection.alert is None:
        return False

    alert = detection.alert
    alert_type = alert.alert_type
    symbol = alert.symbol

    conn = _conn()
    try:
        cur = conn.cursor()

        if alert_type in ("volume_spike", "gap_up", "natr_spike"):
            if _same_day_alert_exists(cur, alert_type, symbol):
                logger.info("Skip same-day %s duplicate for %s", alert_type, symbol)
                conn.close()
                return False

        if alert_type == "oscillator_extremes":
            if _same_day_alert_exists(cur, alert_type, symbol) and not _oscillator_intraday_exception(alert):
                logger.info("Skip same-day %s duplicate for %s", alert_type, symbol)
                conn.close()
                return False

        now = datetime.now()
        alert_id = f"{symbol}_{alert_type}_{now.strftime('%Y%m%d%H%M%S')}"
        cur.execute(
            """
            INSERT INTO alert_queue
              (id, alert_type, symbol, severity, payload, status, request_llm_analysis)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s)
            ON DUPLICATE KEY UPDATE
              severity = VALUES(severity),
              payload  = VALUES(payload),
              status   = VALUES(status)
            """,
            (
                alert_id,
                alert_type,
                symbol,
                alert.severity,
                json.dumps(alert.payload),
                1,
            ),
        )
        conn.commit()
        logger.info("Queued alert %s", alert_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to queue alert: %s", exc)
        conn.rollback()
        conn.close()
        return False

    conn.close()
    return True


def _same_day_alert_exists(cur: Any, alert_type: str, symbol: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) FROM alert_queue
        WHERE symbol = %s
          AND alert_type = %s
          AND DATE(created_at) = CURDATE()
          AND status != 'failed'
        """,
        (symbol, alert_type),
    )
    return int(cur.fetchone()[0]) > 0


def _oscillator_intraday_exception(alert: Alert) -> bool:
    payload = alert.payload or {}
    rsi = payload.get("rsi_20d") or payload.get("rsi")
    if rsi is None:
        return False
    try:
        value = abs(float(rsi) - 70.0) < 5.0 or abs(float(rsi) - 30.0) < 5.0
    except (TypeError, ValueError):
        return False
    return value
