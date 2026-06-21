"""Event publisher for lifecycle and domain events."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


class EventPublishError(Exception):
    """Raised when an event cannot be persisted."""


class EventPublisher:
    def __init__(self, db) -> None:
        self.db = db

    def publish(self, event_type: str, payload: dict[str, Any]) -> str:
        event_id = str(uuid4())
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO event_queue "
                "(event_id, event_type, payload, occurred_at, status, attempts, last_error) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    event_id,
                    event_type,
                    _json_safe(payload),
                    datetime.now().isoformat(),
                    "pending",
                    0,
                    None,
                ),
            )
        logger.info("Published event %s of type %s", event_id, event_type)
        return event_id

    def publish_symbol_state(self, symbol: str, state, source: str) -> str:
        return self.publish(
            "symbol_state_changed",
            {
                "symbol": symbol,
                "state": state.value if hasattr(state, "value") else str(state),
                "source": source,
            },
        )

    def publish_screener_ingested(self, symbols: list[str], preset_name: str) -> str:
        return self.publish(
            "screener_symbols_ingested",
            {"symbols": symbols, "preset_name": preset_name},
        )

    def publish_transaction_created(
        self,
        transaction_id: int,
        user_id: int,
        symbol: str,
        transaction_type: str,
        source: str = "transaction_controller",
    ) -> str:
        return self.publish(
            "transaction_created",
            {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "symbol": symbol,
                "transaction_type": transaction_type,
                "source": source,
            },
        )



