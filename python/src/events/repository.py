"""MariaDB-backed event queue repository."""
from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import List, Optional
import pymysql
from .event_contract import Event

logger = logging.getLogger(__name__)
_mysql = {
    'host': 'ksfraser.ca',
    'port': 3306,
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': True,
}


class EventRepository:
    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(**_mysql)

    def _exec(self, sql, params=None):
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def enqueue(self, event: Event) -> bool:
        try:
            self._exec(
                "INSERT INTO event_queue (event_id, event_type, payload, status, occurred_at, attempts, last_error) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (event.event_id, event.event_type, json.dumps(event.payload, default=str), event.status,
                 event.occurred_at, event.attempts, event.last_error),
            )
            logger.info("Enqueued %s", event.event_id)
            return True
        except Exception as exc:
            logger.exception("enqueue failed for %s: %s", getattr(event, 'event_id', '?'), exc)
            return False

    def claim(self, limit: int = 10, max_attempts: int = 5) -> List[Event]:
        conn = pymysql.connect(**_mysql)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT event_id, event_type, payload, occurred_at, processed_at,
                       status, attempts, last_error
                FROM event_queue
                WHERE status = 'pending' AND attempts <= %s
                ORDER BY occurred_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (max_attempts, limit),
            )
            rows = cur.fetchall()
            for r in rows:
                cur.execute("UPDATE event_queue SET status='running' WHERE event_id=%s", (r[0],))
            conn.commit()
            return [self._row_to_event(r) for r in rows]
        finally:
            conn.close()

    def mark_completed(self, event_id: str) -> None:
        conn = pymysql.connect(**_mysql)
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE event_queue SET status='completed', processed_at=%s WHERE event_id=%s",
                (datetime.now(), event_id),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_failed(self, event_id: str, error: str, attempts: int = 0) -> None:
        conn = pymysql.connect(**_mysql)
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE event_queue SET status='failed', last_error=%s, attempts=%s WHERE event_id=%s",
                (error[:5000], attempts, event_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_event(self, row) -> Event:
        return Event(
            event_id=row['event_id'],
            event_type=row['event_type'],
            payload=json.loads(row['payload'] or '{}'),
            occurred_at=row['occurred_at'] or datetime.now(),
            processed_at=row['processed_at'],
            status=row['status'] or 'pending',
            attempts=int(row['attempts'] or 0),
            last_error=row['last_error'],
        )
