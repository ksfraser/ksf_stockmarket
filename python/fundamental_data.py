#!/usr/bin/env python3
"""
fundamental_data.py — Fetch and store fundamental data for symbols.

Fetches from yfinance:
  - Payout ratio (dividends / earnings)
  - Debt-to-equity
  - ROE (return on equity)
  - Revenue growth
  - Free cash flow
  - Dividend yield
  - Sector/industry
  - Market cap
  - Book value
  - EPS (trailing and forward)
  - PE ratio
  - PEG ratio

Stores in fundamentals table keyed by symbol + quarter.

Usage:
    python3 fundamental_data.py --mode fetch --symbol AAPL
    python3 fundamental_data.py --mode fetch_all
    python3 fundamental_data.py --mode status
"""

import sys, os, json, argparse, time
import numpy as np
import pymysql
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

YFINANCE_AVAILABLE = False
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    pass


# ── Fundamental Data Fetcher ───────────────────────────────────────────────

class FundamentalFetcher:
    """
    Fetches fundamental data from yfinance and stores in MySQL.
    """

    # Mapping of our field names to yfinance info keys
    FIELD_MAP = {
        'market_cap': 'marketCap',
        'dividend_yield': 'dividendYield',
        'payout_ratio': 'payoutRatio',
        'trailing_eps': 'trailingEps',
        'forward_eps': 'forwardEps',
        'trailing_pe': 'trailingPE',
        'forward_pe': 'forwardPE',
        'peg_ratio': 'pegRatio',
        'price_to_book': 'priceToBook',
        'price_to_sales': 'priceToSalesTrailing12Months',
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

    def fetch_symbol(self, symbol: str) -> dict:
        """
        Fetch all available fundamental data for a symbol.
        Returns dict of {field: value}.
        """
        if not YFINANCE_AVAILABLE:
            return {'error': 'yfinance not available'}

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}

            result = {'symbol': symbol, 'fetch_date': str(date.today())}

            for our_key, yf_key in self.FIELD_MAP.items():
                val = info.get(yf_key)
                if val is not None:
                    if isinstance(val, (int, float)):
                        result[our_key] = float(val)
                    else:
                        result[our_key] = str(val)

            # Calculate additional fields
            # Total dividends paid (annual)
            if result.get('dividend_rate') and result.get('shares_outstanding'):
                result['annual_dividend_total'] = result['dividend_rate'] * result['shares_outstanding']

            # FCF per share
            if result.get('free_cash_flow') and result.get('shares_outstanding'):
                result['fcf_per_share'] = result['free_cash_flow'] / result['shares_outstanding']

            # Dividend coverage (FCF / dividends)
            if result.get('free_cash_flow') and result.get('annual_dividend_total'):
                if result['annual_dividend_total'] > 0:
                    result['dividend_fcf_coverage'] = result['free_cash_flow'] / result['annual_dividend_total']

            return result

        except Exception as e:
            return {'symbol': symbol, 'error': str(e)}

    def fetch_dividend_history(self, symbol: str) -> list:
        """Fetch dividend history for a symbol."""
        if not YFINANCE_AVAILABLE:
            return []
        try:
            ticker = yf.Ticker(symbol)
            divs = ticker.dividends
            results = []
            for date_idx, amount in divs.items():
                results.append({
                    'date': date_idx.strftime('%Y-%m-%d'),
                    'amount': float(amount)
                })
            return results
        except:
            return []

    def fetch_earnings_history(self, symbol: str) -> list:
        """Fetch earnings history from yfinance."""
        if not YFINANCE_AVAILABLE:
            return []
        try:
            ticker = yf.Ticker(symbol)
            # Get quarterly financials
            fin = ticker.quarterly_financials
            if fin is None or fin.empty:
                return []

            results = []
            for col in fin.columns:
                row_data = {'date': col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)}
                for idx in fin.index:
                    val = fin.loc[idx, col]
                    if val is not None:
                        row_data[idx] = float(val)
                results.append(row_data)
            return results
        except:
            return []


# ── Database Storage ────────────────────────────────────────────────────────

