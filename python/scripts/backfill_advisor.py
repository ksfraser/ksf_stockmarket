#!/usr/bin/env python3
"""Backfill live advisor portfolio/transactions from historical strategy runs.

Usage:
    PYTHONPATH=".:python:python/src" python3 scripts/backfill_advisor.py \
        --slug buffett_quality --start 2022-01-01 --end 2025-07-14 --initial 100000
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pymysql

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "python" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from python.src.database import get_connection
from advisors import BuffettQualityStrategy
from advisors.executor import AdvisorExecutor
from advisors.base import Signal

logger = logging.getLogger(__name__)


def get_advisor(db: pymysql.connections.Connection, slug: str) -> dict[str, Any]:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.username AS slug, u.display_name,
                   COALESCE(us.setting_value, 'buffett_quality') AS strategy,
                   COALESCE(sector.setting_value, '') AS sector,
                   COALESCE(equity.setting_value, '') AS equity,
                   COALESCE(bonds.setting_value, '') AS bond_basket
            FROM users u
            LEFT JOIN user_settings us ON us.user_id = u.id AND us.setting_key = 'advisor_strategy'
            LEFT JOIN user_settings sector ON sector.user_id = u.id AND sector.setting_key = 'advisor_sector'
            LEFT JOIN user_settings equity ON equity.user_id = u.id AND equity.setting_key = 'advisor_equity'
            LEFT JOIN user_settings bonds ON bonds.user_id = u.id AND bonds.setting_key = 'advisor_bonds'
            WHERE u.role = 'advisor' AND u.username = %s
            LIMIT 1
            """,
            (slug,),
        )
        row = cur.fetchone()
        return dict(row) if row else {}


def seed_initial_cash(db: pymysql.connections.Connection, user_id: int,
                      initial_capital: float, run_date: date) -> None:
    """Create an opening cash position + transaction if none exist."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM transactions WHERE user_id = %s AND symbol = 'CASH-CAD' AND type = 'BUY' LIMIT 1",
            (user_id,),
        )
        if cur.fetchone():
            return

        cur.execute(
            """
            INSERT INTO transactions
                (user_id, symbol, trade_date, type, quantity, price, total, commission,
                 account_type, notes, source_file, created_at)
            VALUES (%s, 'CASH-CAD', %s, 'BUY', 1, %s, %s, 0.00, 'MARGIN',
                    'Initial advisor backfill seed', 'backfill_advisor', NOW())
            """,
            (user_id, run_date.isoformat(), initial_capital, initial_capital),
        )
        cur.execute(
            """
            INSERT INTO portfolio
                (user_id, symbol, price_symbol, account_type, shares, cost_basis,
                 cost_basis_total, currency, entry_date, strategy, notes, updated_at)
            VALUES (%s, 'CASH-CAD', 'CASH-CAD', 'MARGIN', 1, 1.0, %s, 'CAD', %s,
                    'CASH', 'Initial advisor backfill seed', NOW())
            """,
            (user_id, initial_capital, run_date.isoformat()),
        )
    db.commit()
    logger.info("Seeded CASH-CAD position for user %s", user_id)


def persist_trade(db: pymysql.connections.Connection, user_id: int,
                  trade: dict[str, Any]) -> None:
    """Persist one trade into transactions + update portfolio."""
    symbol = trade["symbol"]
    trade_type = trade["trade_type"]
    trade_date = trade["trade_date"] if isinstance(trade["trade_date"], date) else date.fromisoformat(str(trade["trade_date"]))
    price = float(trade["price"])
    quantity = int(trade["quantity"])
    commission = float(trade["commission"])
    total = float(trade["total_cost"])

    with db.cursor() as cur:
        # Use a more informative note for advisor trades
        notes = f"Advisor backfill {trade.get('signal_reasons', '')}"

        cur.execute(
            """
            INSERT INTO transactions
                (user_id, symbol, trade_date, type, quantity, price, total, commission,
                 account_type, notes, source_file, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MARGIN', %s, 'backfill_advisor', NOW())
            """,
            (user_id, symbol, trade_date.isoformat(), trade_type, quantity, price,
             total, commission, notes),
        )

        if trade_type == "BUY":
            cost_basis_total = quantity * price
            cur.execute(
                """
                INSERT INTO portfolio
                    (user_id, symbol, price_symbol, account_type, shares, cost_basis,
                     cost_basis_total, currency, entry_date, strategy, notes, updated_at)
                VALUES (%s, %s, %s, 'MARGIN', %s, %s, %s, 'CAD', %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    shares = shares + VALUES(shares),
                    cost_basis_total = cost_basis_total + VALUES(cost_basis_total),
                    updated_at = NOW()
                """,
                (user_id, symbol, symbol, quantity, price, cost_basis_total,
                 trade_date.isoformat(), "advisor", notes),
            )
        elif trade_type == "SELL":
            cur.execute(
                "SELECT id, shares, cost_basis FROM portfolio WHERE user_id = %s AND symbol = %s AND account_type = 'MARGIN'",
                (user_id, symbol),
            )
            existing = cur.fetchone()
            if existing:
                new_shares = max(0, int(existing["shares"]) - quantity)
                if new_shares <= 0:
                    cur.execute(
                        "DELETE FROM portfolio WHERE id = %s",
                        (existing["id"],),
                    )
                else:
                    cur.execute(
                        "UPDATE portfolio SET shares = %s, updated_at = NOW() WHERE id = %s",
                        (new_shares, existing["id"]),
                    )

    db.commit()


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Backfill advisor portfolio from strategy history")
    p.add_argument("--slug", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--initial", type=float, default=100_000.0)
    p.add_argument("--max-positions", type=int, default=6)
    args = p.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    db = get_connection()
    try:
        advisor = get_advisor(db, args.slug)
        if not advisor:
            logger.error("Advisor %s not found", args.slug)
            return 1

        user_id = int(advisor["id"])
        strategy_name = advisor.get("strategy") or args.slug

        config = {"schedule": "daily", "table_prefix": ""}
        if strategy_name == "buffett_quality":
            config.setdefault("buffett", {})
            config["buffett"]["min_market_cap"] = 5_000_000
            config["buffett"]["min_roe"] = 1.0
            config["buffett"]["max_debt_ratio"] = 200.0

        from advisors import STRATEGY_MAP  # strategy map is module-level
        strategy_cls = STRATEGY_MAP.get(strategy_name)
        if strategy_cls is None:
            logger.error("Unknown strategy %s", strategy_name)
            return 1

        strategy = strategy_cls(db, config=config)
        strategy.slug = args.slug
        strategy.name = advisor.get("display_name") or args.slug

        seed_initial_cash(db, user_id, args.initial, start)

        executor = AdvisorExecutor(strategy, config=config)
        result = executor.run(db, user_id, start, end,
                               initial_capital=args.initial,
                               max_positions=args.max_positions)

        if "error" in result:
            logger.error("Executor error: %s", result["error"])
            return 1

        for trade in result["trades"]:
            persist_trade(db, user_id, trade)

        summary = result["summary"]
        logger.info(
            "Backfill %s complete: trades=%d win_rate=%.1f%% total_return=%.2f%%",
            args.slug,
            summary["num_trades"],
            summary["win_rate_pct"],
            summary["total_return_pct"],
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run())
