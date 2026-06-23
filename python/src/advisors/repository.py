"""Repository for advisor_accounts and advisor_runs."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


class AdvisorRepository:
    def __init__(self, db: Any, table_prefix: str = "") -> None:
        self.db = db
        self.table_prefix = table_prefix

    def _t(self, name: str) -> str:
        return f"{self.table_prefix}{name}"

    def get_active_advisors(self) -> list[dict[str, Any]]:
        with self.db.cursor() as cur:
            cur.execute(
                f"SELECT a.id, a.user_id, a.slug, a.strategy, u.username "
                f"FROM {self._t('advisor_accounts')} a "
                "JOIN users u ON u.id = a.user_id "
                "WHERE a.is_active = 1"
            )
            return cur.fetchall()

    def get_advisor_by_slug(self, slug: str) -> dict[str, Any] | None:
        with self.db.cursor() as cur:
            cur.execute(
                f"SELECT a.id, a.user_id, a.slug, a.strategy, u.username "
                f"FROM {self._t('advisor_accounts')} a "
                "JOIN users u ON u.id = a.user_id "
                "WHERE a.slug = %s AND a.is_active = 1",
                (slug,),
            )
            return cur.fetchone()

    def run_exists(self, advisor_id: int, run_date: date) -> bool:
        with self.db.cursor() as cur:
            cur.execute(
                f"SELECT id FROM {self._t('advisor_runs')} WHERE advisor_id = %s AND run_date = %s",
                (advisor_id, run_date),
            )
            return cur.fetchone() is not None

    def create_run(self, advisor_id: int, run_date: date) -> int:
        with self.db.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self._t('advisor_runs')} (advisor_id, run_date, status) "
                "VALUES (%s, %s, 'running')",
                (advisor_id, run_date),
            )
            return cur.lastrowid

    def update_run(
        self,
        run_id: int,
        *,
        status: str | None = None,
        universe_size: int | None = None,
        signals_generated: int | None = None,
        trades_executed: int | None = None,
        error_message: str | None = None,
    ) -> None:
        sets: list[str] = []
        params: list[Any] = []
        if status is not None:
            sets.append("status = %s")
            params.append(status)
        if universe_size is not None:
            sets.append("universe_size = %s")
            params.append(universe_size)
        if signals_generated is not None:
            sets.append("signals_generated = %s")
            params.append(signals_generated)
        if trades_executed is not None:
            sets.append("trades_executed = %s")
            params.append(trades_executed)
        if error_message is not None:
            sets.append("error_message = %s")
            params.append(error_message)
        if status in {"completed", "failed", "skipped"}:
            sets.append("finished_at = NOW()")
        params.append(run_id)
        with self.db.cursor() as cur:
            cur.execute(
                f"UPDATE {self._t('advisor_runs')} SET {', '.join(sets)} WHERE id = %s",
                params,
            )
