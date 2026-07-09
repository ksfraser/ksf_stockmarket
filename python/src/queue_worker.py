"""Queue worker for lifecycle and data pipeline events."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pymysql

from lifecycle.state import SymbolState, advance_state, TERMINAL_STATES
from lifecycle.repository import SymbolLifecycleRepository
from events.publisher import EventPublisher

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_DIR = REPO_ROOT / "python"


class LifecycleWorker:
    def __init__(self, mysql_config: dict[str, Any], db) -> None:
        self.mysql_config = mysql_config
        self.db = db
        self.lifecycle_repo = SymbolLifecycleRepository(db)
        self.publisher = EventPublisher(db)

    def _spawn(self, script_name: str, args: list[str]) -> None:
        script = str(PYTHON_DIR / script_name)
        cmd = [sys.executable, script, *args]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        try:
            subprocess.Popen(
                cmd,
                cwd=str(REPO_ROOT),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            logger.exception("Failed to spawn %s", script_name)

    def pump(self, batch: int = 10) -> int:
        events = self._claim(batch)
        if not events:
            return 0
        processed = 0
        for event_id, event_type, payload in events:
            try:
                self.process(event_id, event_type, payload)
                processed += 1
            except Exception:
                logger.exception("Failed processing event %s", event_id)
                self._mark_failed(event_id)
        return processed

    def claim_once(self) -> None:
        processed = self.pump(50)
        logger.info("Queue pump processed %s events", processed)

    def run_forever(self, poll_seconds: int = 30) -> None:
        logger.info("Lifecycle worker started")
        while True:
            try:
                processed = self.pump(50)
                logger.debug("Pump processed %s events", processed)
            except Exception:
                logger.exception("Queue pump failed")
            time.sleep(poll_seconds)

    def process(self, event_id: str, event_type: str, payload: dict[str, Any]) -> None:
        handler = {
            "screener_symbols_ingested": self.handle_screener_symbols_ingested,
            "transaction_created": self.handle_transaction_created,
            "symbol_activated": self.handle_symbol_activated,
            "symbol_deactivated": self.handle_symbol_deactivated,
            "prices_loaded": self.handle_prices_loaded,
            "indicators_calculated": self.handle_indicators_calculated,
        }.get(event_type)
        if handler is None:
            logger.info("No handler for %s; marking complete", event_type)
            self._mark_complete(event_id)
            return

        if handler(payload):
            self._mark_complete(event_id)
        else:
            self._mark_failed(event_id)

    def handle_screener_symbols_ingested(self, payload: dict[str, Any]) -> bool:
        symbols = payload.get("symbols", []) or []
        if not symbols:
            return True
        for symbol in symbols:
            try:
                current = self.lifecycle_repo.get_state(symbol)
                if current in TERMINAL_STATES:
                    continue
                next_state = advance_state(current, SymbolState.CANDIDATE)
                if current != next_state:
                    self.lifecycle_repo.set_state(symbol, next_state)
            except Exception:
                logger.exception("Failed state transition for %s", symbol)
        return True

    def handle_transaction_created(self, payload: dict[str, Any]) -> bool:
        symbol = payload.get("symbol")
        if not symbol:
            return True
        self.forward_to_candidate(symbol, "transaction_created")
        return True

    def handle_symbol_activated(self, payload: dict[str, Any]) -> bool:
        symbol = payload.get("symbol")
        if not symbol:
            return True
        self.forward_to_candidate(symbol, "symbol_activated")
        return True

    def handle_symbol_deactivated(self, payload: dict[str, Any]) -> bool:
        symbol = payload.get("symbol")
        if not symbol:
            return True
        try:
            state = self.lifecycle_repo.get_state(symbol)
            if state in {SymbolState.CANDIDATE, SymbolState.PENDING_BACKFILL,
                         SymbolState.PRICES_LOADED, SymbolState.TA_READY}:
                self.lifecycle_repo.set_state(symbol, SymbolState.INACTIVE)
                logger.info("Deactivated symbol %s via event", symbol)
        except Exception:
            logger.exception("Failed to deactivate %s", symbol)
        return True

    def handle_prices_loaded(self, payload: dict[str, Any]) -> bool:
        symbol = payload.get("symbol")
        if not symbol:
            return True
        try:
            state = self.lifecycle_repo.get_state(symbol)
            if state in {SymbolState.CANDIDATE, SymbolState.PENDING_BACKFILL,
                         SymbolState.PRICES_LOADED}:
                next_state = advance_state(state, SymbolState.TA_READY)
                self.lifecycle_repo.set_state(symbol, next_state)
        except Exception:
            logger.exception("Failed state transition for %s after price load", symbol)

        # Trigger downstream analysis for this symbol
        try:
            self._spawn("news_monitor.py", ["--symbol", symbol, "--category", "stocks"])
            self._spawn("fundamental_data.py", ["--mode", "fetch", "--symbol", symbol])
        except Exception:
            logger.exception("Failed to trigger downstream jobs for %s", symbol)
        return True

    def handle_indicators_calculated(self, payload: dict[str, Any]) -> bool:
        symbol = payload.get("symbol")
        if not symbol:
            return True
        try:
            state = self.lifecycle_repo.get_state(symbol)
            if state in {SymbolState.PRICES_LOADED, SymbolState.TA_READY}:
                next_state = advance_state(state, SymbolState.ANALYSIS_ELIGIBLE)
                self.lifecycle_repo.set_state(symbol, next_state)
                self.publisher.publish_symbol_state(symbol, next_state, "indicators_calculated")
        except Exception:
            logger.exception("Failed state transition for %s after indicators", symbol)

        # Trigger LLM / Buffett-style qualitative analysis
        try:
            self._spawn("llm_analyzer.py", ["--table", "tenets", "--symbol", symbol])
        except Exception:
            logger.exception("Failed to trigger LLM analysis for %s", symbol)
        return True

    def forward_to_candidate(self, symbol: str, source: str) -> None:
        current = self.lifecycle_repo.get_state(symbol)
        if current in TERMINAL_STATES:
            return
        next_state = advance_state(current, SymbolState.CANDIDATE)
        if current != next_state:
            self.lifecycle_repo.set_state(symbol, next_state)

    def _claim(self, limit: int) -> list[tuple[str, str, dict[str, Any]]]:
        conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **self.mysql_config)
        try:
            conn.begin()
            cur = conn.cursor()
            cur.execute(
                "SELECT event_id, event_type, payload FROM event_queue "
                "WHERE status = 'pending' "
                "ORDER BY occurred_at ASC "
                "LIMIT %s FOR UPDATE SKIP LOCKED",
                (limit,),
            )
            rows = cur.fetchall()
            event_ids = [row['event_id'] for row in rows]
            if event_ids:
                placeholders = ",".join(["%s"] * len(event_ids))
                cur.execute(
                    "UPDATE event_queue SET status = 'running' "
                    "WHERE event_id IN (%s)" % placeholders,
                    event_ids,
                )
            conn.commit()
            return [(row['event_id'], row['event_type'], _safe_payload(row['payload'])) for row in rows]
        finally:
            conn.close()

    def _mark_complete(self, event_id: str) -> None:
        self._update_event(event_id, "completed")

    def _mark_failed(self, event_id: str) -> None:
        self._update_event(
            event_id,
            "failed",
            extra="UPDATE event_queue SET attempts = attempts + 1 WHERE event_id = %s",
        )

    def _update_event(self, event_id: str, status: str, extra: str = "") -> None:
        conn = pymysql.connect(**self.mysql_config)
        try:
            cur = conn.cursor()
            if extra:
                cur.execute(extra, (event_id,))
            cur.execute(
                "UPDATE event_queue SET status = %s, processed_at = NOW() WHERE event_id = %s",
                (status, event_id),
            )
            conn.commit()
        finally:
            conn.close()


def _safe_payload(raw: str | bytes | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        import ast
        import json

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": str(raw)}
    except Exception:
        return {"raw": str(raw)}
