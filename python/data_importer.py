#!/usr/bin/env python3
"""
data_importer.py — Stock Price & Fundamental Data Importer
==========================================================
Imports OHLCV price data and fundamental metadata into the partitioned
stockprices / stockinfo tables.

Modes (run_import):
    daily  — fetch latest prices via yfinance for all tracked symbols
    csv    — parse legacy CSV files from the currentdata/ directory
    full   — daily + csv

Every import operation is logged to data_import_log.

Usage:
    python3 data_importer.py                  # default daily mode
    python3 data_importer.py --mode csv       # CSV-only import
    python3 data_importer.py --mode full      # both
    python3 data_importer.py --mode daily --symbols AAPL,MSFT,RY.TO

DB columns (stockprices):
    symbol, price_date, day_open, day_high, day_low, day_close,
    previous_close, day_change, adj_close, volume, bid, ask, source, updated_at

Author:  ksf_stockmarket
"""

import argparse
import csv
import glob  # noqa: F401 (reserved for future glob-based features)
import logging
import os
import re
import sys
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any

import mysql.connector
from mysql.connector import Error as MySQLError

try:
    import yfinance as yf
except ImportError:
    yf = None  # graceful handling at function level

try:
    import pandas as pd
except ImportError:
    pd = None

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_CONFIG = {
    'host': 'localhost',
    'user': 'ksf_stockmarket',
    'password': 'change_me',
    'database': 'ksf_stockmarket',
    'charset': 'utf8mb4',
    'use_unicode': True,
    'autocommit': False,
}

BATCH_SIZE = 500  # rows per executemany batch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger('data_importer')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# TSX symbols: yfinance requires ".TO" suffix
TSX_PATTERN = re.compile(r'^[A-Z][A-Z0-9]*\.TO$', re.IGNORECASE)

def normalize_symbol(symbol: str) -> str:
    """Ensure TSX symbols carry the .TO suffix that yfinance expects."""
    symbol = symbol.strip().upper()
    if re.match(r'^[A-Z][A-Z0-9]*$', symbol) and '.' not in symbol:
        # If it looks like a TSX symbol (<=4 chars, no dot), append .TO
        if len(symbol) <= 4:
            return f"{symbol}.TO"
    return symbol


def get_conn(config: Optional[Dict] = None):
    """Return a new mysql.connector connection."""
    cfg = config or DB_CONFIG
    return mysql.connector.connect(**cfg)


def _df_to_prices_df(prices_df: Any, symbol: str) -> List[Dict]:
    """
    Convert a yfinance OHLCV DataFrame (indexed by date) into a list
    of normalised dicts ready for write_prices().
    """
    results = []
    for ts, row in prices_df.iterrows():
        # yfinance returns Timestamp index
        d = ts.date() if hasattr(ts, 'date') else ts
        results.append({
            'symbol': symbol.upper().replace('.TO', ''),
            'date': d,
            'open':   _safe_float(row.get('Open')),
            'high':   _safe_float(row.get('High')),
            'low':    _safe_float(row.get('Low')),
            'close':  _safe_float(row.get('Close')),
            'adj_close': _safe_float(row.get('Adj Close', row.get('Close'))),
            'volume': _safe_int(row.get('Volume')),
        })
    return results


