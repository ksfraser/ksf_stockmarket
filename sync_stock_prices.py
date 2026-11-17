#!/usr/bin/env python3
"""sync_stock_prices.py — Intraday price sync to SQLite (ephemeral, non-MariaDB).

Syncs intraday OHLCV price data for the symbols in watchlist_symbols to the
SQLite price_intraday table (data/analysis_results.db).

Usage:
    sync_stock_prices.py --sqlite

This script intentionally writes NO data to MariaDB.
"""

import argparse
import logging
import sqlite3
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Ensure the KSF Python src packages are importable (project root on path).
REPO_ROOT = Path('/home/ksf_stockmarket/ksf_stockmarket')
SRC_DIR = REPO_ROOT / 'python' / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.paths import INTRADAY_PRICE_DB
from symbol_resolver import resolve_for_yfinance

import yfinance as yf

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MariaDB (read-only) — pull the symbols / exchange hints, never write
# ---------------------------------------------------------------------------

def _mysql_conn():
    import pymysql
    return pymysql.connect(
        host='ksfraser.ca',
        port=3306,
        user='ksfraser_stockmarket',
        password='Zaqwsx9sm1@',
        database='ksfraser_stock_market',
        charset='utf8mb4',
        connect_timeout=10,
        autocommit=True,
    )


def load_watchlist_symbols() -> List[str]:
    """Return the ordered list of watchlist symbol strings (read-only)."""
    conn = None
    try:
        conn = _mysql_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol FROM watchlist_symbols ORDER BY id"
            )
            return [r[0] for r in cur.fetchall()]
    except Exception as exc:
        logger.warning("load_watchlist_symbols: MariaDB read failed — %s", exc)
        return []
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Fetch + insert
# ---------------------------------------------------------------------------

def fetch_intraday_row(symbol: str, res: str) -> Optional[Dict]:
    """Fetch the most recent daily OHLCV row for one resolved symbol.

    Returns a dict suitable for INSERT OR REPLACE into price_intraday, or
    None when no data could be retrieved for the day.
    """
    if res is None or not res.strip():
        return None

    try:
        ticker = yf.Ticker(res.strip().upper())
        hist = ticker.history(period='5d', interval='1d', auto_adjust=False)
        if hist is None or hist.empty:
            return None
        # Latest row
        row = hist.iloc[-1]
        dt = row.name
        if hasattr(dt, 'tz_localize') and dt.tz is not None:
            dt = dt.tz_localize(None)
        if hasattr(dt, 'date'):
            d = dt.date()
        else:
            d = str(dt)[:10]
        close = float(row.get('Close', 0) or 0)
        high = float(row.get('High', close) or 0)
        low = float(row.get('Low', close) or 0)
        open_ = float(row.get('Open', close) or 0)
        volume = int(row.get('Volume', 0) or 0)
        return {
            'symbol': symbol.upper(),
            'price_date': d,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'currency': 'USD',
            'exchange': 'TSX',
            'unit_class': '',
        }
    except Exception as exc:
        logger.warning("fetch_intraday_row: %r -> %s", symbol, exc)
        return None


def sync_symbol(conn: sqlite3.Connection, symbol: str) -> Tuple[int, str]:
    """Fetch + upsert one symbol. Returns (rows_upserted, error_message)."""
    res = resolve_for_yfinance(symbol)
    if res is None:
        return 0, f"{symbol} -> resolution returned None"

    row = fetch_intraday_row(symbol, res)
    if row is None:
        return 0, f"{symbol} -> no data returned for {res}"

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO price_intraday
                (symbol, price_date, open, high, low, close, volume,
                 currency, exchange, unit_class)
            VALUES
                (:symbol, :price_date, :open, :high, :low, :close, :volume,
                 :currency, :exchange, :unit_class)
            ON CONFLICT(symbol, price_date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume,
                currency=excluded.currency, exchange=excluded.exchange,
                unit_class=excluded.unit_class,
                updated_at=CURRENT_TIMESTAMP
            """,
            row,
        )
        conn.commit()
        return 1, ""
    except Exception as exc:
        conn.rollback()
        logger.error("sync_symbol: %r -> %s", symbol, exc)
        return 0, f"{symbol} -> {exc}"
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Sync intraday prices to SQLite (ephemeral).'
    )
    parser.add_argument(
        '--sqlite', action='store_true',
        help='Write to SQLite (default behaviour; no MariaDB writes).',
    )
    args = parser.parse_args()

    if not args.sqlite:
        print('sync_stock_prices.py: only --sqlite is supported', file=sys.stderr)
        return 2

    # Determine the SQLite path from the config layer.
    sqlite_db = INTRADAY_PRICE_DB
    logger.info('sqlite_db=%s', sqlite_db)

    symbols = load_watchlist_symbols()
    n_watched = len(symbols)
    logger.info('watched symbols from watchlist_symbols: %d', n_watched)

    # Open the SQLite DB (create the tables if needed).
    conn = sqlite3.connect(str(sqlite_db))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS price_intraday ("
        " symbol TEXT NOT NULL,"
        " price_date DATE NOT NULL,"
        " open REAL, high REAL, low REAL, close REAL, volume INTEGER,"
        " currency TEXT DEFAULT 'USD',"
        " updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        " dividend REAL DEFAULT 0.0, base_symbol TEXT, exchange TEXT,"
        " unit_class TEXT,"
        " PRIMARY KEY (symbol, price_date)"
        ")"
    )
    conn.commit()

    n_upserted = 0
    resolution_errors: List[str] = []
    fetch_errors: List[str] = []

    for i, sym in enumerate(symbols, start=1):
        cnt, err = sync_symbol(conn, sym)
        if cnt:
            n_upserted += cnt
        if err:
            if 'resolution' in err.lower() or 'None' in err:
                resolution_errors.append(err)
            else:
                fetch_errors.append(err)
        logger.info(
            '[%d/%d] %s -> upserted=%d err=%s',
            i, n_watched, sym, cnt, err,
        )
        # Throttle slightly to avoid hammering the free tier of yfinance.
        if i < n_watched:
            time.sleep(0.25)

    conn.close()

    print('=' * 64)
    print('INTRADAY PRICE SYNC (SQLite, ephemeral) — COMPLETE')
    print('=' * 64)
    print(f'  Symbols watched     : {n_watched}')
    print(f'  Symbols with data   : {n_upserted}')
    print(f'  Rows upserted       : {n_upserted}')
    print(f'  Resolution errors   : {len(resolution_errors)}')
    if resolution_errors:
        for e in resolution_errors:
            print(f'    - {e}')
    print(f'  Fetch errors        : {len(fetch_errors)}')
    if fetch_errors:
        for e in fetch_errors:
            print(f'    - {e}')
    print(f'  SQLite DB           : {sqlite_db.resolve()}')
    print('=' * 64)

    return 0


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s %(name)s %(message)s',
    )
    sys.exit(main())
