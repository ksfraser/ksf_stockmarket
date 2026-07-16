#!/usr/bin/env python3
"""Backfill historical fundamentals from yfinance financial statements.

For each symbol with existing fundamentals, fetch annual income statement
and balance sheet, compute key ratios for each fiscal year, look up the
nearest historical price, and insert historical rows into the fundamentals
table.

Runs in batches with throttled yfinance calls.

Usage:
    PYTHONPATH=".:python:python/src" python3 scripts/backfill_historical_fundamentals.py \
        --batch-size 50 --sleep 0.5
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path

import pymysql
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "python" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from db_connector import get_connection  # noqa: E402

logger = logging.getLogger(__name__)

YEARS_BACK = 10
MIN_FISCAL_DATE = date.today().replace(year=date.today().year - YEARS_BACK)

# Fields we compute from statements that map to fundamentals columns
STATEMENT_RATIOS = [
    "roe",
    "debt_to_equity",
    "gross_margin",
    "operating_margin",
    "profit_margin",
    "roa",
    "revenue_growth",
]


def get_symbols(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT f.symbol
            FROM fundamentals f
            INNER JOIN stockprices p ON p.symbol = f.symbol
            WHERE p.price_date >= %s
            ORDER BY f.symbol
        """, (MIN_FISCAL_DATE,))
        return [r[0] for r in cur.fetchall()]


def nearest_price(db, symbol: str, target: date) -> float | None:
    with db.cursor() as cur:
        cur.execute("""
            SELECT close FROM stockprices
            WHERE symbol = %s AND price_date <= %s
            ORDER BY price_date DESC LIMIT 1
        """, (symbol, target))
        row = cur.fetchone()
        return float(row[0]) if row else None


def ratios_from_statements(symbol: str) -> dict[date, dict[str, float | None]]:
    """Fetch annual financials + balance sheet, return ratios keyed by fiscal_date."""
    out: dict[date, dict[str, float | None]] = {}
    try:
        ticker = yf.Ticker(symbol)
        fin = ticker.financials
        bs = ticker.balance_sheet
    except Exception as exc:
        logger.warning("yfinance fetch failed for %s: %s", symbol, exc)
        return out

    if fin is None or fin.empty or bs is None or bs.empty:
        return out

    # Align fiscal dates
    fin_dates = list(fin.columns)
    bs_dates = list(bs.columns)

    for fd in fin_dates:
        if not hasattr(fd, "date"):
            continue
        fd_date = fd.date()
        if fd_date < MIN_FISCAL_DATE:
            continue
        ratios: dict[str, float | None] = {k: None for k in STATEMENT_RATIOS}

        try:
            row = fin[fd]
            def _f(v):
                try:
                    if v is None:
                        return None
                    f = float(v)
                    return f if f == f else None
                except Exception:
                    return None
            revenue = _f(row.get("Total Revenue"))
            gross = _f(row.get("Gross Profit"))
            net_income = _f(row.get("Net Income"))
            operating_income = _f(row.get("Operating Income"))
        except Exception as exc:
            logger.debug("financials row error %s %s: %s", symbol, fd, exc)
            continue

        if revenue is not None and revenue > 0:
            ratios["gross_margin"] = gross / revenue if gross is not None else None
            ratios["operating_margin"] = operating_income / revenue if operating_income is not None else None
            ratios["profit_margin"] = net_income / revenue if net_income is not None else None
        if net_income:
            ratios["roa"] = None  # need total assets from balance sheet

        # Revenue growth: compare to prior year
        idx = fin_dates.index(fd)
        if idx > 0:
            try:
                prev_revenue = _f(fin.iloc[:, idx - 1].get("Total Revenue"))
                if prev_revenue is not None and prev_revenue > 0 and revenue is not None and revenue > 0:
                    ratios["revenue_growth"] = (revenue / prev_revenue) - 1.0
            except Exception:
                pass

        try:
            bs_row = bs[fd]
        except KeyError:
            bs_row = None

        if bs_row is not None:
            try:
                equity = _f(bs_row.get("Stockholders Equity"))
                total_liab = _f(bs_row.get("Total Liabilities Net Minority Interest"))
                shares_out = _f(bs_row.get("Ordinary Shares Number"))
                if equity is not None and equity > 0:
                    ratios["roe"] = net_income / equity if net_income is not None else None
                    ratios["debt_to_equity"] = total_liab / equity if total_liab is not None else None
                    ratios["roa"] = net_income / equity if net_income is not None else None
                if shares_out is not None and shares_out > 0:
                    ratios["shares_outstanding"] = shares_out
            except Exception as exc:
                logger.debug("balance sheet row error %s %s: %s", symbol, fd, exc)

        out[fd] = ratios

    return out


def upsert_ratios(
    db,
    symbol: str,
    fiscal_date: date,
    ratios: dict[str, float | None],
) -> None:
    if not ratios:
        return
    present = [(k, v) for k, v in ratios.items() if v is not None]
    if not present:
        return
    cols = ["symbol", "fetch_date"] + [k for k, _ in present]
    placeholders = ["%s", "%s"] + ["%s"] * len(present)
    vals: list = [symbol, fiscal_date] + [v for _, v in present]
    set_parts = [f"{k} = VALUES({k})" for k, _ in present]
    sql = f"""
        INSERT INTO fundamentals ({', '.join(cols)})
        VALUES ({', '.join(placeholders)})
        ON DUPLICATE KEY UPDATE {', '.join(set_parts)}
    """
    with db.cursor() as cur:
        cur.execute(sql, vals)


def run(batch_size: int, sleep_seconds: float) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = get_connection()
    try:
        symbols = get_symbols(db)
        logger.info("Symbols to backfill: %d", len(symbols))
    except Exception as exc:
        logger.error("Failed to load symbols: %s", exc)
        return 1

    commits = 0
    errors = 0
    skipped = 0
    for idx, sym in enumerate(symbols, 1):
        try:
            ratios_map = ratios_from_statements(sym)
            for fd, ratios in ratios_map.items():
                price = nearest_price(db, sym, fd)
                if price and price > 0:
                    so = ratios.get("shares_outstanding")
                    ratios["market_cap"] = price * so if so is not None else None
                upsert_ratios(db, sym, fd, ratios)
            if idx % batch_size == 0:
                db.commit()
                commits += 1
                logger.info("Committed %d symbols (batch %d)", idx, commits)
        except Exception as exc:
            logger.warning("Error backfilling %s: %s", sym, exc)
            errors += 1
        finally:
            time.sleep(sleep_seconds)

    db.commit()
    logger.info(
        "Done: symbols=%d errors=%d skipped=%d batches=%d",
        len(symbols), errors, skipped, commits,
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill historical fundamentals")
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--sleep", type=float, default=0.5, help="Seconds between yfinance calls")
    args = p.parse_args()
    return run(batch_size=args.batch_size, sleep_seconds=args.sleep)


if __name__ == "__main__":
    raise SystemExit(main())
