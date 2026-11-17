"""Alert data-access layer (Repository).

Mirrors the price layer (``SQLitePriceRepository`` / ``YFinanceFetcher``): all SQL
against ``alert_queue`` / ``alert_responses`` lives here, and callers pass
``AlertDTO`` in / get dict rows out. This replaces the hand-rolled
``INSERT``/``UPDATE`` statements that were duplicated across
``detection_triggers.py``, ``stock_alert_detection.py``, ``cron_discord_relay.py``
and ``hermes_alert_monitor.py``.

Two backends, selected at construction:

* ``sqlite_mode=True``  -> the ephemeral SQLite ``ANALYTICS_DB`` (the same DB that
  holds ``price_intraday``; the EOD job syncs it to MariaDB).
* ``sqlite_mode=False`` -> MariaDB ``ksfraser_stock_market.alert_queue``.

Connection config is injected (``mariadb_config`` / ``sqlite_path``) so callers
keep their existing credential source — this layer never hardcodes secrets.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from typing import Optional

from .alert_dto import AlertDTO
from .connection import DataSource


def _json_default(o):
    """JSON fallback for non-serializable scalar types (notably numpy scalars).

    numpy scalar types (``bool_``, ``int64``, ``float64`` ...) and arrays leak
    into alert payloads from the detection math. ``json.dumps`` rejects them
    with ``TypeError: Object of type bool_ is not JSON serializable``. We coerce
    numpy scalars via their ``.item()`` method and fall back to ``str()`` for
    anything else rather than dropping the whole alert.
    """
    item = getattr(o, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    if isinstance(o, (tuple, set, frozenset)):
        return list(o)
    return str(o)


def _make_alert_id(alert_type: str, symbol: str) -> str:
    return f"{alert_type[:3]}-{symbol}-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _default_mariadb_config() -> dict:
    from config.db import get_mariadb_config

    return get_mariadb_config()


class AlertRepository:
    """Owns all reads/writes for the alert_queue / alert_responses tables."""

    def __init__(
        self,
        sqlite_mode: bool = False,
        sqlite_path: str = None,
        mariadb_config: dict = None,
    ):
        self.sqlite_mode = sqlite_mode
        if sqlite_mode:
            if sqlite_path:
                self.sqlite_path = sqlite_path
            else:
                from config.paths import ANALYTICS_DB

                self.sqlite_path = str(ANALYTICS_DB)
        else:
            self.mysql = mariadb_config or _default_mariadb_config()

    # ------------------------------------------------------------------ #
    # connection helpers
    # ------------------------------------------------------------------ #
    def _connect(self):
        if self.sqlite_mode:
            return DataSource.sqlite_connection(self.sqlite_path)
        return DataSource.mariadb_connection(self.mysql)

    @staticmethod
    def _placeholders(sql: str) -> str:
        """Swap MariaDB ``%s`` placeholders for SQLite ``?``."""
        return sql.replace("%s", "?")

    # ------------------------------------------------------------------ #
    # writes
    # ------------------------------------------------------------------ #
    def save(self, dto: AlertDTO, dedup_window_s: int = 300) -> Optional[str]:
        """Persist an alert.

        Returns ``None`` if a duplicate (same symbol + alert_type, still
        pending/processing) was raised within ``dedup_window_s`` seconds — this
        prevents alert storms. Otherwise returns the new alert id.
        """
        if self.get_open_for_symbol(dto.symbol, dto.alert_type, dedup_window_s) is not None:
            return None
        if not dto.alert_id:
            dto.alert_id = _make_alert_id(dto.alert_type, dto.symbol)
        payload = dto.with_id_in_payload()
        last_err: Exception | None = None
        # Retry on transient SQLite write contention. In WAL mode a writer is
        # only ever blocked by another writer (e.g. a concurrent price_intraday
        # sync writing to the same multiplexed analysis_results.db). Rather than
        # abort the whole detection run and lose the alert, back off briefly and
        # retry. This keeps unattended intraday cron runs resilient.
        for attempt in range(1, 6):
            conn = self._connect()
            try:
                cur = conn.cursor()
                if self.sqlite_mode:
                    cur.execute(
                        """INSERT OR REPLACE INTO alert_queue
                           (id, alert_type, symbol, severity, payload,
                            status, request_llm_analysis)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (dto.alert_id, dto.alert_type, dto.symbol, dto.severity,
                         json.dumps(payload, default=_json_default), dto.status, dto.request_llm_analysis),
                    )
                else:
                    cur.execute(
                        """INSERT INTO alert_queue
                           (id, alert_type, symbol, severity, payload,
                            status, request_llm_analysis)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (dto.alert_id, dto.alert_type, dto.symbol, dto.severity,
                         json.dumps(payload, default=_json_default), dto.status, dto.request_llm_analysis),
                    )
                conn.commit()
                return dto.alert_id
            except sqlite3.OperationalError as e:
                last_err = e
                conn.close()
                if attempt < 5 and "locked" in str(e).lower():
                    time.sleep(0.2 * attempt)
                    continue
                raise
            finally:
                # Only close here if we didn't already close on the retry path.
                if "conn" in locals() and conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
            break
        if last_err:
            raise last_err
        return dto.alert_id

    def get_open_for_symbol(
        self, symbol: str, alert_type: str, window_s: int = 300
    ) -> Optional[AlertDTO]:
        """Return a lightweight ``AlertDTO`` for an open (pending/processing)
        alert of the same symbol+type raised within ``window_s``, else None."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            sql = """SELECT id, created_at FROM alert_queue
                     WHERE symbol=%s AND alert_type=%s
                       AND status IN ('pending','processing')
                     ORDER BY created_at DESC LIMIT 1"""
            if self.sqlite_mode:
                cur.execute(self._placeholders(sql), (symbol, alert_type))
            else:
                cur.execute(sql, (symbol, alert_type))
            row = cur.fetchone()
            if not row:
                return None
            last_ts = row[1]
            # SQLite stores TIMESTAMP as text; MariaDB returns a datetime. Coerce
            # so the window check works on both backends.
            if isinstance(last_ts, str):
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                    try:
                        last_ts = datetime.strptime(last_ts, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    try:
                        last_ts = datetime.fromisoformat(last_ts)
                    except ValueError:
                        last_ts = None
            age = (datetime.now() - last_ts).total_seconds() if isinstance(last_ts, datetime) else 9999
            if age < window_s:
                return AlertDTO(
                    alert_id=row[0], alert_type=alert_type, symbol=symbol,
                    severity="", payload={},
                )
            return None
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # readers (return raw dict-like rows to keep caller diffs tiny)
    # ------------------------------------------------------------------ #
    def fetch_pending(
        self, notify_discord: int = 1, max_tries: int = 3, limit: int = 1
    ) -> Optional[dict]:
        """Lock + pop a single ready job (MariaDB ``FOR UPDATE SKIP LOCKED``).
        Returns a dict row with at least ``id`` and ``payload``."""
        conn = self._connect()
        try:
            if self.sqlite_mode:
                cur = conn.cursor()
                cur.execute(
                    """SELECT id, payload FROM alert_queue
                       WHERE status='pending'
                       ORDER BY created_at ASC LIMIT ?""",
                    (limit,),
                )
            else:
                import pymysql

                cur = conn.cursor(pymysql.cursors.DictCursor)
                cur.execute(
                    """SELECT id, payload FROM alert_queue
                       WHERE status='pending' AND try_count < %s
                       ORDER BY created_at ASC LIMIT %s
                       FOR UPDATE SKIP LOCKED""",
                    (max_tries, limit),
                )
            return cur.fetchone()
        finally:
            conn.close()

    def get_pending(self, limit: int = 20) -> list:
        """All pending alerts requesting LLM analysis (hermes_alert_monitor)."""
        conn = self._connect()
        try:
            if self.sqlite_mode:
                cur = conn.cursor()
                cur.execute(
                    """SELECT * FROM alert_queue
                       WHERE status='pending' AND request_llm_analysis=1
                       ORDER BY created_at ASC LIMIT ?""",
                    (limit,),
                )
                return [dict(r) for r in cur.fetchall()]
            import pymysql

            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute(
                """SELECT * FROM alert_queue
                   WHERE status='pending' AND request_llm_analysis=1
                   ORDER BY created_at ASC LIMIT %s""",
                (limit,),
            )
            return cur.fetchall()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def mark_processing(self, alert_id: str) -> bool:
        return self._exec(
            "UPDATE alert_queue SET status='processing' "
            "WHERE id=%s AND status='pending'",
            (alert_id,),
        )

    def mark_completed(self, alert_id: str) -> None:
        self._exec("UPDATE alert_queue SET status='completed' WHERE id=%s", (alert_id,))

    def mark_failed(self, alert_id: str, error: str = None) -> None:
        self._exec("UPDATE alert_queue SET status='failed' WHERE id=%s", (alert_id,))

    def mark_reviewed(self, alert_id: str, ok: bool) -> None:
        status = "completed" if ok else "failed"
        if self.sqlite_mode:
            self._exec("UPDATE alert_queue SET status=%s WHERE id=%s", (status, alert_id))
        else:
            self._exec(
                "UPDATE alert_queue SET status=%s, reviewed_at=NOW() WHERE id=%s",
                (status, alert_id),
            )

    def save_response(self, alert_id: str, response_text: str) -> None:
        if self.sqlite_mode:
            self._exec(
                "INSERT INTO alert_responses (alert_id, response_text) VALUES (?, ?)",
                (alert_id, response_text),
            )
        else:
            self._exec(
                "INSERT INTO alert_responses (alert_id, response_text) VALUES (%s, %s)",
                (alert_id, response_text),
            )

    def purge_stale_jobs(self, days: int = 7) -> int:
        """Delete failed jobs that exhausted retries and are older than ``days``.
        Returns the number of rows removed."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            if self.sqlite_mode:
                cur.execute(
                    "DELETE FROM alert_queue WHERE status='failed' "
                    "AND created_at < datetime('now', ? || ' days')",
                    (f"-{days}",),
                )
            else:
                cur.execute(
                    "DELETE FROM alert_queue WHERE status='failed' "
                    "AND try_count >= 3 AND created_at < NOW() - INTERVAL %s DAY",
                    (days,),
                )
            conn.commit()
            return getattr(cur, "rowcount", 0)
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # internal
    # ------------------------------------------------------------------ #
    def _exec(self, sql: str, params: tuple) -> bool:
        if self.sqlite_mode:
            sql = self._placeholders(sql)
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            return getattr(cur, "rowcount", 0) > 0
        finally:
            conn.close()


if __name__ == "__main__":
    import os
    import tempfile

    tmp = os.path.join(tempfile.mkdtemp(), "alert_test.db")
    repo = AlertRepository(sqlite_mode=True, sqlite_path=tmp)
    conn = repo._connect()
    try:
        conn.executescript(
            """
            CREATE TABLE alert_queue (
                id VARCHAR(64) PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                alert_type VARCHAR(50),
                symbol VARCHAR(20),
                severity TEXT,
                payload JSON,
                status TEXT DEFAULT 'pending',
                request_llm_analysis INTEGER DEFAULT 1,
                try_count INTEGER DEFAULT 0
            );
            CREATE TABLE alert_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_text TEXT
            );
            """
        )
    finally:
        conn.close()

    # save
    a = AlertDTO(alert_id="", alert_type="volume_spike", symbol="RY.TO",
                 severity="high", payload={"x": 1})
    id1 = repo.save(a)
    assert id1 and id1.startswith("vol-RY.TO-"), id1
    # dedup within window returns None
    assert repo.save(AlertDTO(alert_id="", alert_type="volume_spike", symbol="RY.TO",
                              severity="high", payload={"x": 2})) is None
    # different symbol/type is fine
    id2 = repo.save(AlertDTO(alert_id="", alert_type="volume_spike", symbol="SPY",
                             severity="med", payload={"x": 3}))
    assert id2
    # fetch_pending + lifecycle
    job = repo.fetch_pending()
    assert job["id"] == id1, job
    assert repo.mark_processing(id1) is True
    repo.save_response(id1, "looks real")
    repo.mark_completed(id1)
    # get_pending excludes completed
    pending = repo.get_pending()
    assert all(r["id"] != id1 for r in pending), pending
    assert any(r["id"] == id2 for r in pending), pending
    print("AlertRepository self-test OK: save/dedup/fetch/lifecycle all pass")
