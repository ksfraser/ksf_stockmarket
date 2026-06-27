#!/usr/bin/env python3
"""
batch_discover_inactive.py — Probe inactive symbols with yfinance batch download.

Strategy:
  1. Read all inactive symbols with candidates that could be valid tickers.
  2. De-duplicate candidates.
  3. Probe in chunks using yf.download(tickers=chunk, start=..., end=..., threads=False).
     Use a short date range (last 5 days) so probes are fast.
  4. For symbols that return data:
       - reactivate symbol_master row (or rename to cleaned symbol)
       - insert prices into stockprices
       - publish prices_loaded event to trigger downstream (news/fundamentals/TA)
  5. For symbols that still fail: leave inactive/reason untouched.

Rate limiting:
  - Sleep between chunks to avoid hammering Yahoo (8s between 50-symbol chunks).
  - The probe is lightweight (5 days, no threads).
"""

import sys
from pathlib import Path

_PYTHON_DIR = Path(__file__).resolve().parent / 'python'
_PYTHON_SRC = _PYTHON_DIR / 'src'
for _p in (str(_PYTHON_DIR), str(Path(__file__).resolve().parent), str(_PYTHON_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import os
import time
import logging
from datetime import date, timedelta

import pymysql
from db.mysql_adapter import MySQLConnection
import yfinance as yf
import pandas as pd
from config_loader import Config

from src.events.publisher import EventPublisher
from lifecycle.state import SymbolState
from lifecycle.repository import SymbolLifecycleRepository

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('batch_discover')

CFG_PATH = Path(__file__).resolve().parent / 'config.yaml'
cfg = Config(str(CFG_PATH))

MYSQL = dict(
    host=cfg.data.db_host,
    user=cfg.data.db_user,
    password=cfg.db_password,
    database=cfg.data.db_name,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=20,
    read_timeout=120,
    write_timeout=120,
)

# Patterns that are NOT resolvable regardless of prefix stripping
_UNRESOLVABLE_SUFFIXES = tuple(
    f for f in (
        '/PD.TO', '/PB.TO', '/PE.TO', '/PF.TO', '/PG.TO', '/PH.TO', '/PI.TO',
        '/PJ.TO', '/PK.TO', '/PL.TO', '/PM.TO', '/PN.TO', '/PO.TO', '/PQ.TO',
        '/PS.TO', '/PT.TO',
    )
)

_PREFIXES = [
    'AMEX:', 'NYSE:', 'NASDAQ:', 'TSX:', 'TSXV:', 'NEO:', 'OTC:',
    'LSE:', 'HKEX:', 'ASX:', 'CSE:', 'SSE:', 'SZSE:',
]


def _is_bad_suffix(sym: str) -> bool:
    return sym.endswith(_UNRESOLVABLE_SUFFIXES)


def generate_candidates(symbol: str):
    candidates = []
    s = symbol

    for prefix in _PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break

    original = symbol

    # For US/OTC prefixes, if the stripped symbol ends with .TO, trying
    # the plain symbol (without .TO) is usually the correct Yahoo ticker.
    # List that variant first so it gets probed and selected in preference to the .TO form.
    if original.startswith(('AMEX:', 'NYSE:', 'NASDAQ:', 'OTC:')) and s.endswith('.TO'):
        candidates.append(s[:-3])

    candidates.append(s)

    if original.startswith('NEO:') and not s.endswith('.TO'):
        candidates.append(s + '.TO')

    if original.startswith('NEO:') and s.endswith('.TO'):
        # Keep stripped-but-with-.TO as an alternative when NEO is present
        pass

    if original.startswith('OTC:') and s.endswith('.TO'):
        candidates.append(s[:-3] + '-F')

    if s.endswith('.HK.HK'):
        candidates.append(s[:-3])

    if s.count('.TO') > 1:
        candidates.append(s.replace('.TO.TO', '.TO'))

    seen, out = set(), []
    for c in candidates:
        if c not in seen and c != original and not _is_bad_suffix(c):
            seen.add(c)
            out.append(c)
    return out


def load_active_symbol_sets(conn):
    price = {r['symbol'] for r in conn.fetchall("SELECT DISTINCT symbol FROM stockprices")}
    ind = {r['symbol'] for r in conn.fetchall("SELECT DISTINCT symbol FROM indicators_json")}
    fund = {r['symbol'] for r in conn.fetchall("SELECT DISTINCT symbol FROM fundamentals")}
    ar = {r['symbol'] for r in conn.fetchall("SELECT DISTINCT symbol FROM analyst_ratings")}
    return price | ind | fund | ar


def main():
    conn = MySQLConnection(**MYSQL)
    active = load_active_symbol_sets(conn)
    log.info('Symbols with data: %d', len(active))

    inactive = conn.fetchall(
        "SELECT symbol, exchange, name, deactivated_reason FROM symbol_master "
        "WHERE is_active = 0 ORDER BY symbol"
    )

    log.info('Inactive symbols: %d', len(inactive))

    # Parse CLI
    import argparse
    parser = argparse.ArgumentParser(description='Batch probe inactive symbols via yfinance')
    parser.add_argument('--max', type=int, default=None, help='Max candidates to probe')
    parser.add_argument('--dry-run', action='store_true', help='Show candidates but do not write')
    args = parser.parse_args()

    # Build candidate map: original -> best candidate
    candidate_map = {}  # original -> candidate
    seen_candidates = {}  # candidate -> original (to avoid duplicate work)
    skipped_dup = 0
    skipped_bad = 0
    skipped_no_candidate = 0

    for row in inactive:
        symbol, exchange, name, reason = row['symbol'], row['exchange'], row['name'], row['deactivated_reason']

        if reason and 'duplicate format' in str(reason):
            skipped_dup += 1
            continue

        candidates = generate_candidates(symbol)
        if not candidates:
            skipped_no_candidate += 1
            continue

        chosen = None
        for c in candidates:
            if c in active:
                chosen = c
                break
        if chosen is None:
            chosen = candidates[0]

        if chosen in seen_candidates:
            # Already going to probe this candidate from another original
            candidate_map[symbol] = chosen
            skipped_no_candidate += 1  # count as no new candidate
            continue

        seen_candidates[chosen] = symbol
        candidate_map[symbol] = chosen

    unique_candidates = list(seen_candidates.keys())
    log.info(
        'Unique candidates to probe: %d (skipped dup=%d, no_candidate=%d)',
        len(unique_candidates), skipped_dup, skipped_no_candidate,
    )

    # Build reverse map: candidate -> list of originals
    cand_to_originals = {}
    for orig, cand in candidate_map.items():
        cand_to_originals.setdefault(cand, []).append(orig)

    if args.max:
        unique_candidates = unique_candidates[:args.max]
        log.info('Clipped to --max %d', args.max)

    if not unique_candidates:
        log.info('Nothing to do.')
        return

    if args.dry_run:
        log.info('DRY RUN — showing first 20 candidates:')
        for c in unique_candidates[:20]:
            originals = cand_to_originals.get(c, [])
            log.info('  %s <- %s', c, ', '.join(originals))
        log.info('Total candidates: %d', len(unique_candidates))
        return

    # Probe in chunks
    chunk_size = 50
    probe_start = (date.today() - timedelta(days=5)).isoformat()
    probe_end = (date.today() + timedelta(days=1)).isoformat()

    successes = []  # (original, candidate)
    failures = []   # candidate

    for i in range(0, len(unique_candidates), chunk_size):
        chunk = unique_candidates[i:i + chunk_size]
        log.info('Probing chunk %d-%d / %d ...', i + 1, min(i + chunk_size, len(unique_candidates)), len(unique_candidates))

        try:
            df = yf.download(
                tickers=chunk,
                start=probe_start,
                end=probe_end,
                threads=False,
                auto_adjust=True,
                progress=False,
                timeout=15,
            )
        except Exception as e:
            log.warning('Chunk %d download failed: %s', i, e)
            failures.extend(chunk)
            time.sleep(10)
            continue

        if df is None or df.empty:
            failures.extend(chunk)
            time.sleep(8)
            continue

        # Determine which tickers came back with valid (non-NaN) data
        if isinstance(df.columns, object) and hasattr(df.columns, 'get_level_values'):
            all_tickers = list(df.columns.get_level_values(1).unique())
        else:
            all_tickers = list(df.columns)

        chunk_ok = set()
        for t in all_tickers:
            if ('Close', t) in df.columns:
                series = df[('Close', t)]
                if series.notna().any():
                    chunk_ok.add(t)

        for c in chunk:
            if c in chunk_ok:
                successes.append(c)
            else:
                failures.append(c)

        time.sleep(8)

    log.info('Probe complete: %d success, %d failure', len(successes), len(failures))

    reactivated = 0
    renamed = 0
    marked_dup = 0
    inserted_rows = 0
    publish_errors = 0

    # Fetch history for successes and insert
    full_start = '2014-01-01'
    full_end = (date.today() + timedelta(days=1)).isoformat()

    publisher = EventPublisher(conn)
    lifecycle_repo = SymbolLifecycleRepository(conn)

    for c in successes:
        originals = cand_to_originals.get(c, [])
        if not originals:
            continue

        # Usually there should be exactly 1 original mapping to this candidate
        orig = originals[0]

        try:
            # Fetch full history for this candidate
            hist = yf.download(
                tickers=c,
                start=full_start,
                end=full_end,
                threads=False,
                auto_adjust=True,
                progress=False,
                timeout=20,
            )
            if hist is None or hist.empty:
                log.warning('Candidate %s has no full history', c)
                failures.append(c)
                continue

            # Check if target symbol already exists active
            row = conn.fetchone(
                "SELECT symbol FROM symbol_master WHERE symbol = %s AND is_active = 1",
                (c,),
            )
            if row:
                # Mark originals as duplicate of existing active symbol
                for o in originals:
                    conn.execute("""
                        UPDATE symbol_master
                        SET exchange = NULL,
                            name = CONCAT(IFNULL(name, ''), ' [DUPLICATE of ', %s, ']'),
                            deactivated_reason = %s,
                            deactivated_at = NOW(),
                            is_active = 0
                        WHERE symbol = %s
                    """, (c, f'duplicate - superseded by {c}', o))
                conn.commit()
                marked_dup += len(originals)
            else:
                # Rename/reactivate the original to the cleaned candidate
                conn.execute("""
                    UPDATE symbol_master
                    SET symbol = %s,
                        exchange = COALESCE(exchange, 'UNKNOWN'),
                        is_active = 1,
                        deactivated_at = NULL,
                        deactivated_reason = NULL,
                        data_start = %s,
                        last_updated = NOW()
                    WHERE symbol = %s
                """, (c, str(hist.index[0])[:10], orig))
                conn.commit()
                renamed += 1

            # Insert prices
            rows = []
            for idx, r in hist.iterrows():
                d = idx.strftime('%Y-%m-%d')
                close = r[('Close', c)]
                if pd.isna(close):
                    continue
                rows.append((
                    c,
                    d,
                    float(r[('Open', c)]) if not pd.isna(r[('Open', c)]) else None,
                    float(r[('High', c)]) if not pd.isna(r[('High', c)]) else None,
                    float(r[('Low', c)]) if not pd.isna(r[('Low', c)]) else None,
                    float(close),
                    int(r[('Volume', c)]) if not pd.isna(r[('Volume', c)]) else None,
                    float(close),
                    float(r.get(('Dividends', c), 0)) if not pd.isna(r.get(('Dividends', c), 0)) else 0,
                    float(r.get(('Stock Splits', c), 1)) if not pd.isna(r.get(('Stock Splits', c), 1)) else 1,
                ))

            if rows:
                conn.executemany(
                    'INSERT IGNORE INTO stockprices '
                    '(symbol,price_date,open,high,low,close,volume,adj_close,dividend,split_ratio) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    rows,
                )
                conn.commit()
                inserted_rows += len(rows)

            # Trigger lifecycle transitions
            try:
                # Update lifecycle state to TA_READY if applicable
                current_state = lifecycle_repo.get_state(c)
                if current_state in (SymbolState.CANDIDATE, SymbolState.PENDING_BACKFILL, SymbolState.PRICES_LOADED):
                    next_state = SymbolState.TA_READY
                    lifecycle_repo.set_state(c, next_state)
                publisher.publish('prices_loaded', {'symbol': c})
            except Exception as e:
                publish_errors += 1
                log.warning('Event publish failed for %s: %s', c, e)

            # Spawn downstream jobs
            try:
                import subprocess, os
                env = os.environ.copy()
                env['PYTHONPATH'] = str(Path(__file__).resolve().parent)
                subprocess.Popen(
                    [sys.executable, str(_PYTHON_DIR / 'news_monitor.py'), '--symbol', c, '--category', 'stocks'],
                    cwd=str(Path(__file__).resolve().parent),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.Popen(
                    [sys.executable, str(_PYTHON_DIR / 'fundamental_data.py'), '--mode', 'fetch', '--symbol', c],
                    cwd=str(Path(__file__).resolve().parent),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

            reactivated += 1
            time.sleep(0.5)

        except Exception as e:
            import traceback
            log.error('Failed backfill for %s: %s\n%s', c, e, traceback.format_exc())
            failures.append(c)
            time.sleep(2)

    conn.close()

    log.info('=== Batch Discover Summary ===')
    log.info('Candidates probed : %d', len(unique_candidates))
    log.info('Reactivated/renamed: %d', reactivated)
    log.info('Renamed symbols   : %d', renamed)
    log.info('Marked duplicate  : %d', marked_dup)
    log.info('Price rows inserted: %d', inserted_rows)
    log.info('Failures          : %d', len(failures))
    log.info('Publish errors    : %d', publish_errors)


if __name__ == '__main__':
    main()
