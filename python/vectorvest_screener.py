#!/usr/bin/env python3
"""
VectorVest Safe Stock screener for ksf_stockmarket.

Evaluates the 5 VectorVest criteria:
  1. Smooth & steady price uptrend (1-year R² > threshold, slope > 0)
  2. Price currently rising (close > 20-day-ago close)
  3. Earnings rising (forward_eps present and positive or earnings_growth > 0)
  4. Market on your side (SPY 20-day trend > 0)
  5. Follow-through confirmed (today's close > today's open and > yesterday's close)

Stores results in tradingview_screener_results with preset_name='vectorvest_safe'.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from python.db_connector import get_connection

PRESET_NAME = "vectorvest_safe"
MARKET = "local"
LOOKBACK_DAYS = 365
MIN_PRICE_DAYS = 200  # require at least 200 trading days (~1 year)


def _regression_r2(prices: list[float]) -> tuple[float, float]:
    """Return (slope, r2) of ordinary least-squares line on index=0..len(prices)-1."""
    n = len(prices)
    if n < 2:
        return 0.0, 0.0
    x = list(range(n))
    y = prices
    sx = sum(x)
    sy = sum(y)
    sxy = sum(a * b for a, b in zip(x, y))
    sxx = sum(a * a for a in x)
    den = n * sxx - sx * sx
    if den == 0:
        return 0.0, 0.0
    slope = (n * sxy - sx * sy) / den
    intercept = (sy - slope * sx) / n
    ss_res = sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
    ss_tot = sum((yi - sy / n) ** 2 for yi in y)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return slope, r2


def evaluate_symbol(symbol: str, run_date: date, market_ok: bool) -> dict[str, Any] | None:
    """Evaluate VectorVest criteria for one symbol. Returns metrics dict or None."""
    start = run_date - timedelta(days=LOOKBACK_DAYS + 30)

    db = get_connection()
    cur = db.cursor()
    cur.execute(
        f"""
        SELECT price_date, open, high, low, close, volume
        FROM stockprices
        WHERE symbol = %s AND price_date BETWEEN %s AND %s
        ORDER BY price_date ASC
        """,
        (symbol, str(start), str(run_date)),
    )
    rows = cur.fetchall()
    cur.close()
    db.close()

    if not rows or len(rows) < MIN_PRICE_DAYS:
        return None

    closes = [float(r["close"]) for r in rows]
    volumes = [float(r["volume"]) for r in rows]
    opens = [float(r["open"]) for r in rows]

    today = rows[-1]
    yesterday = rows[-2] if len(rows) > 1 else None

    # 1) Smooth uptrend
    slope, r2 = _regression_r2(closes)
    smooth_uptrend = slope > 0 and r2 >= 0.55

    # 2) Price currently rising (close > close 20 days ago)
    price_rising = len(closes) > 20 and closes[-1] > closes[-21]

    # 3) Earnings rising (fundamentals lookup)
    db = get_connection()
    cur = db.cursor()
    cur.execute(
        f"""
        SELECT forward_eps, earnings_growth, trailing_eps
        FROM fundamentals
        WHERE symbol = %s
        ORDER BY fetch_date DESC
        LIMIT 1
        """,
        (symbol,),
    )
    fund = cur.fetchone()
    cur.close()
    db.close()

    earnings_rising = False
    if fund:
        fwd = fund.get("forward_eps")
        eg = fund.get("earnings_growth")
        if fwd is not None and float(fwd) > 0:
            earnings_rising = True
        elif eg is not None and float(eg) > 0:
            earnings_rising = True
        elif fund.get("trailing_eps") is not None and float(fund["trailing_eps"]) > 0:
            earnings_rising = True

    # 4) Market on your side
    market_ok = market_ok

    # 5) Follow-through confirmed (today close > today open AND today close > yesterday close)
    follow_through = False
    if today and yesterday:
        c = float(today["close"])
        o = float(today["open"])
        yc = float(yesterday["close"])
        follow_through = c > o and c > yc

    pass_count = sum([
        1 if smooth_uptrend else 0,
        1 if price_rising else 0,
        1 if earnings_rising else 0,
        1 if market_ok else 0,
        1 if follow_through else 0,
    ])

    score = pass_count * 20.0
    passed = pass_count >= 4  # must pass at least 4/5

    return {
        "symbol": symbol,
        "smooth_uptrend": bool(smooth_uptrend),
        "price_rising": bool(price_rising),
        "earnings_rising": bool(earnings_rising),
        "market_ok": bool(market_ok),
        "follow_through": bool(follow_through),
        "r2": round(r2, 4),
        "slope_positive": bool(slope > 0),
        "pass_count": pass_count,
        "score": score,
        "passed": bool(passed),
        "close": closes[-1],
        "price_date": str(today["price_date"]),
    }


def _get_market_trend(db, run_date: date) -> bool:
    """Return True if SPY 20-day trend is positive (market on your side)."""
    start = run_date - timedelta(days=40)
    cur = db.cursor()
    cur.execute(
        """
        SELECT close FROM stockprices
        WHERE symbol = 'SPY' AND price_date BETWEEN %s AND %s
        ORDER BY price_date ASC
        """,
        (str(start), str(run_date)),
    )
    rows = cur.fetchall()
    cur.close()
    if not rows or len(rows) < 20:
        return True  # default to pass if no data
    closes = [float(r["close"]) for r in rows]
    return closes[-1] > closes[-21] if len(closes) > 21 else closes[-1] > closes[0]


def run(run_date: date | None = None, max_symbols: int = 500) -> None:
    """Run the VectorVest screener for ``run_date`` and persist results."""
    run_date = run_date or date.today()
    db = get_connection()
    market_ok = _get_market_trend(db, run_date)

    # Get symbols with price history
    cur = db.cursor()
    cur.execute(
        """
        SELECT DISTINCT symbol
        FROM stockprices
        WHERE price_date >= %s
        ORDER BY symbol
        LIMIT %s
        """,
        (str(run_date - timedelta(days=LOOKBACK_DAYS + 30)), max_symbols),
    )
    symbols = [r["symbol"] for r in cur.fetchall()]
    cur.close()

    results = []
    for symbol in symbols:
        try:
            metrics = evaluate_symbol(symbol, run_date, market_ok)
            if metrics:
                results.append(metrics)
        except Exception:
            continue

    results.sort(key=lambda r: (r["passed"], r["score"]), reverse=True)

    # Persist to tradingview_screener_results
    cur = db.cursor()
    cur.execute(
        "DELETE FROM tradingview_screener_results WHERE preset_name = %s AND market = %s",
        (PRESET_NAME, MARKET),
    )
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for m in results:
        cur.execute(
            """
            INSERT INTO tradingview_screener_results (preset_name, market, symbol, data, run_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (PRESET_NAME, MARKET, m["symbol"], json.dumps(m), now),
        )
    db.commit()
    cur.close()
    db.close()
    print(f"VectorVest screener complete: {len(results)} symbols evaluated, "
          f"{sum(1 for r in results if r['passed'])} passed.")


if __name__ == "__main__":
    run()
