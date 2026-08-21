#!/usr/bin/env python3
"""
drain_stale_alerts.py — purge stale alert_queue rows.

The alert_queue table only ever holds historical alert records. "Stale" rows
are those that have been resolved (status='completed') and are older than a
configurable cutoff (default 30 days). They carry no active state, so they are
safe to remove; we dump them to a JSON backup first for reversibility.

IMPORTANT — real schema (verified 2026-08-20):
  * There is NO `processed` column.
  * status enum is (pending, processing, completed, failed, ack, ignore).
    There is NO 'sent' status.
  The previous version of this script used a `processed` column and a `sent`
  status that do not exist, so it errored and drained nothing.

Usage:
  python3 drain_stale_alerts.py                  # delete completed older than 30d
  python3 drain_stale_alerts.py --days 14        # older than 14d
  python3 drain_stale_alerts.py --dry-run        # count only, no delete
  python3 drain_stale_alerts.py --status failed --days 90
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')
from config_provider import get_db_config
import pymysql


def main() -> None:
    ap = argparse.ArgumentParser(description="Purge stale alert_queue rows.")
    ap.add_argument('--days', type=int, default=30,
                    help='Purge rows older than N days (default 30).')
    ap.add_argument('--status', default='completed',
                    help="Status to purge (default 'completed').")
    ap.add_argument('--dry-run', action='store_true',
                    help='Count and back up only; do not delete.')
    ap.add_argument('--backup-dir', default='/root',
                    help='Directory for the JSON backup (default /root).')
    args = ap.parse_args()

    cfg = get_db_config()
    conn = pymysql.connect(
        host=cfg['host'],
        user=cfg['user'],
        password=cfg.get('password', ''),
        database=cfg['database'],
        port=int(cfg.get('port', 3306)),
        charset=cfg.get('charset', 'utf8mb4'),
        autocommit=True,
    )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM alert_queue "
                "WHERE status=%s AND created_at < NOW() - INTERVAL %s DAY",
                (args.status, args.days),
            )
            total = cur.fetchone()['n']
            print(f"Rows matching status='{args.status}' AND older than {args.days}d: {total}")

            if total == 0:
                print("Nothing to purge.")
                return

            cur.execute(
                "SELECT * FROM alert_queue "
                "WHERE status=%s AND created_at < NOW() - INTERVAL %s DAY",
                (args.status, args.days),
            )
            rows = cur.fetchall()

            def ser(row):
                return {k: (v.isoformat() if isinstance(v, datetime) else v)
                        for k, v in row.items()}

            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(args.backup_dir, f"alert_queue_purge_backup_{stamp}.json")
            with open(backup_path, 'w') as fh:
                json.dump([ser(r) for r in rows], fh, indent=2, default=str)
            print(f"Backup written: {backup_path} ({len(rows)} rows)")

            if args.dry_run:
                print("DRY-RUN: no rows deleted.")
                return

            ids = [r['id'] for r in rows]
            placeholders = ','.join(['%s'] * len(ids))

            # alert_responses.alert_id -> alert_queue.id (FK). Delete children first.
            cur.execute(
                f"SELECT * FROM alert_responses WHERE alert_id IN ({placeholders})", ids
            )
            child_rows = cur.fetchall()
            if child_rows:
                resp_backup = backup_path.replace('.json', '_responses.json')
                with open(resp_backup, 'w') as fh:
                    json.dump([ser(r) for r in child_rows], fh, indent=2, default=str)
                print(f"Backup written: {resp_backup} ({len(child_rows)} child rows)")
                cur.execute(
                    f"DELETE FROM alert_responses WHERE alert_id IN ({placeholders})", ids
                )
                print(f"Deleted {cur.rowcount} alert_responses child rows")

            cur.execute(
                f"DELETE FROM alert_queue WHERE id IN ({placeholders})", ids
            )
            deleted = cur.rowcount
            print(f"Deleted: {deleted} rows")

            cur.execute("SELECT COUNT(*) AS n FROM alert_queue")
            remaining = cur.fetchone()['n']
            print(f"Remaining rows in alert_queue: {remaining}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
