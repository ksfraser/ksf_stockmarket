#!/usr/bin/env python3
"""
TradingView Screener for ksf_stockmarket
Fetches stock screening results directly from TradingView public API.
Designed for cron job integration.
"""

import urllib.request
import json
import os
from datetime import datetime

from python.db_connector import get_connection

API_BASE = "https://scanner.tradingview.com"

def fetch_tradingview_screen(preset: str = None, filters: list = None, markets: list = None, 
                            sort_by: str = "market_cap_basic", limit: int = 50) -> list:
    """Fetch stock screener results from TradingView."""
    
    # TradingView returns data as {'s': symbol, 'd': [values...]}
    # Need to map values to column names
    
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
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ksf_stockmarket/1.0"
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            # Map the response: {'s': symbol, 'd': [values]} -> dict with named keys
            columns = payload["columns"]
            results = []
            for row in data.get("data", [])[:limit]:
                mapped = {"symbol": row["s"]}  # symbol
                for i, col in enumerate(columns):
                    mapped[col] = row["d"][i] if i < len(row["d"]) else None
                results.append(mapped)
            return results
    except Exception as e:
        print(f"API error: {e}")
        return []


def save_screening_results(results: list, preset_name: str, conn, market: str = "america"):
    """Save screening results to MariaDB."""
    
    cur = conn.cursor()
    
    # Create table if not exists (add market column)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tradingview_screener_results (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            preset_name VARCHAR(100),
            market VARCHAR(20) DEFAULT 'america',
            symbol VARCHAR(20),
            data JSON,
            run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_preset (preset_name),
            INDEX idx_symbol (symbol),
            INDEX idx_run_at (run_at)
        )
    """)
    
    # Clear old results for this preset+market (keep latest)
    cur.execute("DELETE FROM tradingview_screener_results WHERE preset_name = %s AND market = %s", (preset_name, market))
    
    # Insert results
    for row in results:
        symbol = row.get("symbol", "")
        cur.execute("""
            INSERT INTO tradingview_screener_results (preset_name, market, symbol, data)
            VALUES (%s, %s, %s, %s)
        """, (preset_name, market, symbol, json.dumps(row)))
    
    conn.commit()
    print(f"Saved {len(results)} results for '{preset_name}' ({market})")


def main():
    """Run all screens and save results."""
    conn = get_connection()
    try:
        screens = [
            ("dividend_stocks", "Dividend Stocks (Yield >3%)", "america"),
            ("quality_compounder", "Quality Compunders", "america"),
            ("value_stocks", "Value Stocks (P/E <15)", "america"),
            ("canadian_dividends", "Canadian Dividends (Yield >3%)", "canada"),
        ]
        
        for preset_name, label, market in screens:
            # Use dividend_stocks preset for Canadian too
            tv_preset = preset_name if preset_name != "canadian_dividends" else "dividend_stocks"
            print(f"\nFetching {label} ({market})...")
            results = fetch_tradingview_screen(preset=tv_preset, markets=[market], limit=100)
            
            if results:
                save_screening_results(results, preset_name, conn, market)
                print(f"  Top 5:")
                for r in results[:5]:
                    symbol = r.get("symbol", "N/A")
                    name = r.get("name", "N/A")
                    close = r.get("close", 0)
                    yield_pct = r.get("dividends_yield_current")
                    if yield_pct:
                        print(f"    {symbol}: {name[:30]:30} ${close:.2f} Yield: {yield_pct:.1f}%")
                    else:
                        print(f"    {symbol}: {name[:30]:30} ${close:.2f}")
            else:
                print(f"  No results (API error or no matches)")
                
    finally:
        conn.close()

if __name__ == "__main__":
    main()
