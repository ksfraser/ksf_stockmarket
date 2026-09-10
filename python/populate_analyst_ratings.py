#!/usr/bin/env python3
"""
populate_analyst_ratings.py — Enrich analyst ratings from yfinance.

Priority order per run:
  1. Symbols currently held in portfolios
  2. Symbols present in screener results
  3. Remaining known symbols from fundamentals

Writes to analyst_ratings, analyst_recommendations, and analyst_targets.

DB handling (refactored):
  * ONE database connection is opened for the whole run and reused — we no
    longer open/close a connection per symbol.
  * Recommendation and price-target rows are accumulated and written with a
    single multi-row executemany() per flush ("insert multiple rows at a time")
    instead of one INSERT per row.
  * Commits happen every ANALYST_COMMIT_EVERY symbols (default 25), not once per
    symbol, so the run uses far fewer transactions. The job is resumable via
    already_has_recs(), so an uncommitted batch that is lost to a budget/kill
    timeout is simply re-fetched and re-upserted on the next run (idempotent).
"""

from __future__ import annotations

import os
import time
from datetime import date
from typing import Any

from python.db_connector import get_connection
from python.src.symbol_resolver import resolve_for_yfinance
import yfinance as yf

LIMIT_PER_RUN = 1000
SLEEP_BETWEEN = 0.28

# Tunables (env-overridable)
REC_BATCH = int(os.getenv("ANALYST_REC_BATCH", "500"))      # flush recommendations once this many rows accumulate
SYM_COMMIT = int(os.getenv("ANALYST_COMMIT_EVERY", "25"))    # commit every N symbols


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
    add([r[0] for r in cur.fetchall()])

    cur.execute("SELECT DISTINCT symbol FROM tradingview_screener_results WHERE symbol IS NOT NULL AND symbol <> ''")
    add([r[0] for r in cur.fetchall()])

    cur.execute("SELECT symbol FROM fundamentals GROUP BY symbol ORDER BY COUNT(*) DESC")
    add([r[0] for r in cur.fetchall()])

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


def run() -> None:
    symbols = load_symbols_prioritized()
    print(f"Priority list: {len(symbols)} symbols")
    start = time.time()
    budget = int(os.getenv("ANALYST_RATINGS_BUDGET", "90"))

    conn = get_connection()
    try:
        rec_rows: list[tuple] = []
        pt_rows: list[tuple] = []
        processed = 0
        total_records = 0
        skipped = 0
        symbols_since_commit = 0

        def flush() -> None:
            nonlocal rec_rows, pt_rows
            if not rec_rows and not pt_rows:
                return
            with conn.cursor() as cur:
                if rec_rows:
                    cur.executemany(
                        "INSERT IGNORE INTO analyst_recommendations "
                        "(symbol, firm, grade, price_target, action, rec_date) "
                        "VALUES (%s,%s,%s,%s,%s,%s)", rec_rows)
                if pt_rows:
                    cur.executemany(
                        "INSERT INTO analyst_targets "
                        "(ticker, date, target_price, current_price, recommendation, source) "
                        "VALUES (%s,%s,%s,%s,%s,%s) "
                        "ON DUPLICATE KEY UPDATE "
                        "target_price=VALUES(target_price), current_price=VALUES(current_price), "
                        "source=VALUES(source)", pt_rows)
            conn.commit()
            rec_rows = []
            pt_rows = []

        for idx, original_symbol in enumerate(symbols, 1):
            if time.time() - start > budget:
                print(f"Time budget {budget}s reached after {processed} processed — stopping (re-run to continue).")
                break
            ticker = resolve_ticker(original_symbol)
            if not ticker:
                skipped += 1
                continue
            try:
                tk = yf.Ticker(ticker)
                recs = getattr(tk, "recommendations", None)
                price_targets = getattr(tk, "analyst_price_targets", None)
                info = tk.info or {}
                if already_has_recs(conn, original_symbol):
                    skipped += 1
                    time.sleep(SLEEP_BETWEEN)
                    continue

                recs_added = 0
                if recs is not None and not recs.empty:
                    for _, row in recs.iterrows():
                        rec_date = safe_date(row.name[0] if hasattr(row.name, "__getitem__") else row.name)
                        if not rec_date:
                            continue
                        rec_rows.append((
                            original_symbol,
                            str(row.get("Firm", "") or "") or "Unknown",
                            row.get("To Grade") or row.get("Grade"),
                            float(row.get("Price Target")) if row.get("Price Target") is not None else None,
                            str(row.get("Action")) or "",
                            rec_date,
                        ))
                        recs_added += 1

                if price_targets and isinstance(price_targets, dict) and price_targets.get("current") is not None:
                    pt_rows.append((
                        original_symbol,
                        date.today(),
                        float(price_targets["current"]) if price_targets.get("current") is not None else None,
                        info.get("currentPrice"),
                        info.get("recommendationKey"),
                        "yfinance",
                    ))

                total_records += recs_added
                processed += 1
                symbols_since_commit += 1
                if len(rec_rows) >= REC_BATCH or symbols_since_commit >= SYM_COMMIT:
                    flush()
                    symbols_since_commit = 0
            except Exception as exc:
                skipped += 1
                if idx % 50 == 0:
                    print(f"  {original_symbol}: {type(exc).__name__}: {exc}")
            time.sleep(SLEEP_BETWEEN)

        flush()  # commit any remaining accumulated rows
        print(f"Done. Processed {processed} symbols, skipped {skipped}, recs added {total_records}.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
