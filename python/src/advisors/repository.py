"""Repository for advisor lookups via regular users table.

Advisors are regular users with role='advisor'. Their strategy is stored
in user_settings (setting_key='advisor_strategy'). No advisor_accounts
table is used.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


class AdvisorRepository:
    def __init__(self, db: Any) -> None:
        self.db = db

    def get_active_advisors(self) -> list[dict[str, Any]]:
        sql = """
            SELECT u.id, u.username AS slug, u.display_name,
                   COALESCE(us.setting_value, 'buffett_quality') AS strategy
            FROM users u
            LEFT JOIN user_settings us ON us.user_id = u.id AND us.setting_key = 'advisor_strategy'
            WHERE u.role = 'advisor' AND u.is_active = 1
            ORDER BY u.id
        """
        with self.db.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def run_exists(self, user_id: int, run_date: date) -> bool:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT id FROM advisor_runs WHERE user_id = %s AND run_date = %s LIMIT 1",
                (user_id, run_date),
            )
            return cur.fetchone() is not None

    def create_run(self, user_id: int, run_date: date) -> int:
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO advisor_runs (user_id, run_date, status) VALUES (%s, %s, 'running')",
                (user_id, run_date),
            )
            self.db.commit()
            return int(cur.lastrowid)

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
        if status == "completed":
            sets.append("finished_at = NOW()")
        params.append(run_id)
        with self.db.cursor() as cur:
            cur.execute(
                f"UPDATE advisor_runs SET {', '.join(sets)} WHERE id = %s",
                params,
            )
            self.db.commit()
