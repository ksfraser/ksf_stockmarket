#!/usr/bin/env python3
"""Update synthetic BOND_AVG.TO price as the average price of representative Canadian bond ETFs."""

from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

from python.db_connector import get_connection

BOND_BASKET = ["TBIL.TO", "ZGB.TO", "HMP.TO"]
AVERAGE_SYMBOL = "BOND_AVG.TO"


def _latest_prices_per_symbol(cur, symbols: list[str], max_date: date) -> dict[str, float]:
    placeholders = ",".join(["%s"] * len(symbols))
    cur.execute(
        f"""
        SELECT s1.symbol, s1.close
        FROM stockprices s1
        JOIN (
            SELECT symbol, MAX(price_date) AS max_date
            FROM stockprices
            WHERE symbol IN ({placeholders})
              AND price_date <= %s
            GROUP BY symbol
        ) s2 ON s1.symbol = s2.symbol AND s1.price_date = s2.max_date
        """,
        symbols + [max_date],
    )
    return {r[0]: float(r[1]) for r in cur.fetchall()}


def update(conn, run_date: date | None = None) -> None:
    cur = conn.cursor()
    target = run_date or date.today() - timedelta(days=1)
    prices = _latest_prices_per_symbol(cur, BOND_BASKET, target)
    if not prices:
        logging.warning("No bond prices available for %s", target)
        return
    avg = sum(prices.values()) / len(prices)
    cur.execute(
        """
        INSERT INTO stockprices (symbol, price_date, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE close = VALUES(close), open = VALUES(open), high = VALUES(high), low = VALUES(low)
        """,
        (AVERAGE_SYMBOL, target, avg, avg, avg, avg, 0),
    )
    conn.commit()
    logging.info("Updated %s for %s = %.4f", AVERAGE_SYMBOL, target, avg)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Update bond average price")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    target = date.fromisoformat(args.date) if args.date else None
    conn = get_connection()
    try:
        update(conn, target)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