def _safe_float(val) -> Optional[float]:
    """Return float or None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> Optional[int]:
    """Return int or None."""
    if val is None:
        return None
    try:
        i = int(float(val))
        return i
    except (TypeError, ValueError):
        return None


def log_import(
    cursor,
    import_type: str,
    symbol: str,
    records_before: int,
    records_after: int,
    records_added: int,
    status: str,
    error_message: str = None,
    duration_ms: int = 0,
):
    """Write a row to data_import_log."""
    sql = """
        INSERT INTO data_import_log
            (import_type, symbol, records_before, records_after,
             records_added, status, error_message, duration_ms, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    cursor.execute(sql, (
        import_type,
        symbol,
        records_before,
        records_after,
        records_added,
        status,
        error_message,
        duration_ms,
    ))


# ---------------------------------------------------------------------------
# 1. fetch_yfinance_prices
# ---------------------------------------------------------------------------

def fetch_yfinance_prices(
    symbols: List[str],
    period: str = '5d',
) -> List[Dict]:
    """
    Fetch the latest OHLCV rows for *symbols* via yfinance.

    Each returned dict carries keys:
        symbol, date, open, high, low, close, volume, adj_close

    TSX symbols without a ``.TO`` suffix are handled automatically.
    Errors are captured per-symbol so one failure does not abort the batch.
    """
    if yf is None:
        logger.error("yfinance is not installed. Run: pip install yfinance")
        return []

    all_prices: List[Dict] = []

    for raw_sym in symbols:
        start = time.time()
        sym = normalize_symbol(raw_sym)
        # The original symbol (without .TO) is stored in the DB
        db_symbol = sym.replace('.TO', '').upper()
        try:
            ticker = yf.Ticker(sym)
            # period='5d' gives enough rows to cover a weekend gap
            hist = ticker.history(period=period)

            if hist is None or hist.empty:
                logger.warning("No price data for %s (%s)", raw_sym, sym)
                elapsed_ms = int((time.time() - start) * 1000)
                _one_shot_log(  # will only write if a cursor/conn is available
                    None,
                    'yfinance', sym.replace('.TO', ''),
                    0, 0, 0, 'empty',
                    'No data returned', elapsed_ms,
                )
                continue

            rows = _df_to_prices_df(hist, db_symbol)
            logger.info("Fetched %d rows for %s (%s)", len(rows), raw_sym, sym)
            all_prices.extend(rows)

        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            logger.error("Failed to fetch %s: %s", raw_sym, exc)
            # Log in _one_shot_log will silently skip if no conn; run_import
            # also logs via _one_shot_log(conn,…) post-write.
        # Small delay to avoid hammering yfinance
        time.sleep(0.15)

    return all_prices


def _one_shot_log(conn, import_type, symbol, records_before, records_after,
                  records_added, status, error_message, duration_ms):
    """
    Utility that writes a log row to data_import_log.
    If *conn* is None, skip silently (used in fetch_yfinance_prices where no
    connection is available yet run_import will also log after write_prices).
    """
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        log_import(cursor, import_type, symbol,
                   records_before, records_after, records_added,
                   status, error_message, duration_ms)
        conn.commit()
        cursor.close()
    except Exception as exc:
        logger.warning("Could not write to data_import_log: %s", exc)


# ---------------------------------------------------------------------------
# 2. write_prices
# ---------------------------------------------------------------------------

def write_prices(
    conn,
    prices: List[Dict],
    source: str = 'yfinance',
) -> int:
    """
    Batch-INSERT *prices* into stockprices with ON DUPLICATE KEY UPDATE.

    For each incoming row we:
        - look up the previous day's close so we can populate previous_close
          and derive day_change
        - set *source* ('yfinance' | 'csv' | ...)
        - let updated_at default to NOW() (table default)

    Returns the number of rows actually inserted/updated.
    """
    if not prices:
        return 0

    cursor = conn.cursor()

    # Pre-fetch existing latest close per symbol to compute previous_close
    unique_symbols = {p['symbol'] for p in prices if p.get('symbol')}
    prev_close_map: Dict[str, float] = {}
    if unique_symbols:
        placeholders = ','.join(['%s'] * len(unique_symbols))
        # Get the latest close for each symbol prior to the import dates
        cursor.execute(f"""
            SELECT symbol, day_close
            FROM stockprices
            WHERE symbol IN ({placeholders})
            ORDER BY price_date DESC
        """, tuple(unique_symbols))
        seen = set()
        for row in cursor.fetchall():
            if row[0] not in seen:
                prev_close_map[row[0]] = row[1]
                seen.add(row[0])

        # Also count rows per symbol before import for logging
        cursor.execute(
            "SELECT COUNT(*) FROM stockprices WHERE symbol IN ({})".format(placeholders),
            tuple(unique_symbols),
        )
        _before_total = cursor.fetchone()[0]
    else:
        _before_total = 0

    insert_sql = """
        INSERT INTO stockprices
            (symbol, price_date, day_open, day_high, day_low, day_close,
             previous_close, day_change, adj_close, volume,
             bid, ask, source, updated_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            day_open       = VALUES(day_open),
            day_high       = VALUES(day_high),
            day_low        = VALUES(day_low),
            day_close      = VALUES(day_close),
            previous_close = VALUES(previous_close),
            day_change     = VALUES(day_change),
            adj_close      = VALUES(adj_close),
            volume         = VALUES(volume),
            bid            = VALUES(bid),
            ask            = VALUES(ask),
            source         = VALUES(source),
            updated_at     = NOW()
    """

    batch = []
    for p in prices:
        sym = p.get('symbol', '').upper()
        d = p.get('date')
        o = p.get('open')
        h = p.get('high')
        lo = p.get('low')
        c = p.get('close')
        adj = p.get('adj_close')
        vol = p.get('volume')

        # previous_close: last close we have for this symbol
        prev = prev_close_map.get(sym)
        if prev is None:
            # This is the first row for the symbol — use the same close
            prev = c

        # day_change = close - previous_close
        chg = None
        if c is not None and prev is not None:
            chg = round(c - prev, 4)

        batch.append((
            sym, d, o, h, lo, c,
            prev, chg, adj, vol,
            None, None,  # bid, ask — not available from yfinance
            source,
        ))

        # Update prev_close_map as we go for intra-batch previous_close
        # (yesterday's close within this batch can become previous_close
        #  for tomorrow's row in the same batch)
        if c is not None:
            prev_close_map[sym] = c

    inserted = 0
    try:
        # Execute in chunks
        for i in range(0, len(batch), BATCH_SIZE):
            chunk = batch[i:i + BATCH_SIZE]
            cursor.executemany(insert_sql, chunk)
            conn.commit()
            inserted += len(chunk)
    except MySQLError as exc:
        conn.rollback()
        logger.error("Batch insert failed: %s", exc)
        raise

    # Count after
    if unique_symbols:
        cursor.execute(
            "SELECT COUNT(*) FROM stockprices WHERE symbol IN ({})".format(
                ','.join(['%s'] * len(unique_symbols))
            ),
            tuple(unique_symbols),
        )
        _after_total = cursor.fetchone()[0]
    else:
        _after_total = _before_total

    added = _after_total - _before_total
    logger.info("write_prices: %d rows written, %d new records", inserted, added)

    cursor.close()
    return inserted


# ---------------------------------------------------------------------------
# 3. fetch_fundamentals
# ---------------------------------------------------------------------------

# Map yfinance info keys → stockinfo columns
FUNDAMENTAL_MAP = {
    'marketCap':          'marketcap',
    'sector':             'sector',
    'industry':           'industry',
    'longName':           'corporatename',
    'shortName':          'corporatename',
    'trailingPE':         'peratio',
    'dividendYield':      None,  # not in stockinfo schema
    'fiftyTwoWeekHigh':   'yearhigh',
    'fiftyTwoWeekLow':    'yearlow',
    'averageVolume':      'averagevolume',
    'regularMarketVolume':'dailyvolume',
    'trailingEps':        'EPS',
    'bookValue':          None,
    'priceToBook':        None,
    'exchange':           None,   # mapped separately via stockexchange
}

INSERT_STOCKINFO_SQL = """
    INSERT INTO stockinfo
        (stocksymbol, corporatename, sector, industry, peratio,
         yearhigh, yearlow, averagevolume, dailyvolume, EPS,
         marketcap, currentprice, `high`, `low`, reviseddate)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON DUPLICATE KEY UPDATE
        corporatename = COALESCE(VALUES(corporatename), corporatename),
        sector        = COALESCE(NULLIF(VALUES(sector), ''), sector),
        industry      = COALESCE(NULLIF(VALUES(industry), ''), industry),
        peratio       = COALESCE(VALUES(peratio), peratio),
        yearhigh      = COALESCE(VALUES(yearhigh), yearhigh),
        yearlow       = COALESCE(VALUES(yearlow), yearlow),
        averagevolume = COALESCE(VALUES(averagevolume), averagevolume),
        dailyvolume   = COALESCE(VALUES(dailyvolume), dailyvolume),
        EPS           = COALESCE(VALUES(EPS), EPS),
        marketcap     = COALESCE(VALUES(marketcap), marketcap),
        currentprice  = COALESCE(VALUES(currentprice), currentprice),
        `high`        = COALESCE(VALUES(`high`), `high`),
        `low`         = COALESCE(VALUES(`low`), `low`),
        reviseddate   = NOW()
"""


def fetch_fundamentals(
    symbols: List[str],
    conn=None,
) -> int:
    """
    Fetch fundamental info for *symbols* via yfinance and upsert into stockinfo.

    Returns the number of symbols successfully updated.

    If *conn* is provided the function writes directly; otherwise a new
    connection is opened using DB_CONFIG.
    """
    if yf is None:
        logger.error("yfinance is not installed.")
        return 0

    close_after = conn is None
    if conn is None:
        conn = get_conn()

    cursor = conn.cursor()
    updated = 0

    for raw_sym in symbols:
        sym = normalize_symbol(raw_sym)
        db_sym = sym.replace('.TO', '').upper()
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info or {}

            if not info:
                logger.warning("No info returned for %s", raw_sym)
                continue

            corporatename = (
                info.get('longName')
                or info.get('shortName')
                or db_sym
            )
            sector = info.get('sector') or None
            industry = info.get('industry') or None
            peratio = _safe_float(info.get('trailingPE'))
            yearhigh = _safe_float(info.get('fiftyTwoWeekHigh'))
            yearlow = _safe_float(info.get('fiftyTwoWeekLow'))
            avg_vol = _safe_int(info.get('averageVolume'))
            daily_vol = _safe_int(info.get('regularMarketVolume'))
            eps = _safe_float(info.get('trailingEps'))
            marketcap = _safe_float(info.get('marketCap'))
            currentprice = _safe_float(info.get('regularMarketPrice')
                                       or info.get('currentPrice'))
            high = _safe_float(info.get('dayHigh'))
            low = _safe_float(info.get('dayLow'))

            cursor.execute(INSERT_STOCKINFO_SQL, (
                db_sym,
                corporatename,
                sector,
                industry,
                peratio,
                yearhigh,
                yearlow,
                avg_vol,
                daily_vol,
                eps,
                marketcap,
                currentprice,
                high,
                low,
            ))
            conn.commit()
            updated += 1
            logger.info("Updated fundamentals for %s", db_sym)

        except MySQLError as exc:
            conn.rollback()
            logger.error("DB error writing fundamentals for %s: %s", raw_sym, exc)
        except Exception as exc:
            logger.error("Failed fundamentals for %s: %s", raw_sym, exc)

        time.sleep(0.2)

    cursor.close()
    if close_after and conn.is_connected():
        conn.close()

    logger.info("fetch_fundamentals: %d/%d symbols updated", updated, len(symbols))
    return updated


# ---------------------------------------------------------------------------
# 4. import_csv
# ---------------------------------------------------------------------------

# Expected CSV column names (flexible matching)
CSV_COLUMN_MAP = {
    'date':        ['date', 'Date', 'DATE', 'timestamp'],
    'open':        ['open', 'Open', 'OPEN', 'open_price'],
    'high':        ['high', 'High', 'HIGH'],
    'low':         ['low', 'Low', 'LOW'],
    'close':       ['close', 'Close', 'CLOSE', 'adj close', 'adj_close',
                    'adjustedclose', 'Adj Close'],
    'adj_close':   ['adj close', 'adj_close', 'Adj Close', 'adjustedclose',
                    'Adjusted Close', 'close'],
    'volume':      ['volume', 'Volume', 'VOLUME', 'vol', 'Vol'],
    'previous_close': ['previous_close', 'prev close', 'Prev Close',
                       'previousclose'],
    'day_change':  ['day_change', 'day change', 'Day Change', 'change'],
}


def _resolve_column(header: List[str], target: str) -> Optional[int]:
    """Return the index of the column that matches *target* (case-insensitive)."""
    candidates = CSV_COLUMN_MAP.get(target, [target])
    for c in candidates:
        for i, h in enumerate(header):
            if h.strip().lower() == c.strip().lower():
                return i
    return None


def _parse_csv_date(val: str) -> Optional[date]:
    """Try common date formats."""
    for fmt in (
        '%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y',
        '%m-%d-%Y', '%Y%m%d', '%b %d, %Y', '%d-%b-%Y',
    ):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    return None


def import_csv(
    csv_dir: str,
    conn=None,
) -> int:
    """
    Parse all *.csv files in *csv_dir*, treating each file as historical OHLCV
    data for one symbol (derived from the filename).

    Batch-inserts into stockprices with source='csv'.

    Returns the total number of rows imported.
    """
    close_after = conn is None
    if conn is None:
        conn = get_conn()

    csv_path = Path(csv_dir)
    if not csv_path.is_dir():
        logger.error("CSV directory not found: %s", csv_dir)
        if close_after:
            conn.close()
        return 0

    files = sorted(csv_path.glob('*.csv'))
    if not files:
        logger.warning("No CSV files found in %s", csv_dir)
        if close_after:
            conn.close()
        return 0

    total_imported = 0

    for fpath in files:
        # Symbol = filename without extension
        sym = fpath.stem.upper().replace('.TO', '')
        logger.info("Importing %s from %s", sym, fpath.name)

        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as fh:
                reader = csv.reader(fh)
                header = next(reader)

                idx = {
                    'date':        _resolve_column(header, 'date'),
                    'open':        _resolve_column(header, 'open'),
                    'high':        _resolve_column(header, 'high'),
                    'low':         _resolve_column(header, 'low'),
                    'close':       _resolve_column(header, 'close'),
                    'adj_close':   _resolve_column(header, 'adj_close'),
                    'volume':      _resolve_column(header, 'volume'),
                    'previous_close': _resolve_column(header, 'previous_close'),
                    'day_change':  _resolve_column(header, 'day_change'),
                }

                if idx['date'] is None:
                    logger.warning(
                        "No date column found in %s (header: %s). Skipping.",
                        fpath.name, header,
                    )
                    continue

                rows_raw = []
                for row in reader:
                    if not row or not row[idx['date']].strip():
                        continue
                    d = _parse_csv_date(row[idx['date']])
                    if d is None:
                        continue
                    rows_raw.append({
                        'symbol': sym,
                        'date': d,
                        'open': _safe_float(row[idx['open']]) if idx['open'] is not None else None,
                        'high': _safe_float(row[idx['high']]) if idx['high'] is not None else None,
                        'low': _safe_float(row[idx['low']]) if idx['low'] is not None else None,
                        'close': _safe_float(row[idx['close']]) if idx['close'] is not None else None,
                        'adj_close': _safe_float(row[idx['adj_close']]) if idx['adj_close'] is not None else None,
                        'volume': _safe_int(row[idx['volume']]) if idx['volume'] is not None else None,
                        'previous_close': _safe_float(row[idx['previous_close']]) if idx['previous_close'] is not None else None,
                        'day_change': _safe_float(row[idx['day_change']]) if idx['day_change'] is not None else None,
                    })

            if not rows_raw:
                logger.warning("No data rows in %s", fpath.name)
                continue

            n = write_prices(conn, rows_raw, source='csv')
            total_imported += n
            logger.info("Imported %d rows from %s", n, fpath.name)

        except Exception as exc:
            logger.error("Error importing %s: %s", fpath.name, exc)
            try:
                conn.rollback()
            except Exception:
                pass

    if close_after and conn.is_connected():
        conn.close()

    logger.info("import_csv: %d total rows imported", total_imported)
    return total_imported


# ---------------------------------------------------------------------------
# 5. run_import  (main entry point)
# ---------------------------------------------------------------------------

def _get_all_symbols(conn) -> List[str]:
    """Return a distinct list of all symbols currently tracked in stockprices."""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM stockprices")
    syms = [row[0] for row in cursor.fetchall() if row[0]]
    cursor.close()
    return syms


def _ensure_data_import_log_table(conn):
    """Create data_import_log if it does not already exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `data_import_log` (
            `id`            INT AUTO_INCREMENT PRIMARY KEY,
            `import_type`   ENUM('csv', 'yfinance', 'manual', 'full') NOT NULL DEFAULT 'manual',
            `symbol`        VARCHAR(20) NULL,
            `records_before` INT NOT NULL DEFAULT 0,
            `records_after`  INT NOT NULL DEFAULT 0,
            `records_added`  INT NOT NULL DEFAULT 0,
            `status`        ENUM('running', 'ok', 'error', 'empty') NOT NULL DEFAULT 'running',
            `error_message` TEXT NULL,
            `duration_ms`   INT NOT NULL DEFAULT 0,
            `created_at`    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    """)
    conn.commit()
    cursor.close()


