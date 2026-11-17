#!/usr/bin/env python3
"""Cron queue processor for ksf_stockmarket.

Processes jobs stored in the ``event_queue`` table of the stockmarket MariaDB.

Subcommands
-----------
cancel-dupes   Cancel duplicate pending events. For every event_type that has
               more than one pending job, all but the most recent are marked
               cancelled (attempts incremented).
run            Claim and run pending events, up to --limit (default 5). Each
               claimed event is marked 'running', dispatched to its handler,
               then marked 'completed' or 'failed'.

Usage
-----
    python3 cron_queue.py cancel-dupes
    python3 cron_queue.py run --limit 5
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pymysql

REPO_ROOT = Path(__file__).resolve().parent
SRC_ROOT = REPO_ROOT / "python" / "src"
for _candidate in (str(REPO_ROOT), str(SRC_ROOT), str(REPO_ROOT / "python")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from config_loader import Config  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _get_db_config() -> dict[str, Any]:
    """Read the MariaDB connection details from config.yaml (no vault needed)."""
    cfg = Config(str(REPO_ROOT / "config.yaml"))
    return {
        "host": cfg.data.db_host,
        "port": int(getattr(cfg.data, "db_port", 3306)),
        "database": cfg.data.db_name,
        "user": cfg.data.db_user,
        "password": cfg.db_password or cfg.secrets.get("db_password") or os.environ.get(
            "DB_PASS", ""
        ),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }


class EventRepository:
    """Thin MariaDB-backed access to the event_queue table."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(**self.config)

    def list_pending(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT event_id, event_type, occurred_at "
                    "FROM event_queue WHERE status = 'pending' ORDER BY occurred_at ASC",
                )
                return cur.fetchall()
        finally:
            conn.close()

    def cancel(self, event_id: str) -> bool:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE event_queue SET status = 'cancelled', "
                    "attempts = attempts + 1, last_error = 'Cancelled as duplicate' "
                    "WHERE event_id = %s",
                    (event_id,),
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()

    def claim(self, limit: int, max_attempts: int = 5) -> list[dict[str, Any]]:
        """Mark up to `limit` pending events as 'running' and return them."""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT event_id, event_type, payload, occurred_at "
                    "FROM event_queue "
                    "WHERE status = 'pending' AND attempts <= %s "
                    "ORDER BY occurred_at ASC LIMIT %s FOR UPDATE",
                    (max_attempts, limit),
                )
                rows = cur.fetchall()
                event_ids = [r["event_id"] for r in rows]
                if event_ids:
                    placeholders = ",".join(["%s"] * len(event_ids))
                    cur.execute(
                        "UPDATE event_queue SET status = 'running' "
                        "WHERE event_id IN (%s)" % placeholders,
                        event_ids,
                    )
                    conn.commit()
            return rows
        finally:
            conn.close()

    def mark_completed(self, event_id: str) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE event_queue SET status = 'completed', processed_at = NOW() "
                    "WHERE event_id = %s",
                    (event_id,),
                )
                conn.commit()
        finally:
            conn.close()

    def mark_failed(self, event_id: str, error: str) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE event_queue SET status = 'failed', last_error = %s, "
                    "attempts = attempts + 1 WHERE event_id = %s",
                    (error[:5000], event_id),
                )
                conn.commit()
        finally:
            conn.close()

    def status_tally(self) -> dict[str, int]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, COUNT(*) AS c "
                    "FROM event_queue GROUP BY status"
                )
                return {r["status"]: int(r["c"]) for r in cur.fetchall()}
        finally:
            conn.close()

    def list_failed(self, limit: int = 10) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT event_id, event_type, occurred_at "
                    "FROM event_queue WHERE status = 'failed' "
                    "ORDER BY occurred_at DESC LIMIT %s",
                    (limit,),
                )
                return cur.fetchall()
        finally:
            conn.close()

    def retry(self, event_id: str) -> bool:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE event_queue SET status = 'pending', "
                    "last_error = '', attempts = 0 "
                    "WHERE event_id = %s",
                    (event_id,),
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()


