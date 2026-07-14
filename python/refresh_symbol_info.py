#!/usr/bin/env python3
"""
Refresh symbol identity fields and re-enrich company-specific data from yfinance.

- Update symbol_master: name, sector, industry, exchange
- Refresh fundamentals row from yfinance .info
- Optionally wipe dependent enrichment tables so yahoo_enrichment.py can rebuild them
"""
import sys
import os
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'src'))

import pymysql.cursors
import yfinance as yf
from symbol_resolver import resolve_for_yfinance

DB_CFG = {
    'host': 'ksfraser.ca',
    'port': 3306,
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

# Short bare symbols that resolve correctly without .TO on yfinance.
# All other short, dot-free symbols default to .TO for TSX disambiguation.
US_SHORT_NO_SUFFIX = {
    'CEF', 'GLD', 'RGLD', 'SLV', 'USO', 'UNG', 'TLT', 'EEM', 'EFA',
    'VWO', 'VEA', 'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'IVV',
    'AGG', 'BND', 'LQD', 'HYG', 'JNK', 'XLF', 'XLE', 'XLI', 'XLV',
    'XLP', 'XLY', 'XLB', 'XLRE', 'XLK', 'XLU', 'XLC', 'XBI', 'IBB',
    'SMH', 'SOXX', 'KRE', 'KBE', 'XOP', 'OIH', 'ITB', 'XHB', 'XRT',
    'XME', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA',
    'BRK-B', 'JNJ', 'JPM', 'V', 'MA', 'PG', 'UNH', 'HD', 'KO', 'PEP',
    'ABBV', 'MRK', 'XOM', 'CVX', 'LLY', 'TMO', 'ABT', 'ORCL', 'COST',
    'AVGO', 'QCOM', 'CSCO', 'ACN', 'MCD', 'NKE', 'DHR', 'TXN', 'PM',
    'LIN', 'UNP', 'LOW', 'BA', 'IBM', 'AMGN', 'CAT', 'GS', 'BLK',
}


def get_symbol_exchange(symbol: str) -> str | None:
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            # 1. exchange_mapping
            cur.execute("SELECT yahoo_ticker FROM exchange_mapping WHERE symbol = %s AND is_primary = 1 AND is_active = 1 LIMIT 1", (symbol,))
            row = cur.fetchone()
            if row and row.get('yahoo_ticker'):
                return row['yahoo_ticker']
            # 2. portfolio price_symbol ending in .TO
            cur.execute("SELECT price_symbol FROM portfolio WHERE symbol = %s AND price_symbol LIKE %s LIMIT 1", (symbol, '%.TO'))
            row = cur.fetchone()
            if row:
                return 'TSX'
            # 3. symbol_master exchange = TSX
            cur.execute("SELECT exchange FROM symbol_master WHERE symbol = %s LIMIT 1", (symbol,))
            row = cur.fetchone()
            if row and row.get('exchange'):
                return 'TSX' if 'TSX' in (row.get('exchange') or '').upper() else row.get('exchange')
    finally:
        conn.close()
    return None


def resolve_with_fallback(symbol: str) -> str:
    resolved = resolve_for_yfinance(symbol)
    if resolved != symbol or '.' in symbol or len(symbol) > 5 or symbol in US_SHORT_NO_SUFFIX:
        return resolved

    exchange_hint = get_symbol_exchange(symbol)
    if exchange_hint and 'TSX' in str(exchange_hint).upper():
        return symbol + '.TO'

    candidate = symbol + '.TO'
    bare_info = _safe_info(symbol)
    ca_info = _safe_info(candidate)
    if ca_info and (bare_info is None or len(ca_info) > len(bare_info)):
        return candidate
    return symbol


def _safe_info(ticker: str):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        keys = len(info)
        # yfinance returns a 1-key error dict for not-found tickers.
        if keys <= 1 and not info.get('shortName') and not info.get('longName'):
            return None
        return info
    except Exception:
        return None


def clean(v):
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    # Numeric types can legitimately appear for sector/industry? usually not
    return None


def get_active_symbols():
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
            return [r['symbol'] for r in cur.fetchall()]
    finally:
        conn.close()


def update_symbol_master(symbol, name, sector, industry, exchange):
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE symbol_master
                   SET name = %s,
                       sector = COALESCE(%s, sector),
                       industry = COALESCE(%s, industry),
                       exchange = COALESCE(%s, exchange),
                       last_updated = NOW()
                 WHERE symbol = %s
            """, (name, sector, industry, exchange, symbol))
            conn.commit()
    finally:
        conn.close()


def upsert_fundamentals(symbol, info):
    if not info:
        return

    fields = {
        'market_cap': 'marketCap',
        'dividend_yield': 'dividendYield',
        'payout_ratio': 'payoutRatio',
        'trailing_eps': 'trailingEps',
        'forward_eps': 'forwardEps',
        'trailing_pe': 'trailingPE',
        'forward_pe': 'forwardPE',
        'peg_ratio': 'pegRatio',
        'price_to_book': 'priceToBook',
        'price_to_sales': 'priceToSales',
        'book_value': 'bookValue',
        'free_cash_flow': 'freeCashflow',
        'operating_cash_flow': 'operatingCashflow',
        'total_revenue': 'totalRevenue',
        'revenue_growth': 'revenueGrowth',
        'gross_margin': 'grossMargins',
        'operating_margin': 'operatingMargins',
        'profit_margin': 'profitMargins',
        'roe': 'returnOnEquity',
        'roa': 'returnOnAssets',
        'debt_to_equity': 'debtToEquity',
        'current_ratio': 'currentRatio',
        'quick_ratio': 'quickRatio',
        'dividend_rate': 'dividendRate',
        'annual_dividend_total': 'dividendRate',
        'fcf_per_share': 'freeCashflowPerShare',
        'dividend_fcf_coverage': 'dividendFCFCoverage',
        'five_year_div_yield': 'fiveYearAvgDividendYield',
        'earnings_growth': 'earningsGrowth',
        'beta': 'beta',
        'short_ratio': 'shortRatio',
        'short_percent': 'shortPercentOfFloat',
        'insider_percent': 'heldPercentInsiders',
        'institutional_percent': 'heldPercentInstitutions',
        'shares_outstanding': 'sharesOutstanding',
        'float_shares': 'floatShares',
        'sector': 'sector',
        'industry': 'industry',
    }

    set_parts = []
    params = []
    for col, info_key in fields.items():
        val = clean(info.get(info_key))
        if val is not None:
            set_parts.append(f"{col} = VALUES({col})")

    if not set_parts:
        return

    cols = ['symbol', 'fetch_date'] + list(fields.keys())
    placeholders = ['%s', '%s'] + ['%s'] * len(fields)
    values = [symbol, datetime.now().date()]
    for key in fields.values():
        values.append(clean(info.get(key)))

    sql = f"""
        INSERT INTO fundamentals ({', '.join(cols)})
        VALUES ({', '.join(placeholders)})
        ON DUPLICATE KEY UPDATE {', '.join(set_parts)}
    """

    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            conn.commit()
    finally:
        conn.close()


def clear_enrichment(symbol):
    tables = [
        'analyst_recommendations',
        'analyst_estimates',
        'financial_statements',
        'holders',
        'symbol_news',
    ]
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            for t in tables:
                try:
                    cur.execute(f"DELETE FROM {t} WHERE symbol = %s", (symbol,))
                except Exception:
                    pass
            conn.commit()
    finally:
        conn.close()


def enrich_symbol(symbol, ticker_info):
    info = ticker_info or {}

    name = clean(info.get('shortName') or info.get('longName') or info.get('name'))
    sector = clean(info.get('sector'))
    industry = clean(info.get('industry'))

    exchange = None
    if info.get('exchange'):
        exchange = clean(info.get('exchange'))
    raw_ex = info.get('fullExchangeName')
    if not exchange and isinstance(raw_ex, str):
        exchange = clean(raw_ex.split()[0])

    if name or sector or industry or exchange:
        update_symbol_master(symbol, name, sector, industry, exchange)
    elif not name:
        # Synthetic fallback so row has an identifier even when yfinance has no data.
        marker = f"{symbol} (no data)"
        update_symbol_master(symbol, marker, None, None, None)

    upsert_fundamentals(symbol, info)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbols', default=None, help='Comma-separated symbols')
    parser.add_argument('--clear', action='store_true', help='Delete dependent enrichment tables before refresh')
    parser.add_argument('--no-fundamentals', action='store_true', help='Do not write fundamentals table')
    args = parser.parse_args()

    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
    else:
        symbols = get_active_symbols()

    print(f"Active symbols: {len(symbols)}")

    done = 0
    updated = 0
    errors = 0
    for sym in symbols:
        try:
            resolved = resolve_with_fallback(sym)
            print(f"  {sym} -> {resolved}")
            try:
                info = _safe_info(resolved)
                if not info:
                    raise ValueError("Empty info")
            except Exception as e:
                print(f"  yfinance fetch failed for {sym} ({resolved}): {e}")
                # Synthetic fallback so row has a non-NULL name even with no yfinance data.
                update_symbol_master(sym, sym, None, None, None)
                errors += 1
                done += 1
                continue

            if args.clear:
                clear_enrichment(sym)

            enrich_symbol(sym, info)
            updated += 1

            done += 1
            if done % 25 == 0:
                print(f"  Processed {done}/{len(symbols)} ({sym})")
        except Exception as e:
            errors += 1
            print(f"  Error on {sym}: {e}")

        time.sleep(0.12)

    print(f"Done. Processed: {done}, Updated: {updated}, Errors: {errors}")


if __name__ == '__main__':
    main()
