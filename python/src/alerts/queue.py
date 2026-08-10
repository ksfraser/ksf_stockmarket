"""Alert queue persistence with daily dedup guard."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict

import pymysql

from .checks import MYSQL

logger = logging.getLogger(__name__)


def same_day_alert_exists(cursor, alert_type: str, symbol: str) -> bool:
    """Return True if a non-failed alert of this type exists for symbol today."""
    try:
        cursor.execute(
            """
            SELECT COUNT(*) FROM alert_queue
            WHERE symbol = %s
              AND alert_type = %s
              AND DATE(created_at) = CURDATE()
              AND status != 'failed'
            """,
            (symbol, alert_type),
        )
        return int(cursor.fetchone()[0]) > 0
    except Exception:
        return False


def oscillator_intraday_exception(alert: Dict) -> bool:
    """Allow a second oscillator alert when RSI is very close to 30 or 70."""
    payload = ((alert or {}).get("payload") or {})
    rsi = payload.get("rsi_20d") or payload.get("rsi")
    if rsi is None:
        return False
    try:
        return abs(float(rsi) - 70.0) < 5.0 or abs(float(rsi) - 30.0) < 5.0
    except (TypeError, ValueError):
        return False


def write_alert(alert: Dict) -> bool:
    """Persist an alert dict to MariaDB, applying daily dedup rules."""
    alert_type = alert.get("alert_type") or alert.get("type")
    symbol = alert.get("symbol")

    conn = pymysql.connect(**MYSQL)
    try:
        cur = conn.cursor()
        if alert_type in ("volume_spike", "oscillator_extremes"):
            if alert_type == "volume_spike" and same_day_alert_exists(cur, alert_type, symbol):
                logger.info("Skip same-day volume duplicate for %s", symbol)
                return False
            if alert_type == "oscillator_extremes":
                if same_day_alert_exists(cur, alert_type, symbol) and not oscillator_intraday_exception(alert):
                    logger.info("Skip same-day oscillator duplicate for %s", symbol)
                    return False

        now = datetime.now()
        alert_id = f"{symbol}_{alert_type}_{now.strftime('%Y%m%d%H%M%S')}"
        cur.execute(
            """
            INSERT INTO alert_queue
              (id, alert_type, symbol, severity, payload, status, request_llm_analysis)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              severity = VALUES(severity),
              payload  = VALUES(payload),
              status   = VALUES(status)
            """,
            (
                alert_id,
                alert_type,
                symbol,
                alert.get("severity"),
                json.dumps(alert.get("payload") or {}, default=str),
                "pending",
                1 if alert_type in ("volume_spike", "gap_up", "natr_spike") else 0,
            ),
        )
        conn.commit()
        logger.info("Queued alert %s", alert_id)
        return True
    except Exception as exc:
        logger.error("Failed to queue alert: %s", exc)
        conn.rollback()
        return False
    finally:
        conn.close()
