#!/usr/bin/env python3
"""Build low_cost_index_funds screener preset from curated symbol_master list."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from typing import Any

from python.db_connector import get_connection

LOW_COST_ETF_SYMBOLS = [
    # Canadian equity
    "XIC.TO", "VCN.TO", "ZCN.TO", "XIU.TO",
    # US equity
    "VFV.TO", "ZSP.TO", "XSP.TO",
    # Global / all-equity
    "XAW.TO", "VEQT.TO", "XEQT.TO",
    # Emerging markets
    "XEC.TO",
    # Sector / specialty
    "XIT.TO", "XFN.TO", "XGD.TO", "XEG.TO", "XMA.TO",
    "XLB.TO", "XLE.TO", "XRE.TO", "HXT.TO", "ZLB.TO",
    "XSU.TO",
    # Bonds / cash equivalents
    "XBB.TO", "ZAG.TO", "VAB.TO",
    "TBIL.TO", "ZGB.TO", "HMP.TO",
    "BOND_AVG.TO",
]

SYMBOL_SECTOR_MAP: dict[str, str] = {
    "XIC.TO": "Finance",
    "VCN.TO": "Finance",
    "ZCN.TO": "Finance",
    "XIU.TO": "Finance",
    "VFV.TO": "Technology Services",
    "ZSP.TO": "Technology Services",
    "XSP.TO": "Technology Services",
    "XAW.TO": "Miscellaneous",
    "VEQT.TO": "Miscellaneous",
    "XEQT.TO": "Miscellaneous",
    "XEC.TO": "Non-Energy Minerals",
    "XIT.TO": "Electronic Technology",
    "XFN.TO": "Finance",
    "XGD.TO": "Non-Energy Minerals",
    "XEG.TO": "Energy Minerals",
    "XMA.TO": "Non-Energy Minerals",
    "XLB.TO": "Non-Energy Minerals",
    "XLE.TO": "Energy Minerals",
    "XRE.TO": "Real Estate",
    "HXT.TO": "Finance",
    "ZLB.TO": "Finance",
    "XSU.TO": "Technology Services",
    "XBB.TO": "Bonds",
    "ZAG.TO": "Bonds",
    "VAB.TO": "Bonds",
    "TBIL.TO": "Bonds",
    "ZGB.TO": "Bonds",
    "HMP.TO": "Bonds",
    "BOND_AVG.TO": "Bonds",
}


def build(conn: Any) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tradingview_screener_results (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            preset_name VARCHAR(100),
            market VARCHAR(20) DEFAULT 'america',
            symbol VARCHAR(20),
            data JSON,
            run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_preset_market_symbol (preset_name, market, symbol),
            INDEX idx_preset (preset_name),
            INDEX idx_symbol (symbol),
            INDEX idx_run_at (run_at)
        )
        """
    )

    placeholders = ",".join(["%s"] * len(LOW_COST_ETF_SYMBOLS))
    cur.execute(
        f"""
        SELECT symbol, close, price_date
        FROM stockprices
        WHERE symbol IN ({placeholders})
        ORDER BY symbol, price_date DESC
        """,
        LOW_COST_ETF_SYMBOLS,
    )
    rows = cur.fetchall()
    price_map: dict[str, dict] = {}
    for r in rows:
        sym = r[0]
        if sym not in price_map:
            price_map[sym] = {
                "close": float(r[1]),
                "price_date": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
            }

    now = datetime.now().isoformat()
    upserted = 0
    for sym in LOW_COST_ETF_SYMBOLS:
        px = price_map.get(sym, {})
        payload = {
            "symbol": sym,
            "name": sym,
            "close": px.get("close"),
            "change": None,
            "Perf.Y": None,
            "RSI": None,
            "SMA50": None,
            "SMA200": None,
            "return_on_equity": None,
            "price_earnings_ttm": None,
            "price_book_fq": None,
            "dividends_yield_current": None,
            "market_cap_basic": None,
            "volume": None,
            "gross_margin_ttm": None,
            "return_on_invested_capital": None,
            "free_cash_flow_fy": None,
            "debt_to_equity": None,
            "sector": SYMBOL_SECTOR_MAP.get(sym, "Miscellaneous"),
        }
        cur.execute(
            """
            INSERT INTO tradingview_screener_results
                (preset_name, market, symbol, data, run_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                data = VALUES(data),
                run_at = VALUES(run_at)
            """,
            ("low_cost_index_funds", "canada", sym, json.dumps(payload), now),
        )
        upserted += 1
    conn.commit()
    logging.info("Upserted %d rows for low_cost_index_funds preset", upserted)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Build low-cost index fund screener preset")
    parser.add_argument("--connection", default=None)
    args = parser.parse_args()

    conn = get_connection()
    try:
        build(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
