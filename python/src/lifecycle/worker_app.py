"""Queue worker app: claim events, advance symbol lifecycle, emit follow-up events."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

import pymysql

from lifecycle.state import SymbolState, advance_state, TERMINAL_STATES
from lifecycle.repository import SymbolLifecycleRepository
from events.publisher import EventPublisher, EventPublishError

logger = logging.getLogger(__name__)


MYSQL = {
    "host": "ksfraser.ca",
    "port": 3306,
    "user": "ksfraser_stockmarket",
    "password": "Zaqwsx9sm1@",
    "database": "ksfraser_stock_market",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


class WorkerApp:
    def __init__(self):
        self.conn = pymysql.connect(**MYSQL)
        self.conn.autocommit(False)
        self.repository = SymbolLifecycleRepository(self.conn)
        self.publisher = EventPublisher(self.conn)

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def emit_symbol_state_changed(self, symbol: str, state: str) -> None:
        payload = {
            "symbol": symbol,
            "pipeline_state": state,
            "changed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.publisher.publish("symbol_state_changed", payload)
        logger.info("Emitted symbol_state_changed for %s -> %s", symbol, state)

    def process(self, event: dict[str, Any]) -> None:
        event_type = event.get("event_type")
        payload = event.get("payload", {}) or {}
        try:
            if event_type == "screener_symbols_ingested":
                self._handle_screener_ingested(payload)
            elif event_type == "transaction_created":
                self._handle_transaction_created(payload)
            elif event_type == "symbol_activated":
                self._handle_symbol_activated(payload)
            elif event_type == "symbol_deactivated":
                self._handle_symbol_deactivated(payload)
            else:
                logger.info("No handler for event type %s", event_type)
        except Exception as error:
            logger.exception("Failed to process event %s: %s", event.get("event_id"), error)
            raise

    def _handle_screener_ingested(self, payload: dict[str, Any]) -> None:
        symbols = payload.get("symbols") or []
        for symbol in symbols:
            current = self.repository.get_symbol_pipeline_state(symbol)
            next_state = advance_symbol_state(current, "candidate")
            self.repository.set_symbol_pipeline_state(symbol, next_state)
            self.emit_symbol_state_changed(symbol, next_state)
        logger.info("Processed screener ingestion for %s symbols", len(symbols))

    def _handle_transaction_created(self, payload: dict[str, Any]) -> None:
        symbol = payload.get("symbol")
        if not symbol:
            return
        current = self.repository.get_symbol_pipeline_state(symbol)
        next_state = advance_symbol_state(current, "candidate")
        self.repository.set_symbol_pipeline_state(symbol, next_state)
        self.emit_symbol_state_changed(symbol, next_state)

    def _handle_symbol_activated(self, payload: dict[str, Any]) -> None:
        symbol = payload.get("symbol")
        if not symbol:
            return
        current = self.repository.get_symbol_pipeline_state(symbol)
        next_state = advance_symbol_state(current, "candidate")
        self.repository.set_symbol_pipeline_state(symbol, next_state)
        self.emit_symbol_state_changed(symbol, next_state)

    def _handle_symbol_deactivated(self, payload: dict[str, Any]) -> None:
        symbol = payload.get("symbol")
        if not symbol:
            return
        if symbol in self.repository.iter_active_symbols():
            self.repository.set_symbol_pipeline_state(symbol, "inactive")


def run_event_processor():
    worker = WorkerApp()
    try:
        logger.info("Worker started")
        while True:
            batch = claim_events(worker.conn, limit=50)
            if not batch:
                time.sleep(30)
                continue
            for event in batch:
                try:
                    event_id = event.get("event_id")
                    worker.process(event)
                    mark_completed(worker.conn, event_id)
                except Exception:
                    mark_failed(worker.conn, event.get("event_id"))
            worker.conn.commit()
    finally:
        worker.close()


def claim_events(conn, limit: int = 50) -> list[dict[str, Any]]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT event_id, event_type, payload
            FROM event_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
            """,
            (limit,),
        )
        rows = cursor.fetchall() or []
        event_ids = [row[0] for row in rows]
        if event_ids:
            placeholders = ",".join(["%s"] * len(event_ids))
            cursor.execute(
                f"UPDATE event_queue SET status='running' WHERE event_id IN ({placeholders})",
                event_ids,
            )
    conn.commit()
    return [{"event_id": row[0], "event_type": row[1], "payload": _decode_payload(row[2])} for row in rows]


def mark_completed(conn, event_id: str) -> None:
    if not event_id:
        return
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE event_queue SET status='completed', processed_at=%s WHERE event_id=%s",
            (datetime.now(timezone.utc), event_id),
        )


def mark_failed(conn, event_id: str) -> None:
    if not event_id:
        return
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE event_queue SET status='failed', last_error='handler error', attempts=attempts + 1 WHERE event_id=%s",
            (event_id,),
        )


def _decode_payload(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        if isinstance(raw, (dict, list)):
            return raw
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        return json.loads(raw)
    except Exception:
        return {"raw": str(raw)}


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        run_event_processor()
    except KeyboardInterrupt:
        logger.info("Queue worker stopped")
        sys.exit(0)
