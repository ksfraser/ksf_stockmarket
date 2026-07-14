#!/usr/bin/env python3
"""
populate_analyst_ratings.py — Enrich analyst ratings from yfinance.

Priority order per run:
  1. Symbols currently held in portfolios
  2. Symbols present in screener results
  3. Remaining known symbols from fundamentals

Writes to analyst_ratings, analyst_recommendations, and analyst_targets.
"""

from __future__ import annotations

import json
import time
from datetime import date
from typing import Any

from python.db_connector import get_connection
from python.symbol_resolver import resolve_for_yfinance
import yfinance as yf

LIMIT_PER_RUN = 1000
SLEEP_BETWEEN = 0.28


def load_symbols_prioritized() -> list[str]:
    db = get_connection()
    cur = db.cursor()
    seen: set[str] = set()
    ordered: list[str] = []

    def add(symbols: list[str]) -> None:
        for sym in symbols:
            if sym and sym not in seen:
                seen.add(sym)
                ordered.append(sym)

    cur.execute("SELECT DISTINCT symbol FROM portfolio WHERE symbol IS NOT NULL AND symbol <> ''")
    add([r["symbol"] for r in cur.fetchall()])

    cur.execute("SELECT DISTINCT symbol FROM tradingview_screener_results WHERE symbol IS NOT NULL AND symbol <> ''")
    add([r["symbol"] for r in cur.fetchall()])

    cur.execute("SELECT symbol FROM fundamentals GROUP BY symbol ORDER BY COUNT(*) DESC")
    add([r["symbol"] for r in cur.fetchall()])

    cur.close()
    db.close()
    return ordered[:LIMIT_PER_RUN]


def resolve_ticker(symbol: str) -> str | None:
    try:
        resolved = resolve_for_yfinance(symbol)
        if resolved:
            return resolved
    except Exception:
        pass
    return symbol if "." in symbol or len(symbol) <= 5 else None


def safe_date(v):
    if v is None:
        return None
    if hasattr(v, "date"):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except Exception:
        return None


def already_has_recs(conn: Any, symbol: str) -> bool:
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM analyst_recommendations WHERE symbol = %s LIMIT 1", (symbol,))
        return cur.fetchone() is not None
    finally:
        cur.close()


def populate_recommendations(conn: Any, symbol: str, recs: Any) -> int:
    if recs is None or recs.empty:
        return 0
    cur = conn.cursor()
    count = 0
    for _, row in recs.iterrows():
        rec_date = safe_date(row.name[0] if hasattr(row.name, "__getitem__") else row.name)
        if not rec_date:
            continue
        try:
            cur.execute(
                """
                INSERT IGNORE INTO analyst_recommendations (symbol, firm, grade, price_target, action, rec_date)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    symbol,
                    str(row.get("Firm", "") or "") or "Unknown",
                    row.get("To Grade") or row.get("Grade"),
                    float(row.get("Price Target")) if row.get("Price Target") is not None else None,
                    str(row.get("Action")) or "",
                    rec_date,
                ),
            )
            count += 1
        except Exception:
            pass
    conn.commit()
    cur.close()
    return count


def populate_price_targets(conn: Any, symbol: str, price_targets: Any, info: dict) -> int:
    if not price_targets:
        return 0
    cur = conn.cursor()
    try:
        current = price_targets.get("current") if isinstance(price_targets, dict) else None
        cur.execute(
            """
            INSERT INTO analyst_targets (ticker, date, target_price, current_price, recommendation, source)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE target_price=VALUES(target_price), current_price=VALUES(current_price), source=VALUES(source)
            """,
            (
                symbol,
                date.today(),
                float(current) if current is not None else None,
                info.get("currentPrice"),
                info.get("recommendationKey"),
                "yfinance",
            ),
        )
        return 1
    except Exception:
        return 0
    finally:
        conn.commit()
        cur.close()


def run() -> None:
    symbols = load_symbols_prioritized()
    print(f"Priority list: {len(symbols)} symbols")
    processed = 0
    total_records = 0
    skipped = 0
    for idx, original_symbol in enumerate(symbols, 1):
        ticker = resolve_ticker(original_symbol)
        if not ticker:
            skipped += 1
            continue
        try:
            tk = yf.Ticker(ticker)
            recs = getattr(tk, "recommendations", None)
            price_targets = getattr(tk, "analyst_price_targets", None)
            info = tk.info or {}
            conn = get_connection()
            if already_has_recs(conn, original_symbol):
                skipped += 1
                conn.close()
                time.sleep(SLEEP_BETWEEN)
                continue
            rec_count = populate_recommendations(conn, original_symbol, recs)
            populate_price_targets(conn, original_symbol, price_targets, info)
            conn.close()
            total_records += rec_count
            processed += 1
            if idx % 50 == 0:
                print(f"  processed {idx}/{len(symbols)} — recs added: {total_records}")
        except Exception as exc:
            skipped += 1
            if idx % 50 == 0:
                print(f"  {original_symbol}: {type(exc).__name__}: {exc}")
        time.sleep(SLEEP_BETWEEN)

    print(f"Done. Processed {processed} symbols, skipped {skipped}, recs added {total_records}.")


if __name__ == "__main__":
    run()