class FundamentalStore:
    """Stores and retrieves fundamental data from MySQL."""

    def __init__(self):
        self.conn = pymysql.connect(**MYSQL)
        self.cursor = self.conn.cursor()

    def close(self):
        self.conn.close()

    def create_table(self):
        """Create the fundamentals table if it doesn't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fundamentals (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                fetch_date DATE NOT NULL,
                market_cap DOUBLE NULL,
                dividend_yield DOUBLE NULL,
                payout_ratio DOUBLE NULL,
                trailing_eps DOUBLE NULL,
                forward_eps DOUBLE NULL,
                trailing_pe DOUBLE NULL,
                forward_pe DOUBLE NULL,
                peg_ratio DOUBLE NULL,
                price_to_book DOUBLE NULL,
                price_to_sales DOUBLE NULL,
                book_value DOUBLE NULL,
                free_cash_flow BIGINT NULL,
                operating_cash_flow BIGINT NULL,
                total_revenue BIGINT NULL,
                revenue_growth DOUBLE NULL,
                gross_margin DOUBLE NULL,
                operating_margin DOUBLE NULL,
                profit_margin DOUBLE NULL,
                roe DOUBLE NULL,
                roa DOUBLE NULL,
                debt_to_equity DOUBLE NULL,
                current_ratio DOUBLE NULL,
                quick_ratio DOUBLE NULL,
                dividend_rate DOUBLE NULL,
                annual_dividend_total DOUBLE NULL,
                fcf_per_share DOUBLE NULL,
                dividend_fcf_coverage DOUBLE NULL,
                five_year_div_yield DOUBLE NULL,
                earnings_growth DOUBLE NULL,
                beta DOUBLE NULL,
                short_ratio DOUBLE NULL,
                short_percent DOUBLE NULL,
                insider_percent DOUBLE NULL,
                institutional_percent DOUBLE NULL,
                shares_outstanding BIGINT NULL,
                float_shares BIGINT NULL,
                sector VARCHAR(50) NULL,
                industry VARCHAR(80) NULL,
                raw_json TEXT NULL,
                INDEX idx_symbol_date (symbol, fetch_date),
                INDEX idx_symbol (symbol),
                INDEX idx_sector (sector)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.conn.commit()
        print("✓ Fundamentals table created/verified")

    def upsert(self, data: dict):
        """Insert or update fundamental data for a symbol."""
        if not data or 'error' in data:
            return False

        # Build dynamic INSERT ... ON DUPLICATE KEY UPDATE
        # Use symbol + fetch_date as the unique key
        fields = ['symbol', 'fetch_date']
        values = [data.get('symbol'), data.get('fetch_date', str(date.today()))]
        updates = []

        field_list = [
            'market_cap', 'dividend_yield', 'payout_ratio', 'trailing_eps', 'forward_eps',
            'trailing_pe', 'forward_pe', 'peg_ratio', 'price_to_book', 'price_to_sales',
            'book_value', 'free_cash_flow', 'operating_cash_flow', 'total_revenue',
            'revenue_growth', 'gross_margin', 'operating_margin', 'profit_margin',
            'roe', 'roa', 'debt_to_equity', 'current_ratio', 'quick_ratio',
            'dividend_rate', 'annual_dividend_total', 'fcf_per_share', 'dividend_fcf_coverage',
            'five_year_div_yield', 'earnings_growth', 'beta', 'short_ratio', 'short_percent',
            'insider_percent', 'institutional_percent', 'shares_outstanding', 'float_shares',
            'sector', 'industry'
        ]

        for f in field_list:
            if f in data and data[f] is not None:
                fields.append(f)
                values.append(data[f])
                updates.append(f"{f}=VALUES({f})")

        # Store raw JSON
        fields.append('raw_json')
        values.append(json.dumps(data, default=str))
        updates.append("raw_json=VALUES(raw_json)")

        placeholders = ','.join(['%s'] * len(fields))
        update_clause = ','.join(updates)

        sql = f"INSERT INTO fundamentals ({','.join(fields)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"

        try:
            self.cursor.execute(sql, values)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            return False

    def get_latest(self, symbol: str) -> dict:
        """Get the latest fundamental data for a symbol."""
        self.cursor.execute("""
            SELECT * FROM fundamentals
            WHERE symbol = %s
            ORDER BY fetch_date DESC LIMIT 1
        """, (symbol,))
        return self.cursor.fetchone()

    def get_all_latest(self) -> list:
        """Get latest fundamentals for all symbols."""
        self.cursor.execute("""
            SELECT f.* FROM fundamentals f
            INNER JOIN (
                SELECT symbol, MAX(fetch_date) as max_date
                FROM fundamentals GROUP BY symbol
            ) latest ON f.symbol = latest.symbol AND f.fetch_date = latest.max_date
            ORDER BY f.symbol
        """)
        return self.cursor.fetchall()

    def get_dividend_safety(self, symbol: str) -> dict:
        """
        Calculate dividend safety score (0-100) for a symbol.
        Returns dict with score and component breakdown.
        """
        row = self.get_latest(symbol)
        if not row:
            return {'score': 50, 'reason': 'no_data', 'components': {}}

        score = 100
        components = {}

        # Payout ratio (30 points)
        payout = row.get('payout_ratio')
        if payout is not None:
            if payout > 1.0:
                score -= 40
                components['payout_ratio'] = ('CRITICAL', f'{payout:.0%} > 100%')
            elif payout > 0.8:
                score -= 20
                components['payout_ratio'] = ('WARNING', f'{payout:.0%} high')
            elif payout > 0.6:
                score -= 10
                components['payout_ratio'] = ('CAUTION', f'{payout:.0%}')
            else:
                components['payout_ratio'] = ('OK', f'{payout:.0%}')
        else:
            score -= 5
            components['payout_ratio'] = ('UNKNOWN', 'N/A')

        # FCF coverage (25 points)
        fcf_cov = row.get('dividend_fcf_coverage')
        if fcf_cov is not None:
            if fcf_cov < 0.5:
                score -= 35
                components['fcf_coverage'] = ('CRITICAL', f'{fcf_cov:.1f}x coverage')
            elif fcf_cov < 0.8:
                score -= 20
                components['fcf_coverage'] = ('WARNING', f'{fcf_cov:.1f}x coverage')
            elif fcf_cov < 1.0:
                score -= 10
                components['fcf_coverage'] = ('CAUTION', f'{fcf_cov:.1f}x coverage')
            else:
                components['fcf_coverage'] = ('OK', f'{fcf_cov:.1f}x coverage')
        else:
            score -= 5
            components['fcf_coverage'] = ('UNKNOWN', 'N/A')

        # Debt/Equity (20 points)
        de = row.get('debt_to_equity')
        if de is not None:
            if de > 2.0:
                score -= 20
                components['debt_equity'] = ('WARNING', f'{de:.1f}x')
            elif de > 1.5:
                score -= 10
                components['debt_equity'] = ('CAUTION', f'{de:.1f}x')
            else:
                components['debt_equity'] = ('OK', f'{de:.1f}x')
        else:
            score -= 5
            components['debt_equity'] = ('UNKNOWN', 'N/A')

        # Revenue growth (15 points)
        rev_g = row.get('revenue_growth')
        if rev_g is not None:
            if rev_g < -0.10:
                score -= 20
                components['revenue_growth'] = ('CRITICAL', f'{rev_g:.1%} decline')
            elif rev_g < 0:
                score -= 10
                components['revenue_growth'] = ('WARNING', f'{rev_g:.1%} decline')
            elif rev_g > 0.10:
                components['revenue_growth'] = ('STRONG', f'{rev_g:.1%} growth')
            else:
                components['revenue_growth'] = ('OK', f'{rev_g:.1%}')
        else:
            score -= 5
            components['revenue_growth'] = ('UNKNOWN', 'N/A')

        # Yield trap check (10 points)
        div_yield = row.get('dividend_yield')
        five_year = row.get('five_year_div_yield')
        if div_yield is not None and five_year is not None and five_year > 0:
            if div_yield > five_year * 2:
                score -= 15
                components['yield_trap'] = ('WARNING', f'Yield {div_yield:.1%} vs 5yr avg {five_year:.1%}')
            else:
                components['yield_trap'] = ('OK', f'{div_yield:.1%} vs 5yr {five_year:.1%}')
        else:
            components['yield_trap'] = ('N/A', '')

        score = max(0, min(100, score))

        # Overall rating
        if score >= 80:
            rating = 'SAFE'
        elif score >= 60:
            rating = 'MODERATE'
        elif score >= 40:
            rating = 'WARNING'
        else:
            rating = 'CRITICAL'

        return {
            'symbol': symbol,
            'score': score,
            'rating': rating,
            'components': components,
            'fetch_date': row.get('fetch_date'),
        }

    def create_dividends_table(self):
        """Create the dividends history table if it doesn't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                ex_date DATE NOT NULL,
                amount DOUBLE NOT NULL,
                INDEX idx_symbol_date (symbol, ex_date),
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.conn.commit()

    def store_dividends(self, symbol: str, dividends: list):
        """Store dividend history for a symbol."""
        for d in dividends:
            self.cursor.execute("""
                INSERT INTO dividends (symbol, ex_date, amount)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE amount = VALUES(amount)
            """, (symbol, d['date'], d['amount']))
        self.conn.commit()


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fundamental Data Fetcher')
    parser.add_argument('--mode', required=True, choices=['fetch', 'fetch_all', 'status', 'dividend_safety'])
    parser.add_argument('--symbol', help='Symbol to fetch')
    args = parser.parse_args()

    store = FundamentalStore()

    if args.mode == 'status':
        # Check what symbols have fundamental data
        store.cursor.execute("SELECT COUNT(DISTINCT symbol) as n FROM fundamentals")
        n = store.cursor.fetchone()['n']
        store.cursor.execute("SELECT COUNT(*) as n FROM fundamentals")
        total = store.cursor.fetchone()['n']
        print(f"Fundamental data: {n} symbols, {total} total rows")

        store.cursor.execute("""
            SELECT symbol, MAX(fetch_date) as latest
            FROM fundamentals GROUP BY symbol ORDER BY symbol LIMIT 10
        """)
        for r in store.cursor.fetchall():
            print(f"  {r['symbol']}: {r['latest']}")

    elif args.mode == 'fetch':
        if not args.symbol:
            print("Required: --symbol")
            sys.exit(1)
        store.create_table()
        store.create_dividends_table()
        fetcher = FundamentalFetcher()
        data = fetcher.fetch_symbol(args.symbol)
        if store.upsert(data):
            print(f"✓ Stored fundamentals for {args.symbol}")
            # Print key metrics
            for k in ['market_cap','dividend_yield','payout_ratio','roe','debt_to_equity','revenue_growth','trailing_pe']:
                if k in data:
                    print(f"  {k}: {data[k]}")
        else:
            print(f"✗ Failed to store {args.symbol}: {data.get('error', 'unknown')}")

        # Also fetch dividends
        divs = fetcher.fetch_dividend_history(args.symbol)
        if divs:
            store.store_dividends(args.symbol, divs)
            print(f"  Dividends: {len(divs)} payments stored")

    elif args.mode == 'fetch_all':
        store.create_table()
        store.create_dividends_table()
        fetcher = FundamentalFetcher()

        conn2 = pymysql.connect(**MYSQL)
        c = conn2.cursor()
        c.execute("SELECT symbol FROM symbol_master ORDER BY symbol")
        symbols = [r['symbol'] for r in c.fetchall()]
        conn2.close()

        total = len(symbols)
        ok = 0
        fail = 0
        for i, sym in enumerate(symbols):
            data = fetcher.fetch_symbol(sym)
            if store.upsert(data):
                ok += 1
            else:
                fail += 1
            if (i + 1) % 10 == 0:
                print(f"[{i+1}/{total}] ok={ok} fail={fail}")
            time.sleep(0.5)  # Rate limiting

        print(f"\nDone. {ok} ok, {fail} failed out of {total}")

    elif args.mode == 'dividend_safety':
        if not args.symbol:
            print("Required: --symbol")
            sys.exit(1)
        result = store.get_dividend_safety(args.symbol)
        print(f"\nDividend Safety for {args.symbol}: {result['score']}/100 ({result['rating']})")
        for comp, (status, detail) in result['components'].items():
            if detail:
                print(f"  {comp}: {status} — {detail}")

    store.close()
