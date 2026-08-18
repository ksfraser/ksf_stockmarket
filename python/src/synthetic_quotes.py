#!/usr/bin/env python3
"""Synthetic quote provider — a 'fake exchange' for instruments that have no
real market quote (money-market funds, private series, etc.).

Symbols registered in the `synthetic_quotes` table resolve to a static local
NAV instead of being sent to yfinance (which raises "Quote not found"). This is
the single source of truth for the synthetic exchange; the symbol resolver and
the daily pipeline both consult it.

Add/adjust rows via sql/seed_synthetic_quotes.sql.
"""
from typing import Optional, Dict, Any
import datetime

try:
    from database import get_connection
    _db_available = True
except ImportError:
    _db_available = False

SYNTHETIC_EXCHANGE = 'MMF'  # displayed exchange label for synthetic quotes


def is_synthetic(symbol: str) -> bool:
    """True if the symbol is registered in the synthetic exchange."""
    if not symbol or not _db_available:
        return False
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM synthetic_quotes WHERE symbol = %s AND is_active = 1 LIMIT 1",
                (symbol.upper(),),
            )
            return cur.fetchone() is not None
    except Exception:
        return False


def get_synthetic_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Return a single-row quote dict (shape matches daily_pipeline.download_today).

    Money-market NAVs are flat, so open/high/low/close are all the same price
    and volume is 0.
    """
    if not _db_available:
        return None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, name, price, currency, asof_date "
                "FROM synthetic_quotes WHERE symbol = %s AND is_active = 1 LIMIT 1",
                (symbol.upper(),),
            )
            row = cur.fetchone()
        if not row:
            return None
        price = float(row['price'])
        asof = row.get('asof_date') or datetime.date.today()
        if not isinstance(asof, str):
            asof = asof.strftime('%Y-%m-%d')
        return {
            'date': str(asof),
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': 0,
        }
    except Exception:
        return None
