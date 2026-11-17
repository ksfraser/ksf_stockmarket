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


def _translate_symbol(raw: str) -> str:
    """Normalize TradingView screener symbols to canonical form.

    Rules:
      * NASDAQ:SYM / NYSE:SYM / TSE:SYM / OTC:SYM -> SYM   (non-Canadian, no suffix)
      * TSX:SYM.UN            -> SYM.UN.TO
      * TSX:SYM               -> SYM.TO
      * NEO:SYM.UN            -> SYM.UN.TO
      * NEO:SYM               -> SYM.TO
      * already .TO/.UN.TO    -> pass-through

    Prevously every non-Canadian symbol was blindly given a ".TO" suffix,
    turning US/OTC tickers (e.g. NASDAQ:HOPE -> HOPE.TO) into invalid Toronto
    symbols and polluting downstream price/indicator data.
    """
    if not raw:
        return ""
    sym = raw.strip()
    if sym.endswith(".TO") or sym.endswith(".UN.TO"):
        return sym
    us_prefixes = ("NASDAQ:", "NYSE:", "TSE:", "OTC:")
    ca_prefixes = ("TSX:", "NEO:")
    for prefix in us_prefixes:
        if sym.startswith(prefix):
            return sym[len(prefix):]
    for prefix in ca_prefixes:
        if sym.startswith(prefix):
            base = sym[len(prefix):]
            return base + ".TO"
    # No recognized prefix: a bare ".UN" implies a Canadian unit-trust.
    if sym.endswith(".UN"):
        return sym + ".TO"
    return sym


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

    # Ensure unique key for true upsert
    cur.execute("""
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
    """)

    upsert_sql = """
        INSERT INTO tradingview_screener_results (preset_name, market, symbol, data, run_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            run_at = VALUES(run_at)
    """
    rows_inserted = 0
    for row in results:
        sym = _translate_symbol(row.get("symbol", ""))
        if not sym:
            continue
        payload = dict(row)
        payload["symbol"] = sym
        # Merge with existing JSON to avoid overwriting non-null old values with nulls
        cur.execute(
            "SELECT data FROM tradingview_screener_results WHERE preset_name=%s AND market=%s AND symbol=%s",
            (preset_name, market, sym),
        )
        existing = cur.fetchone()
        if existing and existing[0]:
            merged = json.loads(existing[0])
            for k, v in payload.items():
                if v is not None:
                    merged[k] = v
                # else: keep existing non-null value
            payload = merged
        cur.execute(upsert_sql, (preset_name, market, sym, json.dumps(payload)))
        rows_inserted += 1

        # Auto-insert new symbols into symbol_master
        try:
            if sym.endswith(".TO") or sym.endswith(".UN.TO"):
                exchange = "TSX"
                geography = "CA"
            else:
                exchange = "NASDAQ"
                geography = "US"
            cur.execute(
                """
                INSERT IGNORE INTO symbol_master
                    (symbol, name, exchange, geography, sector, is_active, last_updated)
                VALUES (%s, %s, %s, %s, %s, 1, NOW())
                """,
                (
                    sym,
                    payload.get("name") or "",
                    exchange,
                    geography,
                    payload.get("sector") or "",
                ),
            )
        except Exception as e:
            print(f"  Warning: symbol_master insert failed for {sym}: {e}")
    conn.commit()
    print(f"Upserted {rows_inserted} results for '{preset_name}' ({market})")


def build_index_fund_screener_results(conn) -> None:
    """Upsert curated low-cost Canadian index ETFs as a screener preset."""
    cur = conn.cursor()
    from build_index_fund_screener import LOW_COST_ETF_SYMBOLS, SYMBOL_SECTOR_MAP
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
    print(f"Upserted {upserted} rows for low_cost_index_funds preset")


def update_bond_average_from_db(conn) -> None:
    """Refresh synthetic BOND_AVG.TO price from representative Canadian bond ETFs."""
    from update_bond_average import BOND_BASKET, AVERAGE_SYMBOL
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
    if not prices:
        print("  No bond prices available")
        return
    avg = sum(prices.values()) / len(prices)
    cur.execute(
        """
        INSERT INTO stockprices (symbol, price_date, open, high, low, close, volume)
        VALUES (%s, CURDATE() - INTERVAL 1 DAY, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE close = VALUES(close), open = VALUES(open), high = VALUES(high), low = VALUES(low)
        """,
        (AVERAGE_SYMBOL, avg, avg, avg, avg, 0),
    )
    conn.commit()
    print(f"Updated {AVERAGE_SYMBOL} = {avg:.4f}")


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
        
        print("\nBuilding low-cost index fund screener preset...")
        build_index_fund_screener_results(conn)
        
        print("\nUpdating bond average (BOND_AVG.TO)...")
        update_bond_average_from_db(conn)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
