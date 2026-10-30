#!/usr/bin/env python3
"""
tv_screener_resilient.py — Resilient TradingView screener for cron.

Fixes: shorter timeouts + retry logic + smaller query batches to avoid
the 600s cron timeout. TradingView API is slow (~2-3 min per screen).
"""

import sys
import os
import json
import time
import urllib.request
from datetime import datetime
from decimal import Decimal

# Add repo to path (two levels up from scripts/)
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_DIR, "python/src"))
sys.path.insert(0, os.path.join(REPO_DIR, "python"))

from tv_screener import fetch_tradingview_screen, save_screening_results
from db_connector import get_connection
from stockprice_dao import PriceRow, create_central_stockprice_dao
from build_index_fund_screener import LOW_COST_ETF_SYMBOLS, SYMBOL_SECTOR_MAP
from update_bond_average import BOND_BASKET, AVERAGE_SYMBOL


def fetch_tradingview_screen_with_retry(preset, markets, limit=100, max_retries=5, timeout=25):
    """Fetch screen with retry logic (shorter timeout + retry)."""
    payload = {
        "symbols": {"query": {"types": []}},
        "columns": [
            "name", "close", "change", "Perf.Y", "RSI", "SMA50", "SMA200",
            "return_on_equity", "price_earnings_ttm", "price_book_fq", "dividends_yield_current",
            "market_cap_basic", "volume", "gross_margin_ttm", "return_on_invested_capital",
            "free_cash_flow_fy", "debt_to_equity", "sector"
        ],
        "filter": []
    }
    if preset == "dividend_stocks":
        payload["filter"] = [
            {"left": "dividends_yield_current", "operation": "nempty"},
            {"left": "dividends_yield_current", "operation": "greater", "right": 3},
            {"left": "market_cap_basic", "operation": "greater", "right": 1000000000},
            {"left": "debt_to_equity", "operation": "less", "right": 1.0}
        ]
    elif preset == "quality_compounder":
        payload["filter"] = [
            {"left": "gross_margin_ttm", "operation": "greater", "right": 40},
            {"left": "return_on_invested_capital", "operation": "greater", "right": 15},
            {"left": "free_cash_flow_fy", "operation": "greater", "right": 0}
        ]
    elif preset == "value_stocks":
        payload["filter"] = [
            {"left": "price_earnings_ttm", "operation": "less", "right": 15},
            {"left": "price_book_fq", "operation": "less", "right": 1.5},
            {"left": "return_on_equity", "operation": "greater", "right": 10}
        ]
    if markets is None:
        markets = ["america"]
    url = f"{API_BASE}/{markets[0]}/scan"
    headers = {"Content-Type": "application/json", "User-Agent": "ksf_stockmarket/1.0"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode())
                columns = payload["columns"]
                results = []
                for row in data.get("data", [])[:limit]:
                    mapped = {"symbol": row["s"]}
                    for i, col in enumerate(columns):
                        mapped[col] = row["d"][i] if i < len(row["d"]) else None
                    results.append(mapped)
                return results
        except Exception as e:
            last_err = e
            print(f"  Attempt {attempt+1} failed: {e}", flush=True)
            time.sleep(5)
    print(f"  GAVE UP after {max_retries} attempts: {last_err}", flush=True)
    return []


def main():
    conn = get_connection()
    try:
        screens = [
            ("dividend_stocks", "Dividend Stocks (Yield >3%)", "america"),
            ("quality_compounder", "Quality Compounders", "america"),
            ("value_stocks", "Value Stocks (P/E <15)", "america"),
            ("canadian_dividends", "Canadian Dividends (Yield >3%)", "canada"),
        ]

        for preset_name, label, market in screens:
            tv_preset = preset_name if preset_name != "canadian_dividends" else "dividend_stocks"
            print(f"\nFetching {label} ({market})...", flush=True)
            results = fetch_tradingview_screen_with_retry(tv_preset, [market], limit=100, max_retries=5)
            if results:
                save_screening_results(results, preset_name, conn, market)
                print(f"  Top 5:", flush=True)
                for r in results[:5]:
                    symbol = r.get("symbol", "N/A")
                    name = r.get("name", "N/A")
                    close = r.get("close", 0)
                    yield_pct = r.get("dividends_yield_current")
                    if yield_pct:
                        print(f"    {symbol}: {name[:30]:30} ${close:.2f} Yield: {yield_pct:.1f}%", flush=True)
                    else:
                        print(f"    {symbol}: {name[:30]:30} ${close:.2f}", flush=True)
            else:
                print(f"  No results (API error or no matches)", flush=True)

        print("\nBuilding low-cost index fund screener preset...", flush=True)
        cur = conn.cursor()
        from build_index_fund_screener import LOW_COST_ETF_SYMBOLS, SYMBOL_SECTOR_MAP
        placeholders = ",".join(["%s"] * len(LOW_COST_ETF_SYMBOLS))
        cur.execute(
            f"SELECT symbol, close, price_date FROM stockprices WHERE symbol IN ({placeholders}) ORDER BY symbol, price_date DESC",
            LOW_COST_ETF_SYMBOLS,
        )
        rows = cur.fetchall()
        price_map = {}
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
                "symbol": sym, "name": sym, "close": px.get("close"), "change": None, "Perf.Y": None,
                "RSI": None, "SMA50": None, "SMA200": None, "return_on_equity": None,
                "price_earnings_ttm": None, "price_book_fq": None, "dividends_yield_current": None,
                "market_cap_basic": None, "volume": None, "gross_margin_ttm": None,
                "return_on_invested_capital": None, "free_cash_flow_fy": None, "debt_to_equity": None,
                "sector": SYMBOL_SECTOR_MAP.get(sym, "Miscellaneous"),
            }
            cur.execute(
                "INSERT INTO tradingview_screener_results (preset_name, market, symbol, data, run_at) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE data = VALUES(data), run_at = VALUES(run_at)",
                ("low_cost_index_funds", "canada", sym, json.dumps(payload), now),
            )
            upserted += 1
        conn.commit()
        print(f"Upserted {upserted} rows for low_cost_index_funds preset", flush=True)

        print("\nUpdating bond average (BOND_AVG.TO)...", flush=True)
        cur = conn.cursor()
        placeholders = ",".join(["%s"] * len(BOND_BASKET))
        cur.execute(
            f"""
            SELECT s1.symbol, s1.close
            FROM stockprices s1
            JOIN (
                SELECT symbol, MAX(price_date) AS max_date
                FROM stockprices
                WHERE symbol IN ({placeholders})
                  AND price_date <= CURDATE() - INTERVAL 1 DAY
                GROUP BY symbol
            ) s2 ON s1.symbol = s2.symbol AND s1.price_date = s2.max_date
            """,
            BOND_BASKET,
        )
        prices = {r[0]: float(r[1]) for r in cur.fetchall()}
        cur.close()
        if not prices:
            print("No bond prices available", flush=True)
        else:
            avg = sum(prices.values()) / len(prices)
            dao = create_central_stockprice_dao(central_db=conn)
            row = PriceRow(
                symbol=AVERAGE_SYMBOL,
                price_date=date.today(),
                open=Decimal(str(avg)),
                high=Decimal(str(avg)),
                low=Decimal(str(avg)),
                close=Decimal(str(avg)),
                volume=0,
                adj_close=Decimal(str(avg)),
                currency="CAD",
                dividend=None,
                split_ratio=Decimal("1"),
            )
            affected = dao.write_prices([row])
            print(f"Updated {AVERAGE_SYMBOL} = {avg:.4f} ({affected} row(s) affected)", flush=True)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