def run_import(
    mode: str = 'daily',
    symbols: Optional[List[str]] = None,
    csv_dir: Optional[str] = None,
    db_config: Optional[Dict] = None,
):
    """
    Main entry point.

    Parameters
    ----------
    mode   – 'daily' (default), 'csv', or 'full'
    symbols – explicit list of symbols; if None all symbols from stockprices
              are auto-discovered
    csv_dir – path to CSV directory (used for / defaults csv and full modes)
    db_config – override DB_CONFIG
    """
    cfg = db_config or DB_CONFIG
    start = time.time()
    conn = get_conn(cfg)

    _ensure_data_import_log_table(conn)

    if symbols is None:
        symbols = _get_all_symbols(conn)

    logger.info("run_import: mode=%s, %d symbols", mode, len(symbols))

    # ---- Daemon tracking: log running status ----
    log_cursor = conn.cursor()
    log_import(log_cursor, mode if mode != 'full' else 'full',
               None, 0, 0, 0, 'running', None, 0)
    conn.commit()
    running_log_id = log_cursor.lastrowid
    log_cursor.close()

    error_msg = None
    total_added = 0
    total_before = 0
    total_after = 0

    try:
        if mode in ('daily', 'full', 'yfinance'):
            if not symbols:
                logger.warning("No symbols to fetch; skipping yfinance step.")
            else:
                logger.info("Fetching yfinance prices for %d symbols…", len(symbols))
                prices = fetch_yfinance_prices(symbols)

                # Count before
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM stockprices")
                total_before = cur.fetchone()[0]
                cur.close()

                if prices:
                    n = write_prices(conn, prices, source='yfinance')
                    total_added += n
                    logger.info("Wrote %d price rows from yfinance.", n)

                    # Also refresh fundamentals for these symbols
                    logger.info("Fetching fundamentals for %d symbols…", len(symbols))
                    fetch_fundamentals(symbols, conn)
                else:
                    logger.info("No prices returned from yfinance.")

                # Count after
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM stockprices")
                total_after = cur.fetchone()[0]
                cur.close()

                # Log yfinance import
                elapsed = int((time.time() - start) * 1000)
                log_cursor = conn.cursor()
                log_import(log_cursor, 'yfinance', None,
                           total_before, total_after,
                           total_after - total_before,
                           'ok' if prices else 'empty',
                           None, elapsed)
                conn.commit()
                log_cursor.close()

        if mode in ('csv', 'full'):
            csv_path = csv_dir or os.path.join(
                os.path.dirname(__file__), '..', '..', 'currentdata',
            )
            logger.info("Importing CSV files from %s…", csv_path)

            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM stockprices")
            csv_before = cur.fetchone()[0]
            cur.close()

            n = import_csv(csv_path, conn)
            total_added += n

            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM stockprices")
            csv_after = cur.fetchone()[0]
            cur.close()

            elapsed = int((time.time() - start) * 1000)
            log_cursor = conn.cursor()
            log_import(log_cursor, 'csv', None,
                       csv_before, csv_after,
                       csv_after - csv_before,
                       'ok' if n else 'empty',
                       None, elapsed)
            conn.commit()
            log_cursor.close()

    except Exception as exc:
        error_msg = str(exc)
        logger.error("run_import failed: %s", exc, exc_info=True)
        # Update running log to error
        if running_log_id:
            cur = conn.cursor()
            cur.execute(
                "UPDATE data_import_log SET status='error', "
                "error_message=%s, duration_ms=%s WHERE id=%s",
                (error_msg, int((time.time() - start) * 1000), running_log_id),
            )
            conn.commit()
            cur.close()
        raise

    finally:
        # Finalise the running log entry
        if running_log_id:
            cur = conn.cursor()
            cur.execute(
                "UPDATE data_import_log SET status=%s, records_after=%s, "
                "records_added=%s, duration_ms=%s, error_message=%s "
                "WHERE id=%s",
                (
                    'error' if error_msg else 'ok',
                    total_after or total_after,
                    total_added,
                    int((time.time() - start) * 1000),
                    error_msg,
                    running_log_id,
                ),
            )
            conn.commit()
            cur.close()

        if conn.is_connected():
            conn.close()

    elapsed = int((time.time() - start) * 1000)
    logger.info("run_import complete in %d ms — %d rows added.", elapsed, total_added)
    return total_added


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Import stock price data and fundamentals into ksf_stockmarket DB',
    )
    parser.add_argument(
        '--mode', default='daily',
        choices=['daily', 'csv', 'full', 'yfinance'],
        help='Import mode (default: daily)',
    )
    parser.add_argument(
        '--symbols', type=str, default=None,
        help='Comma-separated list of symbols (overrides auto-discovery)',
    )
    parser.add_argument(
        '--csv-dir', type=str, default=None,
        help='Directory containing CSV files (default: ../../currentdata)',
    )
    parser.add_argument(
        '--host', type=str, default=DB_CONFIG['host'],
    )
    parser.add_argument(
        '--user', type=str, default=DB_CONFIG['user'],
    )
    parser.add_argument(
        '--password', type=str, default=DB_CONFIG['password'],
    )
    parser.add_argument(
        '--database', type=str, default=DB_CONFIG['database'],
    )
    parser.add_argument(
        '--period', type=str, default='5d',
        help='yfinance period (default: 5d)',
    )

    args = parser.parse_args()

    # Override DB_CONFIG with CLI args
    db_cfg = {
        'host': args.host,
        'user': args.user,
        'password': args.password,
        'database': args.database,
        'charset': 'utf8mb4',
        'use_unicode': True,
        'autocommit': False,
    }

    symbols = [s.strip() for s in args.symbols.split(',')] if args.symbols else None

    run_import(
        mode=args.mode,
        symbols=symbols,
        csv_dir=args.csv_dir,
        db_config=db_cfg,
    )


if __name__ == '__main__':
    main()
