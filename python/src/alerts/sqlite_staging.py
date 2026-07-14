"""SQLite staging for alert queue — transient market-hour alert buffer."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pymysql

from alerts.dto import Alert, DetectionResult
from alerts.config_mysql import MYSQL
from config.paths import ALERT_STAGING_DB

logger = logging.getLogger(__name__)

STAGING_DB = ALERT_STAGING_DB
STAGING_DB.parent.mkdir(parents=True, exist_ok=True)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS alert_queue_staging (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    alert_type TEXT,
    symbol TEXT,
    severity TEXT,
    payload TEXT,
    status TEXT DEFAULT 'pending',
    request_llm_analysis INTEGER DEFAULT 1,
    llm_analysis TEXT,
    completed_at TEXT,
    try_count INTEGER DEFAULT 0,
    last_try_at TEXT,
    last_error TEXT,
    discord_dispatched INTEGER DEFAULT 0,
    discord_dispatched_at TEXT
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(STAGING_DB))
    conn.row_factory = sqlite3.Row
    return conn


def init_staging_db() -> None:
    conn = _conn()
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
    finally:
        conn.close()


def _alert_to_row(alert: Alert, alert_id: str) -> tuple:
    triggered_at = alert.triggered_at or datetime.now().isoformat()
    payload = json.dumps(alert.payload) if alert.payload else '{}'
    return (alert_id, triggered_at, alert.alert_type, alert.symbol, alert.severity,
            payload, 'pending', 1, None, None, 0, None, None, 0, None)


def write_alert_staging(detection: DetectionResult) -> bool:
    if detection.skipped or detection.alert is None:
        return False

    alert = detection.alert
    alert_id = f"{alert.symbol}_{alert.alert_type}_{datetime.now().strftime('%Y%m%d')}"
    row = _alert_to_row(alert, alert_id)

    conn = _conn()
    try:
        conn.execute("""
            INSERT INTO alert_queue_staging
                (id, created_at, alert_type, symbol, severity, payload, status,
                 request_llm_analysis, llm_analysis)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', 1, NULL)
            ON CONFLICT(id) DO UPDATE SET
                severity = excluded.severity,
                payload  = excluded.payload,
                status   = 'pending'
        """, row[:6])
        conn.commit()
        logger.info("Staged alert %s", alert_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to stage alert: %s", exc)
        return False
    finally:
        conn.close()


def fetch_pending_staging(limit: int = 50) -> Iterable[Dict[str, Any]]:
    conn = _conn()
    try:
        cur = conn.execute("""
            SELECT id, created_at, alert_type, symbol, severity, payload,
                   status, request_llm_analysis
            FROM alert_queue_staging
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))
        for row in cur.fetchall():
            yield dict(row)
    finally:
        conn.close()


def mark_completed_staging(alert_id: str) -> None:
    conn = _conn()
    try:
        conn.execute("""
            UPDATE alert_queue_staging
            SET status = 'completed', completed_at = ?, try_count = try_count + 1
            WHERE id = ?
        """, (datetime.now().isoformat(), alert_id))
        conn.commit()
    finally:
        conn.close()


# ── MariaDB promotion helpers ─────────────────────────────────────────────
# Used by monitor after LLM analysis: only the *final* completed alert
# is written back to production MariaDB, not every detection event.

def _mysql_conn() -> pymysql.connections.Connection:
    return pymysql.connect(**MYSQL)


def promote_to_mariadb(alert_staging: Dict[str, Any], llm_analysis: str) -> None:
    """
    Upsert final alert state into MariaDB alert_queue and record response.
    This is the only MariaDB write path for alerts during market hours.
    """
    conn = _mysql_conn()
    try:
        cur = conn.cursor()
        payload = json.loads(alert_staging['payload']) if isinstance(alert_staging.get('payload'), str) else alert_staging.get('payload', {})
        now_str = datetime.now().isoformat()

        cur.execute("""
            INSERT INTO alert_queue
              (id, alert_type, symbol, severity, payload, status, request_llm_analysis,
               llm_analysis, try_count, completed_at)
            VALUES (%s, %s, %s, %s, %s, 'completed', %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
              severity      = VALUES(severity),
              payload       = VALUES(payload),
              status        = 'completed',
              llm_analysis  = VALUES(llm_analysis),
              try_count     = VALUES(try_count),
              completed_at  = NOW()
        """, (
            alert_staging['id'],
            alert_staging['alert_type'],
            alert_staging['symbol'],
            alert_staging['severity'],
            json.dumps(payload),
            1,
            llm_analysis[:500] if llm_analysis else None,
            1,
        ))

        cur.execute("""
            INSERT INTO alert_responses
              (alert_id, response_text, response_type, responder)
            VALUES (%s, %s, 'hermes', 'hermes_alert_monitor')
        """, (alert_staging['id'], llm_analysis[:1000]))

        conn.commit()
        logger.info("Promoted alert %s to MariaDB", alert_staging['id'])
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        logger.error("Failed to promote alert to MariaDB: %s", exc)
        raise
    finally:
        conn.close()
