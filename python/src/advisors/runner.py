"""Advisor runner: execute strategies for a given date and persist trades."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pymysql

REPO_ROOT = Path(__file__).resolve().parents[3]
for _cand in (str(REPO_ROOT), str(REPO_ROOT / "python" / "src")):
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

from python.src.database import get_connection as _get_connection
from advisors import (
    BuffettQualityStrategy,
    DividendGrowthStrategy,
    MomentumStrategy,
)
from advisors.base import AdvisorBase, Signal
from advisors.repository import AdvisorRepository

logger = logging.getLogger(__name__)

_STRATEGY_MAP: dict[str, type[AdvisorBase]] = {
    "buffett_quality": BuffettQualityStrategy,
    "dividend_growth": DividendGrowthStrategy,
    "momentum": MomentumStrategy,
}


def _load_config() -> dict[str, Any]:
    try:
        from python.config_loader import Config
    except Exception:
        return {}
    for candidate in (
        str(REPO_ROOT / "config.yaml"),
        "config.yaml",
    ):
        if Path(candidate).is_file():
            try:
                cfg = Config(candidate)
                return dict(getattr(cfg, "advisors", {}) or {})
            except Exception:
                break
    return {}


def get_connection() -> pymysql.connections.Connection:
    return _get_connection()


def run_advisor(
    db: pymysql.connections.Connection,
    repo: AdvisorRepository,
    advisor: dict[str, Any],
    run_date: date,
    dry_run: bool = False,
) -> None:
    slug = advisor["slug"]
    strategy_name = advisor.get("strategy") or "buffett_quality"
    schedule = advisor.get("schedule") or "daily"
    max_positions = int(advisor.get("max_positions") or 20)

    strategy_cls = _STRATEGY_MAP.get(strategy_name)
    if strategy_cls is None:
        logger.error("Unknown strategy '%s' for advisor %s", strategy_name, slug)
        return

    instance: AdvisorBase = strategy_cls(db, config={"schedule": schedule})
    instance.slug = slug

    if not instance.should_run_today(run_date):
        logger.info("Advisor %s is not eligible on %s (%s schedule)", slug, run_date, schedule)
        return

    user_id = int(advisor["id"])
    if repo.run_exists(user_id, run_date):
        logger.info("Advisor %s already has a run for %s; skipping", slug, run_date)
        return

    run_id = repo.create_run(user_id, run_date)
    instance.on_run_start(run_date)

    try:
        signals = instance.generate_signals(run_date, max_positions=max_positions)
    except Exception as exc:
        instance.on_run_error(run_date, exc)
        repo.update_run(run_id, status="failed", error_message=str(exc))
        return

    trades_executed = 0
    if not dry_run:
        for sig in signals:
            try:
                _persist_trade(db, sig, run_date)
                trades_executed += 1
            except Exception:
                logger.exception("Failed to persist trade for %s", sig.symbol)

    repo.update_run(
        run_id,
        status="completed",
        universe_size=len(instance.select_universe(run_date)),
        signals_generated=len(signals),
        trades_executed=trades_executed,
    )
    instance.on_run_complete(run_date, signals)


def _persist_trade(
    db: pymysql.connections.Connection,
    sig: Signal,
    trade_date: date,
) -> None:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO transactions
                (symbol, trade_date, type, quantity, price, total, commission, account_type, notes, source_file, created_at)
            VALUES (%s, %s, 'BUY', 1, 0, 0, 0, 'MARGIN', %s, 'advisor', NOW())
            """,
            (
                sig.symbol,
                trade_date,
                f"Advisor {sig.symbol} action={sig.action} weight={sig.weight:.2f} rank={sig.meta.get('rank', '')} confidence={sig.confidence:.2f}",
            ),
        )
    db.commit()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run advisor strategies for a date.")
    p.add_argument("--date", required=True, help="Run date YYYY-MM-DD")
    p.add_argument("--slug", default=None, help="Limit to a single advisor slug")
    p.add_argument("--dry-run", action="store_true", help="Do not persist trades")
    p.add_argument("--connection", default=None, help="Alias for --date")
    p.add_argument("--user", default=None, help="Alias for --slug")
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_parser().parse_args(argv)

    run_date_str = args.date or args.connection
    slug_filter = args.slug or args.user
    dry_run = args.dry_run

    try:
        run_date = date.fromisoformat(run_date_str)
    except (TypeError, ValueError):
        logger.error("Invalid --date: %s", run_date_str)
        return 2

    db = get_connection()
    repo = AdvisorRepository(db)
    advisors = repo.get_active_advisors()
    if slug_filter:
        advisors = [a for a in advisors if a["slug"] == slug_filter]

    if not advisors:
        logger.info("No active advisors found for filter=%s", slug_filter)
        return 0

    for adv in advisors:
        try:
            run_advisor(db, repo, adv, run_date, dry_run=dry_run)
        except Exception:
            logger.exception("Advisor %s crashed", adv["slug"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
