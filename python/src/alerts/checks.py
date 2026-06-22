"""Pure alert detection functions.

Each function returns a dict payload describing the alert, or None when
the condition is not met.  No DB writes, no side effects.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

import pymysql
from .config_mysql import MYSQL

logger = logging.getLogger(__name__)


def _conn() -> pymysql.connections.Connection:
    return pymysql.connect(**MYSQL)


def _latest_row(symbol: str):
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT MAX(date) FROM stockprices WHERE symbol = %s",
            (symbol,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def check_volume_spike(  # type: ignore[return]
    symbol: str,
    threshold_ratio: float = 3.0,
    critical_ratio: float = 5.0,
) -> Optional[Dict]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT v.volume, w.avg_volume_30d
            FROM stockprices v
            JOIN watchlist_symbols s ON s.symbol = v.symbol
            LEFT JOIN (
                SELECT symbol, AVG(volume) AS avg_volume_30d
                FROM stockprices
                GROUP BY symbol
            ) w ON w.symbol = v.symbol
            WHERE v.symbol = %s
              AND v.price_date = (SELECT MAX(price_date) FROM stockprices WHERE symbol = %s)
            """,
            (symbol, symbol),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    volume, avg_volume_30d = row
    if volume is None:
        return None

    ratio = float(volume) / float(avg_volume_30d)
    if ratio < threshold_ratio:
        return None

    severity = "critical" if ratio >= critical_ratio else "high"
    return {
        "symbol": symbol,
        "alert_type": "volume_spike",
        "severity": severity,
        "payload": {
            "current_volume": int(volume),
            "avg_volume": float(avg_volume_30d),
            "volume_ratio": round(ratio, 2),
        },
        "triggered_at": datetime.now().isoformat(),
    }


def check_oscillator_extremes(symbol: str) -> Optional[Dict]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT RSI_14, STOCH_14_3_3_k, STOCH_14_3_3_d
            FROM ta_indicators
            WHERE symbol = %s
              AND price_date = (SELECT MAX(price_date) FROM ta_indicators WHERE symbol = %s)
            """,
            (symbol, symbol),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    rsi, stoch_k, stoch_d = row
    if rsi is None:
        return None

    extreme = None
    if rsi >= 70:
        extreme = "overbought"
    elif rsi <= 30:
        extreme = "oversold"

    if not extreme:
        return None

    return {
        "symbol": symbol,
        "alert_type": "oscillator_extremes",
        "severity": "medium",
        "payload": {
            "rsi_20d": float(rsi) if rsi is not None else None,
            "rsi": float(rsi) if rsi is not None else None,
            "stoch_k": float(stoch_k) if stoch_k is not None else None,
            "stoch_d": float(stoch_d) if stoch_d is not None else None,
            "extreme": extreme,
        },
        "triggered_at": datetime.now().isoformat(),
    }


def check_natr_spike(
    symbol: str,
    threshold_ratio: float = 2.0,
) -> Optional[Dict]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT NATR_20, natr_avg_20d
            FROM (
                SELECT symbol, price_date, NATR_20,
                       AVG(NATR_20) OVER (PARTITION BY symbol ORDER BY price_date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS natr_avg_20d
                FROM ta_indicators
            ) t
            WHERE symbol = %s
              AND price_date = (SELECT MAX(price_date) FROM ta_indicators WHERE symbol = %s)
            """,
            (symbol, symbol),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    natr_20d, natr_avg_20d = row
    ratio = 0
    if natr_avg_20d:
        ratio = float(natr_20d) / float(natr_avg_20d)

    if ratio < threshold_ratio:
        return None

    return {
        "symbol": symbol,
        "alert_type": "natr_spike",
        "severity": "medium",
        "payload": {
            "natr_20d": float(natr_20d) if natr_20d is not None else None,
            "natr_avg": float(natr_avg_20d) if natr_avg_20d is not None else None,
            "natr_ratio": round(ratio, 2),
        },
        "triggered_at": datetime.now().isoformat(),
    }


def check_gap_opening(
    symbol: str,
    threshold_pct: float = 0.02,
) -> Optional[Dict]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT today.open, yesterday.close
            FROM stockprices today
            JOIN stockprices yesterday
              ON yesterday.symbol = today.symbol
             AND yesterday.price_date = (
                 SELECT MAX(price_date) FROM stockprices WHERE symbol = %s AND price_date < today.price_date
             )
            WHERE today.symbol = %s
              AND today.price_date = (SELECT MAX(price_date) FROM stockprices WHERE symbol = %s)
            """,
            (symbol, symbol, symbol),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row or (row[0] is None or row[0] == 0) or (row[1] is None or row[1] == 0):
        return None

    open_price, prev_close = row
    gap_pct = float(open_price - prev_close) / float(prev_close)

    if abs(gap_pct) < threshold_pct:
        return None

    direction = "gap_up" if gap_pct > 0 else "gap_down"
    if direction == "gap_up":
        implication = "Bullish gap up suggests strong buying momentum; watch for breakout continuation."
    else:
        implication = "Bearish gap down indicates selling pressure; watch for breakdown risk."

    return {
        "symbol": symbol,
        "alert_type": direction,
        "severity": "medium",
        "payload": {
            "open_price": float(open_price),
            "prev_close": float(prev_close),
            "gap_pct": round(gap_pct * 100, 2),
            "direction": direction,
            "implication": implication,
        },
        "triggered_at": datetime.now().isoformat(),
    }
