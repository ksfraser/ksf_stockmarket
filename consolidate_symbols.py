#!/usr/bin/env python3
"""
Consolidate duplicate .TO symbols into bare symbols.
Merges data from RUS.TO -> RUS, MX.TO -> MX, VET.TO -> VET
across all relevant tables, then deletes the .TO rows.
"""
import os
import sys

# Ensure python/ and python/src/ are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python', 'src'))

import pymysql.cursors

# DB credentials from environment or .env
_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

conn = pymysql.connect(
    host=os.environ.get('DB_HOST', 'ksfraser.ca'),
    user=os.environ.get('DB_USER', 'ksfraser_stockmarket'),
    password=os.environ.get('DB_PASS', ''),
    database=os.environ.get('DB_NAME', 'ksfraser_stock_market'),
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=20,
    read_timeout=120,
    write_timeout=120,
)

pairs = [
    ('RUS.TO', 'RUS'),
    ('MX.TO', 'MX'),
    ('VET.TO', 'VET'),
]

# Tables where we merge by (symbol, date) or similar unique key
merge_tables = [
    ('stockprices', 'symbol', 'price_date'),
    ('indicators_json', 'symbol', 'price_date'),
    ('analyst_ratings', 'symbol', ['date', 'firm', 'action', 'rating', 'price_target']),
]

# Tables where we just insert all rows (id is auto_increment)
straight_tables = [
    'fundamentals',
    'analyst_recommendations',
    'analyst_targets',
]

with conn.cursor() as cur:
    for src, dst in pairs:
        print(f"\n=== {src} -> {dst} ===")
        
        # 1. Merge stockprices
        print(f"  Merging stockprices...")
        cur.execute("""
            INSERT IGNORE INTO stockprices (symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio)
            SELECT %s, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio
            FROM stockprices
            WHERE symbol = %s
        """, (dst, src))
        print(f"    stockprices: {cur.rowcount} rows merged")
        
        # 2. Merge indicators_json
        print(f"  Merging indicators_json...")
        cur.execute("""
            INSERT IGNORE INTO indicators_json (symbol, price_date, data)
            SELECT %s, price_date, data
            FROM indicators_json
            WHERE symbol = %s
        """, (dst, src))
        print(f"    indicators_json: {cur.rowcount} rows merged")
        
        # 3. Merge fundamentals (straight insert, no unique key conflict)
        print(f"  Merging fundamentals...")
        cur.execute("""
            INSERT INTO fundamentals (symbol, fetch_date, market_cap, dividend_yield, payout_ratio,
                trailing_eps, forward_eps, trailing_pe, forward_pe, peg_ratio, price_to_book,
                price_to_sales, book_value, free_cash_flow, operating_cash_flow, total_revenue,
                revenue_growth, gross_margin, operating_margin, profit_margin, roe, roa,
                debt_to_equity, current_ratio, quick_ratio, dividend_rate, annual_dividend_total,
                fcf_per_share, dividend_fcf_coverage, five_year_div_yield, earnings_growth, beta,
                short_ratio, short_percent, insider_percent, institutional_percent,
                shares_outstanding, float_shares, sector, industry, raw_json)
            SELECT symbol, fetch_date, market_cap, dividend_yield, payout_ratio,
                trailing_eps, forward_eps, trailing_pe, forward_pe, peg_ratio, price_to_book,
                price_to_sales, book_value, free_cash_flow, operating_cash_flow, total_revenue,
                revenue_growth, gross_margin, operating_margin, profit_margin, roe, roa,
                debt_to_equity, current_ratio, quick_ratio, dividend_rate, annual_dividend_total,
                fcf_per_share, dividend_fcf_coverage, five_year_div_yield, earnings_growth, beta,
                short_ratio, short_percent, insider_percent, institutional_percent,
                shares_outstanding, float_shares, sector, industry, raw_json
            FROM fundamentals
            WHERE symbol = %s
        """, (src,))
        print(f"    fundamentals: {cur.rowcount} rows merged")
        
        # 4. Merge analyst_ratings (unique key on symbol+date+firm+action+rating+price_target)
        print(f"  Merging analyst_ratings...")
        cur.execute("""
            INSERT IGNORE INTO analyst_ratings (symbol, date, firm, analyst_name, action, rating, price_target, prev_rating, prev_price_target)
            SELECT %s, date, firm, analyst_name, action, rating, price_target, prev_rating, prev_price_target
            FROM analyst_ratings
            WHERE symbol = %s
        """, (dst, src))
        print(f"    analyst_ratings: {cur.rowcount} rows merged")
        
        # 5. Merge analyst_recommendations
        print(f"  Merging analyst_recommendations...")
        cur.execute("""
            INSERT INTO analyst_recommendations (symbol, firm, grade, price_target, action, rec_date)
            SELECT %s, firm, grade, price_target, action, rec_date
            FROM analyst_recommendations
            WHERE symbol = %s
        """, (dst, src))
        print(f"    analyst_recommendations: {cur.rowcount} rows merged")
        
        # 6. Merge analyst_targets
        print(f"  Merging analyst_targets...")
        cur.execute("""
            INSERT INTO analyst_targets (ticker, date, target_price, current_price, recommendation, source)
            SELECT %s, date, target_price, current_price, recommendation, source
            FROM analyst_targets
            WHERE ticker = %s
        """, (dst, src))
        print(f"    analyst_targets: {cur.rowcount} rows merged")
        
        # 7. Delete .TO rows from all tables
        print(f"  Deleting {src} rows...")
        for tbl in ['stockprices', 'indicators_json', 'fundamentals', 'analyst_ratings', 'analyst_recommendations', 'analyst_targets']:
            if tbl == 'analyst_targets':
                cur.execute(f"DELETE FROM {tbl} WHERE ticker = %s", (src,))
            else:
                cur.execute(f"DELETE FROM {tbl} WHERE symbol = %s", (src,))
            deleted = cur.rowcount
            if deleted:
                print(f"    {tbl}: deleted {deleted} rows")
        
        conn.commit()
        print(f"  Done: {src} -> {dst}")

conn.close()
print("\nConsolidation complete.")
