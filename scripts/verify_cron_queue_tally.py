#!/usr/bin/env python3
"""Standalone event_queue tally helper for the cron queue processor.

Connects to the remote MariaDB (ksfraser.ca / ksfraser_stock_market) using the
vault-decrypted DB password, then prints the status histogram + pending count.
Usage: python3 scripts/verify_cron_queue_tally.py
"""
import os
import sys

# Repo root on sys.path (python/config_loader.py lives at repo-root/python/)
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _repo_root)

from python.config_loader import Config  # noqa: E402
import pymysql  # noqa: E402

cfg = Config()
password = cfg.db_password or cfg.secrets.get('db_password') or os.environ.get('DB_PASS', '')
if not password:
    raise RuntimeError('DB password not resolved from vault')

conn = pymysql.connect(
    host=cfg.data.db_host,
    port=int(getattr(cfg.data, 'db_port', 3306)),
    database=cfg.data.db_name,
    user=cfg.data.db_user,
    password=password,
    cursorclass=pymysql.cursors.DictCursor,
)
try:
    with conn.cursor() as cur:
        cur.execute(
            'SELECT status, COUNT(*) AS c '
            'FROM event_queue GROUP BY status ORDER BY c DESC'
        )
        rows = cur.fetchall()
        cur.execute(
            "SELECT COUNT(*) AS pending FROM event_queue WHERE status = 'pending'"
        )
        pending = cur.fetchone()['pending']
finally:
    conn.close()

print('status tally:')
for r in rows:
    print(f'  {r["status"]}: {r["c"]}')
print(f'PENDING={pending}')
