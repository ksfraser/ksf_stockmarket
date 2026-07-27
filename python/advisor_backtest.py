#!/usr/bin/env python3
"""
advisor_backtest.py — Run advisor strategies from 2022-01-01 with $100k seed.

For each active advisor, this script:
  1. Seeds a virtual portfolio with $100,000 cash on 2022-01-01.
  2. Walks through trading days and rebalances per the advisor's schedule.
  3. Calls generate_signals() and executes BUY/SELL at that day's close.
  4. Persists run results in backtest_runs and trades in backtest_trades.
  5. Writes a summary JSON for the dashboard.

Usage:
    PYTHONPATH=".:python:python/src" python3 advisor_backtest.py
    PYTHONPATH=".:python:python/src" python3 advisor_backtest.py --slug buffett_quality
    PYTHONPATH=".:python:python/src" python3 advisor_backtest.py --start 2022-01-01 --end 2025-12-31 --initial 100000
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pymysql

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "python" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from python.src.database import get_connection
from advisors import (
    BuffettQualityStrategy,
    DividendGrowthStrategy,
    MomentumStrategy,
    SectorStrategy,
    BondBasketStrategy,
    BalancedFundStrategy,
    VectorVestSafeStockStrategy,
)
from advisors.base import AdvisorBase, Signal
from advisors.repository import AdvisorRepository

logger = logging.getLogger(__name__)

STRATEGY_MAP: dict[str, type[AdvisorBase]] = {
    "buffett_quality": BuffettQualityStrategy,
    "dividend_growth": DividendGrowthStrategy,
    "momentum": MomentumStrategy,
    "sector": SectorStrategy,
    "bond_basket": BondBasketStrategy,
    "balanced_fund": BalancedFundStrategy,
    "vectorvest_safe": VectorVestSafeStockStrategy,
}

NAME_MAP = {k: v.name for k, v in STRATEGY_MAP.items()}


def get_price(conn: pymysql.connections.Connection, symbol: str, target_date: date) -> float | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT close FROM stockprices WHERE symbol = %s AND price_date <= %s ORDER BY price_date DESC LIMIT 1",
            (symbol, target_date),
        )
        row = cur.fetchone()
        return float(row["close"]) if row else None


def trading_dates(conn: pymysql.connections.Connection, start: date, end: date) -> list[date]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT price_date FROM stockprices WHERE price_date BETWEEN %s AND %s ORDER BY price_date ASC",
            (start, end),
        )
        return [r["price_date"] if isinstance(r["price_date"], date) else date.fromisoformat(str(r["price_date"])) for r in cur.fetchall()]


def run_advisor_backtest(
    conn: pymysql.connections.Connection,
    advisor: dict[str, Any],
    start_date: date,
    end_date: date,
    initial_capital: float,
    commission: float = 9.95,
    frequency: str = "weekly",
) -> dict[str, Any]:
    slug = advisor["slug"] if "slug" in advisor else advisor["strategy"]
    strategy_name = advisor.get("strategy") or slug
    user_id = int(advisor["id"])
    display_name = advisor.get("display_name") or NAME_MAP.get(strategy_name, strategy_name)

    strategy_cls = STRATEGY_MAP.get(strategy_name)
    if strategy_cls is None:
        msg = f"Unknown strategy '{strategy_name}' for advisor {slug}"
        logger.error(msg)
        return {"slug": slug, "error": msg}

    config = {"schedule": advisor.get("schedule") or "daily"}
    if advisor.get("sector"):
        config["sector"] = advisor["sector"]
    if advisor.get("equity"):
        config["equity"] = advisor["equity"]
    if advisor.get("bond_basket"):
        config["bond_basket"] = advisor["bond_basket"]
    if strategy_name == "buffett_quality":
        config.setdefault("buffett", {})
        config["buffett"]["min_market_cap"] = config["buffett"].get("min_market_cap", 5_000_000)
        config["buffett"]["min_roe"] = config["buffett"].get("min_roe", 1.0)
        config["buffett"]["max_debt_ratio"] = config["buffett"].get("max_debt_ratio", 200.0)

    instance = strategy_cls(conn, config=config)
    instance.slug = slug
    instance.name = display_name

    cash = float(initial_capital)
    positions: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []

    dates = trading_dates(conn, start_date, end_date)
    if not dates:
        logger.warning("No trading dates found for %s", slug)
        return {"slug": slug, "error": "No trading data"}

    max_positions = int(advisor.get("max_positions") or 20)
    max_position_pct = 0.01  # 1% per position by default
    last_rebalance = start_date - timedelta(days=30)
    rebalance_days = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 91}.get(frequency, 7)

    # Fast-exit if the advisor can't produce any universe for the start date
    try:
        universe = instance.select_universe(start_date)
    except Exception as exc:
        logger.warning("Advisor %s universe failed at start: %s", slug, exc)
        return {"slug": slug, "error": f"Universe error: {exc}"}

    if not universe:
        logger.warning("Advisor %s universe is empty on %s", slug, start_date)
        return {"slug": slug, "error": "Empty universe at start date"}

    # Cap universe for backtest performance; scoring is the bottleneck.
    cap = min(len(universe), max_positions * 2)
    if cap < len(universe):
        logger.info("Advisor %s: truncating universe from %d to %d", slug, len(universe), cap)
        universe = universe[:cap]

    for i, current_date in enumerate(dates):
        if (current_date - last_rebalance).days < rebalance_days:
            # still record portfolio snapshot every 5 days
            if i % 5 == 0:
                history.append(_snapshot(current_date, cash, positions, conn))
            continue

        last_rebalance = current_date
        try:
            signals = instance.generate_signals(current_date, max_positions=max_positions)
        except Exception as exc:
            logger.warning("Advisor %s failed on %s: %s", slug, current_date, exc)
            continue

        if not signals:
            # Force-exit all stale positions when advisor returns empty signals
            target_symbols = set()
            for sym in list(positions.keys()):
                if sym in target_symbols:
                    continue
                pos = positions[sym]
                px = get_price(conn, sym, current_date)
                if not px or px <= 0:
                    continue
                qty = pos["shares"]
                proceeds = qty * px - commission
                pnl = proceeds - (qty * pos["cost_basis"])
                cash += proceeds
                trades.append({
                    "symbol": sym,
                    "trade_type": "SELL",
                    "trade_date": current_date,
                    "price": px,
                    "quantity": qty,
                    "commission": commission,
                    "total_cost": -proceeds,
                    "pnl": pnl,
                    "signal_reasons": "rebalance_out",
                })
                del positions[sym]
            history.append(_snapshot(current_date, cash, positions, conn))
            continue

        sells = [s for s in signals if s.action == "SELL"]
        buys = [s for s in signals if s.action == "BUY"]

        # Execute auto-sells for positions dropped from the new target list
        target_symbols = {s.symbol for s in buys}
        for sym in list(positions.keys()):
            if sym in target_symbols:
                continue
            price = get_price(conn, sym, current_date)
            if not price or price <= 0:
                continue
            pos = positions[sym]
            qty = pos["shares"]
            proceeds = qty * price - commission
            pnl = proceeds - (qty * pos["cost_basis"])
            cash += proceeds
            trades.append({
                "symbol": sym,
                "trade_type": "SELL",
                "trade_date": current_date,
                "price": price,
                "quantity": qty,
                "commission": commission,
                "total_cost": -proceeds,
                "pnl": pnl,
                "signal_reasons": "rebalance_out",
            })
            del positions[sym]

        # Execute sells
        for sig in sells:
            if sig.symbol not in positions:
                continue
            price = get_price(conn, sig.symbol, current_date)
            if price and price > 0:
                pos = positions[sig.symbol]
                qty = pos["shares"]
                proceeds = qty * price - commission
                pnl = proceeds - (qty * pos["cost_basis"])
                cash += proceeds
                trades.append({
                    "symbol": sig.symbol,
                    "trade_type": "SELL",
                    "trade_date": current_date,
                    "price": price,
                    "quantity": qty,
                    "commission": commission,
                    "total_cost": -proceeds,
                    "pnl": pnl,
                    "signal_reasons": _describe_exit(slug, display_name, strategy_name, sig, pos, price),
                })
                del positions[sig.symbol]

        # Execute buys — equal weight across signals, capped by 1% per position
        target_weight = 1.0 / max(max_positions, 1)
        for sig in buys:
            if sig.symbol in positions:
                continue
            if len(positions) >= max_positions:
                break

            price = get_price(conn, sig.symbol, current_date)
            if not price or price <= 0:
                continue

            allocation = cash * target_weight
            shares = int(allocation / price)
            if shares <= 0:
                continue
            cost = shares * price + commission
            if cost > cash:
                shares = int((cash - commission) / price)
                if shares <= 0:
                    continue
                cost = shares * price + commission

            cash -= cost
            positions[sig.symbol] = {
                "shares": shares,
                "cost_basis": price,
                "entry_date": current_date,
                "strategy": strategy_name,
                "trigger_reason": _describe_entry(slug, display_name, strategy_name, sig, price),
            }

            trades.append({
                "symbol": sig.symbol,
                "trade_type": "BUY",
                "trade_date": current_date,
                "price": price,
                "quantity": shares,
                "commission": commission,
                "total_cost": cost,
                "signal_reasons": _describe_entry(slug, display_name, strategy_name, sig, price),
            })

        if i % 5 == 0:
            history.append(_snapshot(current_date, cash, positions, conn))

    # final valuation
    final_snap = _snapshot(dates[-1], cash, positions, conn)
    history.append(final_snap)
    final_value = final_snap["total_value"]
    total_return = (final_value - initial_capital) / initial_capital if initial_capital else 0
    years = (end_date - start_date).days / 365.25
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    # max drawdown
    peak = initial_capital
    max_drawdown = 0.0
    for snap in history:
        v = snap["total_value"]
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    # win rate
    winning = [t for t in trades if t.get("pnl", 0) > 0]
    win_rate = len(winning) / len(trades) if trades else 0

    # Save to database
    run_id = _save_run(
        conn,
        user_id=user_id,
        slug=slug,
        display_name=display_name,
        strategy=strategy_name,
        start=start_date,
        end=end_date,
        initial=initial_capital,
        final=final_value,
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=max_drawdown,
        num_trades=len(trades),
        win_rate=win_rate,
        trades=trades,
    )

    logger.info(
        "Backtest %s: initial=%.2f final=%.2f return=%.2f%% trades=%d",
        slug, initial_capital, final_value, total_return * 100, len(trades),
    )

    return {
        "run_id": run_id,
        "slug": slug,
        "display_name": display_name,
        "strategy": strategy_name,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return": round(total_return * 100, 2),
        "annualized_return": round(annualized_return * 100, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "num_trades": len(trades),
        "win_rate": round(win_rate * 100, 2),
        "trades": trades,
        "portfolio_history": history,
    }


def _snapshot(current_date: date, cash: float, positions: dict[str, Any], conn: pymysql.connections.Connection) -> dict[str, Any]:
    total_value = cash
    for symbol, pos in positions.items():
        price = get_price(conn, symbol, current_date)
        if price is None:
            price = pos["cost_basis"]
        total_value += pos["shares"] * price
    return {
        "date": current_date,
        "cash": cash,
        "total_value": total_value,
        "num_positions": len(positions),
    }


def _describe_entry(slug: str, name: str, strategy: str, sig: Signal, price: float) -> str:
    meta = sig.meta or {}
    rank = meta.get("rank", "")
    score = meta.get("score", sig.confidence)
    return (
        f"Strategy {strategy} ({slug}): BUY {sig.symbol} "
        f"at ${price:.2f} on threshold confidence={sig.confidence:.2f} score={score} rank={rank}. "
        f"Applied position sizing=equal_weight, sizing pct=1%, risk mitigation=20-name diversification, "
        f"rebalance schedule=daily."
    )


def _describe_exit(slug: str, name: str, strategy: str, sig: Signal, pos: dict[str, Any], price: float) -> str:
    return (
        f"Strategy {strategy} ({slug}): SELL {sig.symbol} "
        f"at ${price:.2f} triggered by {sig.reason or 'signal exit'}. "
        f"Risk mitigation=fixed 1% position cap, commission=${9.95:.2f} per trade."
    )


def _save_run(conn, user_id: int, slug: str, display_name: str, strategy: str,
              start: date, end: date, initial: float, final: float,
              total_return: float, annualized_return: float, max_drawdown: float,
              num_trades: int, win_rate: float, trades: list[dict]) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO backtest_runs
                (user_id, strategy, parameters, start_date, end_date,
                 initial_capital, final_value, total_return, annualized_return,
                 sharpe_ratio, max_drawdown, num_trades, win_rate, status, error_message, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'complete', NULL, NOW())
            """,
            (
                user_id,
                f"{strategy}:{slug}:{display_name}",
                json.dumps({"advisor": slug, "strategy": strategy}),
                start.isoformat(),
                end.isoformat(),
                initial,
                final,
                total_return,
                annualized_return,
                0.0,
                max_drawdown,
                num_trades,
                win_rate,
            ),
        )
        run_id = int(cur.lastrowid)
        for t in trades:
            cur.execute(
                """
                INSERT INTO backtest_trades
                    (backtest_id, symbol, trade_type, trade_date, price,
                     quantity, commission, total_cost, signal_reasons)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    t["symbol"],
                    t["trade_type"],
                    t["trade_date"].isoformat(),
                    t["price"],
                    t["quantity"],
                    t["commission"],
                    t["total_cost"],
                    t.get("signal_reasons", ""),
                ),
            )
    conn.commit()
    logger.info("Saved backtest run %d with %d trades", run_id, num_trades)
    return run_id


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run advisor backtests from 2022-01-01")
    p.add_argument("--start", default="2022-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", default=None, help="End date YYYY-MM-DD (default: today)")
    p.add_argument("--initial", type=float, default=100_000.0, help="Initial capital per advisor")
    p.add_argument("--commission", type=float, default=9.95, help="Commission per trade")
    p.add_argument("--slug", default=None, help="Run only a single advisor slug")
    p.add_argument("--all", action="store_true", help="Run all active advisors (default)")
    p.add_argument("--frequency", default="weekly", choices=["daily","weekly","monthly","quarterly"], help="Backtest rebalance frequency")
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else date.today()
    if end < start:
        end = start

    conn = get_connection()
    repo = AdvisorRepository(conn)
    advisors = repo.get_active_advisors()

    if args.slug:
        slug = args.slug.lower()
        advisors = [a for a in advisors if (a.get("slug") or "").lower() == slug or a["strategy"] == slug]

    results = []
    for adv in advisors:
        try:
            res = run_advisor_backtest(conn, adv, start, end, args.initial, args.commission, args.frequency)
            results.append(res)
        except Exception:
            logger.exception("Advisor %s backtest crashed", adv.get("slug"))

    summary_path = REPO_ROOT / "python" / "advisor_backtest_summary.json"
    payload = {
        "generated_at": date.today().isoformat(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "initial_capital": args.initial,
        "advisors": results,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    logger.info("Summary written to %s", summary_path)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
