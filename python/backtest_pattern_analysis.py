#!/usr/bin/env python3
"""
backtest_pattern_analysis.py — Candlestick pattern win-rate analysis from backtest results.

Reads:
  backtest_runs
  backtest_trades
  backtest_trade_indicators
  stockprices

Groups trades by CDL_* tags found in backtest_trade_indicators.indicators JSON
and computes:
  - trade count
  - win rate %
  - average PnL (from SELL trades with forward returns)

Frequency: daily / weekly / monthly, filtered from backtest_runs.parameters.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from python.db_connector import get_connection as _get_connection


def get_connection():
    return _get_connection()


def load_trades(conn, frequency: str | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT r.id AS run_id, r.parameters,
               t.id AS trade_id, t.symbol, t.trade_type, t.trade_date, t.price, t.quantity, t.signal_reasons,
               ti.indicators
        FROM backtest_trades t
        JOIN backtest_runs r ON r.id = t.backtest_id
        LEFT JOIN backtest_trade_indicators ti ON ti.trade_id = t.id
    """
    params: list[Any] = []
    if frequency:
        query += " WHERE r.parameters LIKE %s"
        params.append(f'%"{frequency}"%')
    query += " ORDER BY t.trade_date ASC, t.id ASC"
    with conn.cursor(dictionary=True) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def cdl_tags_from_indicators(indicators: dict | str | None) -> list[str]:
    if not indicators:
        return []
    if isinstance(indicators, str):
        try:
            indicators = json.loads(indicators)
        except json.JSONDecodeError:
            return []
    if not isinstance(indicators, dict):
        return []
    tags = []
    for name, value in indicators.items():
        if not isinstance(name, str) or not name.startswith("CDL_"):
            continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if v == 0:
            continue
        direction = "BULLISH" if v > 0 else "BEARISH"
        tags.append(f"{name}_{direction}")
    return tags


def win_stats(conn, trades: list[dict[str, Any]]):
    by_pattern = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl_sum": 0.0})

    for row in trades:
        tags = cdl_tags_from_indicators(row.get("indicators"))
        if not tags:
            continue
        trade_date = row["trade_date"]
        if isinstance(trade_date, str):
            trade_date = datetime.strptime(trade_date, "%Y-%m-%d").date()

        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT close FROM stockprices
                WHERE symbol = %s AND price_date >= %s
                ORDER BY price_date ASC
                LIMIT 2
                """,
                (row["symbol"], trade_date),
            )
            prices = cur.fetchall()

        if len(prices) < 2:
            pnl = 0.0
        else:
            entry = float(row["price"])
            exit_ = float(prices[1]["close"])
            qty = int(row["quantity"] or 0)
            commission = 9.95
            if row["trade_type"] == "BUY":
                pnl = (exit_ - entry) * qty - commission
            else:
                pnl = (entry - exit_) * qty - commission

        for tag in tags:
            stats = by_pattern[tag]
            stats["trades"] += 1
            if pnl > 0:
                stats["wins"] += 1
            stats["pnl_sum"] += pnl

    return by_pattern


def fmt(stats: dict[str, Any]) -> str:
    lines = []
    lines.append(f"{'Pattern':<35} {'Trades':>7} {'Win%':>7} {'Avg PnL':>10}")
    lines.append("-" * 65)
    for tag in sorted(stats):
        s = stats[tag]
        wr = (s["wins"] / s["trades"] * 100) if s["trades"] else 0.0
        avg = s["pnl_sum"] / s["trades"] if s["trades"] else 0.0
        lines.append(f"{tag:<35} {s['trades']:>7} {wr:>6.1f}% {avg:>10.2f}")
    return "\n".join(lines)


def main() -> int:
    freq = sys.argv[1] if len(sys.argv) > 1 else None
    conn = get_connection()
    trades = load_trades(conn, freq)
    if not trades:
        print("No trades found.")
        conn.close()
        return 0
    stats = win_stats(conn, trades)
    print(f"\nFrequency: {freq or 'all'}")
    print(fmt(stats))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
