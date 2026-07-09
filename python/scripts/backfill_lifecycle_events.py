#!/usr/bin/env python3
"""
backfill_lifecycle_events.py — Backfill prices_loaded events and TA_READY state
for symbols that were reactivated but missed event publishing.
"""
import sys
from pathlib import Path

_PYTHON_DIR = Path(__file__).resolve().parent.parent.parent  # repo root
_PYTHON_SRC = _PYTHON_DIR / 'python' / 'src'
for _p in (str(_PYTHON_DIR), str(_PYTHON_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import logging
import pymysql
import pymysql.cursors
import uuid
from datetime import datetime

from config_loader import Config
from db.mysql_adapter import MySQLConnection
from lifecycle.state import SymbolState

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('backfill_lifecycle')

CFG_PATH = _PYTHON_DIR / 'config.yaml'
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


def main() -> None:
    conn = MySQLConnection(**MYSQL)

    rows = conn.fetchall(
        "SELECT symbol FROM symbol_master "
        "WHERE is_active = 1 AND pipeline_state IN (%s, %s, %s, %s) "
        "ORDER BY symbol",
        (
            SymbolState.UNKNOWN.value,
            SymbolState.CANDIDATE.value,
            SymbolState.PENDING_BACKFILL.value,
            SymbolState.PRICES_LOADED.value,
        ),
    )
    symbols = [row['symbol'] if isinstance(row, dict) else row[0] for row in rows]
    log.info('Found %d active symbols needing lifecycle backfill', len(symbols))

    if not symbols:
        log.info('Nothing to do.')
        conn.close()
        return

    # Use a helper query to verify they actually have price data
    placeholders = ','.join(['%s'] * len(symbols))
    price_rows = conn.fetchall(
        f"SELECT symbol, MAX(price_date) AS latest_price_date FROM stockprices "
        f"WHERE symbol IN ({placeholders}) GROUP BY symbol",
        tuple(symbols),
    )
    price_map = {row['symbol']: row['latest_price_date'] for row in price_rows}

    eligible = []
    skipped = 0
    for s in symbols:
        if not price_map.get(s):
            skipped += 1
            continue
        eligible.append(s)

    if not eligible:
        log.info('No eligible symbols with price data.')
        conn.close()
        return

    now = datetime.now().isoformat()

    # Batch update lifecycle state + backfill events in a bulk operation
    # Build tuples for executemany
    state_rows = [(SymbolState.TA_READY.value, s) for s in eligible]
    conn.executemany(
        "UPDATE symbol_master SET pipeline_state = %s, last_state_transition = NOW() WHERE symbol = %s",
        state_rows,
    )

    event_values = []
    for s in eligible:
        event_values.append((
            str(uuid.uuid4()),
            'prices_loaded',
            '{\"symbol\": \"' + s + '\"}',
            now,
            'pending',
            0,
            None,
        ))

    conn.executemany(
        "INSERT INTO event_queue "
        "(event_id, event_type, payload, occurred_at, status, attempts, last_error) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        event_values,
    )

    conn.commit()
    conn.close()

    log.info('=== Backfill Complete ===')
    log.info('Updated : %d', len(eligible))
    log.info('Skipped : %d', skipped)


if __name__ == '__main__':
    main()