class LifecycleWorker:
    """Execute an event by type, mimicking the existing lifecycle worker."""

    def __init__(self, repo: EventRepository) -> None:
        self.repo = repo
        self.db_config = repo.config

    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(**self.db_config)

    def _look_up_state(self, symbol: str) -> str | None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pipeline_state FROM symbol_master WHERE symbol = %s",
                    (symbol,),
                )
                row = cur.fetchone()
                return row["pipeline_state"] if row else None
        finally:
            conn.close()

    def _set_state(self, symbol: str, state: str) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE symbol_master SET pipeline_state = %s, last_state_transition = NOW() "
                    "WHERE symbol = %s",
                    (state, symbol),
                )
                conn.commit()
        finally:
            conn.close()

    def _spawn(self, script_name: str, args: list[str]) -> None:
        cmd = [sys.executable, str(REPO_ROOT / "python" / script_name), *args]
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

    def process(self, event_id: str, event_type: str, payload: dict[str, Any]) -> bool:
        handler = {
            "screener_symbols_ingested": self._handle_screener_symbols_ingested,
            "transaction_created": self._handle_transaction_created,
            "symbol_activated": self._handle_symbol_activated,
            "symbol_deactivated": self._handle_symbol_deactivated,
            "prices_loaded": self._handle_prices_loaded,
            "indicators_calculated": self._handle_indicators_calculated,
        }.get(event_type)
        if handler is None:
            logger.info("No handler for %s; marking complete", event_type)
            self.repo.mark_completed(event_id)
            return True
        try:
            ok = handler(payload)
            self.repo.mark_completed(event_id) if ok else self.repo.mark_failed(event_id, "handler returned False")
            return ok
        except Exception:
            logger.exception("Failed processing event %s", event_id)
            self.repo.mark_failed(event_id, "exception during process")
            return False

    def _get_symbol(self, payload: dict[str, Any]) -> str | None:
        return (payload or {}).get("symbol")

    def _handle_screener_symbols_ingested(self, payload: dict[str, Any]) -> bool:
        for symbol in (payload or {}).get("symbols", []) or []:
            try:
                state = self._look_up_state(symbol)
            except Exception:
                logger.exception("state lookup failed for %s", symbol)
                continue
            # Terminal / no-op handled by caller; best-effort transition here.
            if state:
                pass
        return True

    def _handle_transaction_created(self, payload: dict[str, Any]) -> bool:
        symbol = self._get_symbol(payload)
        if symbol:
            try:
                self._look_up_state(symbol)
            except Exception:
                logger.exception("state lookup failed for %s", symbol)
        return True

    def _handle_symbol_activated(self, payload: dict[str, Any]) -> bool:
        symbol = self._get_symbol(payload)
        if symbol:
            try:
                self._look_up_state(symbol)
            except Exception:
                logger.exception("state lookup failed for %s", symbol)
        return True

    def _handle_symbol_deactivated(self, payload: dict[str, Any]) -> bool:
        symbol = self._get_symbol(payload)
        if symbol:
            try:
                state = self._look_up_state(symbol)
                if state in {"CANDIDATE", "PENDING_BACKFILL", "PRICES_LOADED", "TA_READY"}:
                    self._set_state(symbol, "INACTIVE")
                    logger.info("Deactivated symbol %s via event", symbol)
            except Exception:
                logger.exception("Failed to deactivate %s", symbol)
        return True

    def _handle_prices_loaded(self, payload: dict[str, Any]) -> bool:
        symbol = self._get_symbol(payload)
        if not symbol:
            return False
        try:
            state = self._look_up_state(symbol)
            if state in {"CANDIDATE", "PENDING_BACKFILL", "PRICES_LOADED"}:
                self._set_state(symbol, "TA_READY")
                logger.info("State for %s advanced to TA_READY", symbol)
        except Exception:
            logger.exception("State transition failed for %s", symbol)

        try:
            self._spawn("news_monitor.py", ["--symbol", symbol, "--category", "stocks"])
            self._spawn("fundamental_data.py", ["--mode", "fetch", "--symbol", symbol])
        except Exception:
            logger.exception("Failed to trigger downstream jobs for %s", symbol)
        return True

    def _handle_indicators_calculated(self, payload: dict[str, Any]) -> bool:
        symbol = self._get_symbol(payload)
        if symbol:
            try:
                state = self._look_up_state(symbol)
                if state in {"PRICES_LOADED", "TA_READY"}:
                    self._set_state(symbol, "ANALYSIS_ELIGIBLE")
                    logger.info("State for %s advanced to ANALYSIS_ELIGIBLE", symbol)
            except Exception:
                logger.exception("State transition failed for %s", symbol)
        return True


