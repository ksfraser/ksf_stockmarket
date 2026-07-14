#!/usr/bin/env python3
"""
Enrich symbol data from yfinance:
- analyst_recommendations
- holders (major + institutional)
- financial_statements (income, balance, cashflow - annual + quarterly)
- analyst_estimates (earnings, revenue - annual + quarterly)
- symbol_news
"""
import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import yfinance as yf
import pandas as pd
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

def get_active_symbols(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
        return [r['symbol'] for r in cur.fetchall()]

def safe_float(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None

def safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None

def upsert_recommendations(conn, symbol, recs):
    if recs is None or recs.empty:
        return
    with conn.cursor() as cur:
        for _, row in recs.iterrows():
            date_val = row.name[0]
            date = date_val.date() if hasattr(date_val, 'date') else date_val
            if not date:
                continue
            cur.execute("""
                INSERT IGNORE INTO analyst_recommendations
                    (symbol, firm, grade, price_target, action, rec_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                symbol,
                str(row.get('Firm', '')) or 'Unknown',
                row.get('To Grade') or row.get('Grade'),
                safe_float(row.get('Price Target')),
                str(row.get('Action')) or '',
                date,
            ))
    conn.commit()

def upsert_holders(conn, symbol, major, inst):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM holders WHERE symbol = %s AND fetch_date = CURDATE()", (symbol,))
        rows = []
        if major is not None and not major.empty:
            for _, row in major.iterrows():
                rows.append((
                    symbol, str(row.get('Holder', '')) or 'Major Holder', 'major',
                    safe_int(row.get('Shares')),
                    safe_float(row.get('% Out') or row.get('Percent Held')),
                    safe_int(row.get('Value')),
                    datetime.now().date(),
                ))
        if inst is not None and not inst.empty:
            for _, row in inst.iterrows():
                rows.append((
                    symbol, str(row.get('Holder', '')) or 'Institutional', 'institutional',
                    safe_int(row.get('Shares')),
                    safe_float(row.get('% Out') or row.get('Percent Held')),
                    safe_int(row.get('Value')),
                    datetime.now().date(),
                ))
        if rows:
            cur.executemany("""
                INSERT INTO holders (symbol, holder_name, holder_type, shares, percent_held, value, fetch_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, rows)
    conn.commit()

def upsert_financial_statements(conn, symbol, stmt_type, period_type, raw_df):
    if raw_df is None or raw_df.empty:
        return
    with conn.cursor() as cur:
        for col in raw_df.columns:
            try:
                fiscal_date = col.date()
            except AttributeError:
                continue
            data = raw_df[col].to_dict()
            clean = {}
            for k, v in data.items():
                key = str(k)
                try:
                    if pd.isna(v) or v != v:
                        clean[key] = None
                    else:
                        clean[key] = float(v) if isinstance(v, (int, float)) else str(v)
                except Exception:
                    clean[key] = None
            cur.execute("""
                INSERT INTO financial_statements (symbol, statement_type, period_type, fiscal_date, raw_data, fetch_date)
                VALUES (%s, %s, %s, %s, %s, CURDATE())
                ON DUPLICATE KEY UPDATE raw_data = VALUES(raw_data)
            """, (symbol, stmt_type, period_type, fiscal_date, json.dumps(clean)))
    conn.commit()

def upsert_estimates(conn, symbol, est_type, est_df):
    if est_df is None or est_df.empty:
        return
    with conn.cursor() as cur:
        for _, row in est_df.iterrows():
            period = row.name
            if hasattr(period, 'date'):
                period = period.date()
            elif hasattr(period, 'strftime'):
                period = period.strftime('%Y-%m-%d')
            else:
                period = str(period)
            cur.execute("""
                INSERT INTO analyst_estimates
                    (symbol, estimate_type, period_type, period, low_estimate, high_estimate, avg_estimate, num_analysts, fetch_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURDATE())
                ON DUPLICATE KEY UPDATE
                    low_estimate = VALUES(low_estimate),
                    high_estimate = VALUES(high_estimate),
                    avg_estimate = VALUES(avg_estimate),
                    num_analysts = VALUES(num_analysts)
            """, (
                symbol, est_type, 'annual', period,
                safe_float(row.get('low')), safe_float(row.get('high')), safe_float(row.get('mean') or row.get('avg')),
                safe_int(row.get('numberOfAnalysts')),
            ))
    conn.commit()

def upsert_fundamentals(conn, symbol, info):
    """Upsert summary-level fundamentals from yfinance .info dict into fundamentals table."""
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
        val = info.get(info_key)
        if val is not None:
            try:
                f = float(val) if not isinstance(val, str) else None
            except Exception:
                f = None
            if f is not None and f == f:  # not NaN
                set_parts.append(f"{col} = %s")
                params.append(f)
            elif isinstance(val, str) and val.strip():
                set_parts.append(f"{col} = %s")
                params.append(val.strip())
    if not set_parts:
        return
    params.extend([symbol, datetime.now().date()])
    sql = f"""
        INSERT INTO fundamentals (symbol, fetch_date, {', '.join(fields.keys())})
        VALUES (%s, %s, {', '.join(['NULL'] * len(fields))})
        ON DUPLICATE KEY UPDATE {', '.join(set_parts)}
    """
    # Build proper INSERT with actual values
    cols = ['symbol', 'fetch_date'] + list(fields.keys())
    placeholders = ['%s', '%s'] + ['%s'] * len(fields)
    values = [symbol, datetime.now().date()]
    for col in fields.values():
        values.append(info.get(col))
    sql = f"""
        INSERT INTO fundamentals ({', '.join(cols)})
        VALUES ({', '.join(placeholders)})
        ON DUPLICATE KEY UPDATE {', '.join(set_parts)}
    """
    with conn.cursor() as cur:
        cur.execute(sql, values)
    conn.commit()

def _extract_article(article):
    """Support both legacy flat yfinance news and the newer nested 'content' format."""
    content = article.get('content') if isinstance(article, dict) else None
    if isinstance(content, dict):
        title = content.get('title', '') or ''
        summary = content.get('summary', '') or ''
        pub = content.get('pubDate')
        publisher = ''
        provider = content.get('provider')
        if isinstance(provider, dict):
            publisher = provider.get('displayName', '') or ''
        # Prefer canonical, then clickThrough, then previewUrl
        link = ''
        for key in ('canonicalUrl', 'clickThroughUrl'):
            url_obj = content.get(key)
            if isinstance(url_obj, dict):
                link = url_obj.get('url', '') or ''
                if link:
                    break
    else:
        title = article.get('title', '') or ''
        summary = article.get('summary', '') or ''
        pub = article.get('published') or article.get('pubDate')
        publisher = article.get('publisher', '') or ''
        link = article.get('link', '') or ''
    return title, summary, pub, publisher, link


def upsert_news(conn, symbol, news):
    if not news:
        return
    with conn.cursor() as cur:
        for article in news:
            title, summary, pub, publisher, link = _extract_article(article)
            if isinstance(pub, datetime):
                pub = pub.strftime('%Y-%m-%d %H:%i:%s')
            # Skip articles without a URL and title
            if not title and not link:
                continue
            cur.execute("""
                INSERT IGNORE INTO symbol_news (symbol, title, url, source, summary, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (symbol, title, link, publisher, summary, pub))
    conn.commit()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbols', default=None, help='Comma-separated symbols to enrich')
    args = parser.parse_args()

    conn = pymysql.connect(**DB_CFG)
    symbols = get_active_symbols(conn)
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
    print(f"Active symbols: {len(symbols)}")

    done = 0
    errors = 0
    for sym in symbols:
        try:
            resolved = resolve_for_yfinance(sym)
            tk = yf.Ticker(resolved)
            # Recommendations
            try:
                recs = tk.recommendations
                if recs is not None and not recs.empty:
                    upsert_recommendations(conn, sym, recs)
            except Exception:
                pass

            # Holders
            try:
                maj = tk.major_holders
                inst = tk.institutional_holders
                if maj is not None and not maj.empty and inst is not None and not inst.empty:
                    upsert_holders(conn, sym, maj, inst)
            except Exception:
                pass

            # Financials
            for stmt_type, method in [
                ('income', lambda t: t.financials),
                ('balance', lambda t: t.balance_sheet),
                ('cashflow', lambda t: t.cash_flow),
            ]:
                try:
                    df = method(tk)
                    if df is not None and not df.empty:
                        upsert_financial_statements(conn, sym, stmt_type, 'annual', df)
                except Exception:
                    pass
                try:
                    q_df = getattr(method(tk), 'quarterly', None)
                    if q_df is not None and not q_df.empty:
                        upsert_financial_statements(conn, sym, stmt_type, 'quarterly', q_df)
                except Exception:
                    pass

            # Estimates
            try:
                eps = tk.earnings_estimate
                rev = tk.revenue_estimate
                if eps is not None and not eps.empty:
                    upsert_estimates(conn, sym, 'earnings', eps)
                if rev is not None and not rev.empty:
                    upsert_estimates(conn, sym, 'revenue', rev)
            except Exception:
                pass

            # News
            try:
                news = tk.news
                if news:
                    upsert_news(conn, sym, news)
            except Exception:
                pass

            # Fundamentals summary
            try:
                info = tk.info
                if info:
                    upsert_fundamentals(conn, sym, info)
            except Exception:
                pass

            done += 1
            if done % 50 == 0:
                print(f"  Processed {done}/{len(symbols)} ({sym})")
        except Exception as e:
            errors += 1
            print(f"  Error on {sym}: {e}")
        time.sleep(0.15)

    conn.close()
    print(f"Done. Processed: {done}, Errors: {errors}")

if __name__ == '__main__':
    main()
