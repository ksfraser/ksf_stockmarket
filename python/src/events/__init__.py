"""Event contracts and repository for the stockmarket domain.

Single source of truth for event types and persistence.
"""
from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, List, Optional
from datetime import datetime

import pymysql

from ..stockmarket.domain.contracts import Event  # canonical contract

logger = getLogger(__name__)


class EventRepository:
    """MariaDB-backed queue with claim semantics."""

    def __init__(self, db=None) -> None:
        self.db = db

    def enqueue(self, event: Event) -> bool:
        cursor = self.db.cursor()
        try:
            cursor.execute(
                "INSERT INTO event_queue "
                "(event_id, event_type, payload, status, occurred_at, attempts, last_error) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    event.event_id,
                    event.event_type,
                    _to_json(event.payload),
                    event.status,
                    event.occurred_at,
                    event.attempts,
                    event.last_error,
                ),
            )
            self.db.commit()
            logger.info("Enqueued %s", event.event_id)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("enqueue failed: %s", exc)
            return False

    def claim(self, limit: int = 10, max_attempts: int = 5) -> List[Event]:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT event_id, event_type, payload, occurred_at, processed_at, "
            "       status, attempts, last_error "
            "FROM event_queue "
            "WHERE status = 'pending' AND attempts <= %s "
            "ORDER BY occurred_at ASC "
            "LIMIT %s FOR UPDATE SKIP LOCKED",
            (max_attempts, limit),
        )
        rows = cursor.fetchall()
        for r in rows:
            cursor.execute("UPDATE event_queue SET status='running' WHERE event_id=%s", (r[0],))
        self.db.commit()
        return [self._from_row(r) for r in rows]

    def mark_completed(self, event_id: str) -> None:
        self._exec("UPDATE event_queue SET status='completed', processed_at=%s WHERE event_id=%s", (datetime.now(), event_id))

    def mark_failed(self, event_id: str, error: str, attempts: int = 0) -> None:
        self._exec(
            "UPDATE event_queue SET status='failed', last_error=%s, attempts=%s WHERE event_id=%s",
            (error[:5000], attempts, event_id),
        )

    def _from_row(self, row: Any) -> Event:
        return Event(
            event_id=row[0],
            event_type=row[1],
            payload=_from_json(row[2]),
            occurred_at=row[3] or datetime.now(),
            processed_at=row[4],
            status=row[5] or "pending",
            attempts=int(row[6] or 0),
            last_error=row[7],
        )

    def _exec(self, sql: str, params: tuple) -> None:
        cursor = self.db.cursor()
        try:
            cursor.execute(sql, params)
            self.db.commit()
        finally:
            cursor.close()


def _to_json(value: Dict[str, Any]) -> str:
    try:
        import json

        return json.dumps(value, default=str)
    except Exception:
        return str(value)


def _from_json(raw: Optional[str]) -> Dict[str, Any]:
    import json

    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": str(raw)}
