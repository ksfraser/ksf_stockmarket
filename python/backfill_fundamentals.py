#!/usr/bin/env python3
"""
backfill_fundamentals.py — Promote older fundamental data for missing current-day fields.

For each symbol with a latest fundamentals row that has NULLs in key fields,
query the most recent prior fetch_date where each specific field IS NOT NULL,
and copy those values into the latest row.

Only fills NULLs; never overwrites existing valid data.
"""

import sys
import os
import pymysql

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
_cfg = Config(_cfg_path) if os.path.exists(_cfg_path) else Config()

DB_CFG = dict(
    host=_cfg.data.db_host,
    user=_cfg.data.db_user,
    password=_cfg.db_password,
    database=_cfg.data.db_name,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)

FIELDS = [
    'forward_pe', 'dividend_yield', 'beta',
    'trailing_pe', 'peg_ratio', 'price_to_book',
    'price_to_sales', 'book_value', 'free_cash_flow',
    'operating_cash_flow', 'total_revenue', 'revenue_growth',
    'gross_margin', 'operating_margin', 'profit_margin',
    'roe', 'roa', 'debt_to_equity', 'current_ratio', 'quick_ratio',
    'dividend_rate', 'annual_dividend_total', 'fcf_per_share',
    'dividend_fcf_coverage', 'five_year_div_yield', 'earnings_growth',
    'short_ratio', 'short_percent', 'insider_percent',
    'institutional_percent', 'shares_outstanding', 'float_shares',
    'sector', 'industry', 'payout_ratio', 'trailing_eps', 'forward_eps',
]


def main():
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT MAX(fetch_date) AS max_date FROM fundamentals')
            max_date = cur.fetchone()['max_date']
            if not max_date:
                print('No fundamentals data found.')
                return

            print(f'Latest fetch_date={max_date}')
            cur.execute('SELECT COUNT(*) AS cnt FROM fundamentals WHERE fetch_date = %s', (max_date,))
            print(f'Rows on latest date: {cur.fetchone()["cnt"]}')

            cur.execute('SELECT symbol FROM fundamentals WHERE fetch_date = %s', (max_date,))
            symbols = [r['symbol'] for r in cur.fetchall()]
            print(f'Symbols to check: {len(symbols)}')

            updated_symbols = []
            for sym in symbols:
                cur.execute('SELECT * FROM fundamentals WHERE symbol = %s AND fetch_date = %s', (sym, max_date))
                latest = cur.fetchone()
                if not latest:
                    continue

                null_fields = [f for f in FIELDS if latest.get(f) is None]
                if not null_fields:
                    continue

                updates = {}
                for fld in null_fields:
                    cur.execute(
                        f'SELECT {fld} FROM fundamentals WHERE symbol = %s AND {fld} IS NOT NULL ORDER BY fetch_date DESC LIMIT 1',
                        (sym,)
                    )
                    val = cur.fetchone()
                    if val and val.get(fld) is not None:
                        updates[fld] = val[fld]

                if not updates:
                    continue

                set_clause = ', '.join([f"{fld} = %s" for fld in updates])
                params = list(updates.values()) + [sym, max_date]
                cur.execute(f'UPDATE fundamentals SET {set_clause} WHERE symbol = %s AND fetch_date = %s', params)
                if cur.rowcount:
                    updated_symbols.append(sym)

            conn.commit()
            print(f'Updated {len(updated_symbols)} symbol rows: {updated_symbols}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