def _cancel_duplicates_bulk(repo: EventRepository) -> int:
    """Cancel every pending event that is a duplicate of a more recent one.

    Keeps the newest event per event_type and marks the older ones cancelled.
    A single SQL statement, so this scales to large queues.
    """
    conn = repo._connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE event_queue e
                JOIN (
                    SELECT event_id
                    FROM (
                        SELECT event_id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY event_type
                                   ORDER BY occurred_at DESC, event_id DESC
                               ) AS rn
                        FROM event_queue
                        WHERE status = 'pending'
                    ) t
                    WHERE t.rn > 1
                ) dup ON e.event_id = dup.event_id
                SET e.status = 'cancelled',
                    e.attempts = e.attempts + 1,
                    e.last_error = 'Cancelled as duplicate'
                """,
            )
            conn.commit()
            return int(cur.rowcount)
    finally:
        conn.close()


def cmd_cancel_dupes(repo: EventRepository, args=None) -> int:
    logger.info("=== cancel-dupes ===")
    pending = repo.list_pending()
    if not pending:
        print("No pending jobs.")
        return 0

    total_pending = len(pending)
    cancelled = _cancel_duplicates_bulk(repo)
    remaining = len(repo.list_pending())
    print(f"Pending: {total_pending} | Remaining pending: {remaining} | Cancelled: {cancelled}")
    return 0


def cmd_run(repo: EventRepository, limit: int) -> int:
    logger.info("=== run --limit %s ===", limit)
    claimed = repo.claim(limit)
    if not claimed:
        print("Queue empty — nothing to retry.")
        return 0

    worker = LifecycleWorker(repo)
    results = []
    for event in claimed:
        event_id = event["event_id"]
        event_type = event["event_type"]
        try:
            payload = eval_payload(event.get("payload"))
        except Exception:
            payload = {}
        logger.info("Running %s (%s)", event_id, event_type)
        ok = worker.process(event_id, event_type, payload)
        results.append((event_id, event_type, "OK" if ok else "FAILED"))

    for event_id, event_type, status in results:
        print(f"{event_id} | {event_type} | {status}")
    return 0


def _append_alert(message: str) -> None:
    log_path = Path("/tmp/cron_alert.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(message)
        fh.write("\n")


def cmd_check(repo: EventRepository, args=None) -> int:
    logger.info("=== check ===")
    limit = args.limit if args else 10
    tally = repo.status_tally()
    pending = tally.get("pending", 0)
    running = tally.get("running", 0)
    failed = tally.get("failed", 0)
    completed = tally.get("completed", 0)
    cancelled = tally.get("cancelled", 0)
    print("status tally:")
    for status in ("pending", "running", "failed", "completed", "cancelled"):
        if status in tally:
            print(f"  {status}: {tally[status]}")
    print(f"PENDING={pending}")
    if pending or running or failed:
        _append_alert(
            "cron-queue failure check: pending=%s running=%s failed=%s completed=%s cancelled=%s"
            % (pending, running, failed, completed, cancelled)
        )
        print(">> ALERTS WRITTEN TO /tmp/cron_alert.log")
    else:
        print("No failures, no pending jobs, no running jobs — no alerts.")
    return 0


def cmd_retry(repo: EventRepository, args=None) -> int:
    logger.info("=== retry ===")
    limit = args.limit if args else 10
    failed = repo.list_failed(limit)
    if not failed:
        print("No failed jobs to retry.")
        return 0
    print(f"Retrying {len(failed)} failed job(s):")
    for event in failed:
        event_id = event["event_id"]
        ok = repo.retry(event_id)
        print(f"  {event_id} -> pending ({'OK' if ok else 'FAILED'})")
    claimed = repo.claim(limit)
    if not claimed:
        print("Queue empty after retry — nothing further to run.")
        return 0
    worker = LifecycleWorker(repo)
    results = []
    for event in claimed:
        event_id = event["event_id"]
        event_type = event["event_type"]
        try:
            payload = eval_payload(event.get("payload"))
        except Exception:
            payload = {}
        logger.info("Running %s (%s)", event_id, event_type)
        ok = worker.process(event_id, event_type, payload)
        results.append((event_id, event_type, "OK" if ok else "FAILED"))
    for event_id, event_type, status in results:
        print(f"{event_id} | {event_type} | {status}")
    return 0


def eval_payload(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        import json
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {"raw": str(raw)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cron queue processor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cancel = sub.add_parser("cancel-dupes", help="Cancel duplicate pending jobs")
    p_cancel.set_defaults(func=cmd_cancel_dupes)

    p_run = sub.add_parser("run", help="Run pending jobs")
    p_run.add_argument("--limit", type=int, default=5, help="Max events to run")
    p_run.set_defaults(func=cmd_run)

    p_check = sub.add_parser("check", help="Check the queue for failures")
    p_check.add_argument("--limit", type=int, default=10, help="Max informational rows")
    p_check.set_defaults(func=cmd_check)

    p_retry = sub.add_parser("retry", help="Retry failed jobs")
    p_retry.add_argument("--limit", type=int, default=10, help="Max failed jobs to retry")
    p_retry.set_defaults(func=cmd_retry)

    args = parser.parse_args(argv)
    repo = EventRepository(_get_db_config())
    if args.command == "run":
        return cmd_run(repo, args.limit)
    return args.func(repo, args)


if __name__ == "__main__":
    sys.exit(main())
