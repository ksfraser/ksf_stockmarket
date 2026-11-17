#!/usr/bin/env python3
"""
Data Cache Layer — 10 years daily OHLCV + dividends + splits
Caches to SQLite for fast backtesting without repeated yfinance calls.

Schema:
  daily_prices: date, ticker, open, high, low, close, volume
  dividends:   date, ticker, amount
  splits:      date, ticker, ratio (e.g., 2.0 = 2:1 split)
  corporate_actions: date, ticker, action_type, value
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from db.dao.base import BaseDAO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))  # src/
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'indicators'))  # src/indicators/

from investment_monitor import SymbolResolver
from analysis_db import get_db


class DataCache(BaseDAO):
    """Manages local cache of 10 years of daily price data."""

    CACHE_DB = os.path.expanduser('~/.hermes/cache/price_cache.db')
    RESOLVER = SymbolResolver()

    def __init__(self):
        super().__init__(db_path=self.CACHE_DB)
        self.conn = self._conn()
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            );
            CREATE TABLE IF NOT EXISTS dividends (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                PRIMARY KEY (ticker, date)
            );
            CREATE TABLE IF NOT EXISTS splits (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                ratio REAL NOT NULL,
                PRIMARY KEY (ticker, date)
            );
            CREATE TABLE IF NOT EXISTS cache_meta (
                ticker TEXT PRIMARY KEY,
                last_updated TEXT,
                n_days INTEGER,
                start_date TEXT,
                end_date TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_prices_ticker ON daily_prices(ticker);
            CREATE INDEX IF NOT EXISTS idx_prices_date ON daily_prices(date);
        """)
        self.conn.commit()

    def is_cached(self, ticker: str, min_days: int = 2000) -> bool:
        """Check if we have sufficient cached data for a ticker."""
        row = self.conn.execute(
            "SELECT n_days FROM cache_meta WHERE ticker = ?", (ticker,)
        ).fetchone()
        return row is not None and row[0] >= min_days

    def refresh_ticker(self, ticker: str, period: str = '10y') -> bool:
        """Fetch and cache data for a single ticker."""
        resolved = self.RESOLVER.resolve(ticker)
        try:
            stock = yf.Ticker(resolved)
            hist = stock.history(period=period)

            if hist.empty or len(hist) < 100:
                print(f"  {ticker}: insufficient data ({len(hist) if not hist.empty else 0} days)")
                return False

            # Normalize index
            hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index

            # Store prices
            for dt, row in hist.iterrows():
                date_str = str(dt.date())
                self.conn.execute("""
                    INSERT OR REPLACE INTO daily_prices (ticker, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ticker, date_str,
                      float(row['Open']), float(row['High']),
                      float(row['Low']), float(row['Close']),
                      int(row['Volume'])))

            # Store dividends
            divs = stock.dividends
            if divs is not None and len(divs) > 0:
                divs.index = divs.index.tz_localize(None) if divs.index.tz else divs.index
                for dt, amount in divs.items():
                    self.conn.execute("""
                        INSERT OR REPLACE INTO dividends (ticker, date, amount)
                        VALUES (?, ?, ?)
                    """, (ticker, str(dt.date()), float(amount)))

            # Store splits
            splits = stock.splits
            if splits is not None and len(splits) > 0:
                splits.index = splits.index.tz_localize(None) if splits.index.tz else splits.index
                for dt, ratio in splits.items():
                    self.conn.execute("""
                        INSERT OR REPLACE INTO splits (ticker, date, ratio)
                        VALUES (?, ?, ?)
                    """, (ticker, str(dt.date()), float(ratio)))

            # Update meta
            self.conn.execute("""
                INSERT OR REPLACE INTO cache_meta (ticker, last_updated, n_days, start_date, end_date)
                VALUES (?, ?, ?, ?, ?)
            """, (ticker, datetime.now().isoformat(), len(hist),
                  str(hist.index[0].date()), str(hist.index[-1].date())))

            self.conn.commit()
            print(f"  {ticker}: cached {len(hist)} days, {len(divs) if divs is not None else 0} divs, {len(splits) if splits is not None else 0} splits")
            return True

        except Exception as e:
            print(f"  {ticker}: ERROR — {e}")
            return False

    def refresh_all(self, tickers: List[str]):
        """Refresh cache for all tickers."""
        print(f"Refreshing data cache for {len(tickers)} tickers...")
        ok = 0
        for ticker in tickers:
            if self.refresh_ticker(ticker):
                ok += 1
        print(f"Cached {ok}/{len(tickers)} tickers successfully")

    def get_prices(self, ticker: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Get cached prices as DataFrame with standard yfinance column names."""
        query = "SELECT date, open, high, low, close, volume FROM daily_prices WHERE ticker = ?"
        params = [ticker]
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        query += " ORDER BY date"

        df = pd.read_sql_query(query, self.conn, params=params, index_col='date', parse_dates=['date'])
        # Rename to match yfinance/TechnicalAnalyzer expected format
        df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
        return df

    def get_dividends(self, ticker: str) -> pd.DataFrame:
        """Get cached dividends."""
        return pd.read_sql_query(
            "SELECT date, amount FROM dividends WHERE ticker = ? ORDER BY date",
            self.conn, params=[ticker], index_col='date', parse_dates=['date']
        )

    def get_splits(self, ticker: str) -> pd.DataFrame:
        """Get cached splits."""
        return pd.read_sql_query(
            "SELECT date, ratio FROM splits WHERE ticker = ? ORDER BY date",
            self.conn, params=[ticker], index_col='date', parse_dates=['date']
        )

    def get_mid_price(self, ticker: str, date_str: str) -> Optional[float]:
        """Get mid price (average of high and low) for a date — for hypothetical execution."""
        row = self.conn.execute(
            "SELECT high, low FROM daily_prices WHERE ticker = ? AND date = ?",
            (ticker, date_str)
        ).fetchone()
        if row:
            return (row[0] + row[1]) / 2.0
        return None

    def get_all_tickers(self) -> List[str]:
        """Get list of all cached tickers."""
        rows = self.conn.execute("SELECT ticker FROM cache_meta").fetchall()
        return [r[0] for r in rows]


def main():
    """Refresh cache for all portfolio tickers."""
    try:
        with open('/tmp/portfolio_from_email.json', 'r') as f:
            portfolio = json.load(f)
        tickers = list(portfolio.keys())
    except:
        print("No portfolio file found. Using default tickers.")
        tickers = ['RY', 'CM', 'CNR', 'TD', 'BMO', 'ENB', 'BPF.UN', 'SRV.UN',
                    'FEZ', 'IEV', 'SPEU', 'MX', 'RGLD', 'UL', 'CDZ', 'PZA',
                    'WJX', 'MTY', 'TFII', 'RUS', 'KEG.UN', 'PDC']

    cache = DataCache()
    cache.refresh_all(tickers)

    # Summary
    print("\nCache summary:")
    for ticker in tickers:
        if cache.is_cached(ticker):
            meta = cache.conn.execute(
                "SELECT n_days, start_date, end_date FROM cache_meta WHERE ticker = ?",
                (ticker,)
            ).fetchone()
            print(f"  {ticker}: {meta[0]} days ({meta[1]} to {meta[2]})")
        else:
            print(f"  {ticker}: NOT CACHED")


if __name__ == '__main__':
    main()
