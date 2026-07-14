#!/usr/bin/env python3
"""
dedup_alerts.py — Remove duplicate alert_queue rows.

Because alert IDs used to include minute/second timestamps, the same
symbol+alert_type on the same caledar day could appear multiple times.
This script keeps the most recent row per (DATE(created_at), symbol, alert_type).
"""
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
_cfg = Config(_cfg_path) if os.path.exists(_cfg_path) else Config()

import pymysql

DB_CFG = dict(
    host=_cfg.data.db_host,
    user=_cfg.data.db_user,
    password=_cfg.db_password,
    database=_cfg.data.db_name,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)


def main() -> None:
    conn = pymysql.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    DATE(created_at) AS alert_date,
                    symbol,
                    alert_type,
                    COUNT(*) AS cnt,
                    MAX(id) AS keep_id
                FROM alert_queue
                GROUP BY DATE(created_at), symbol, alert_type
                HAVING COUNT(*) > 1
            """)
            dupes = cur.fetchall()
            if not dupes:
                print('No duplicate alert groups found.')
                return

            print(f'Duplicate alert groups: {len(dupes)}')
            to_delete = 0
            for g in dupes:
                cur.execute("""
                    SELECT id FROM alert_queue
                    WHERE DATE(created_at) = %s AND symbol = %s AND alert_type = %s
                      AND id <> %s
                """, (g['alert_date'].isoformat(), g['symbol'], g['alert_type'], g['keep_id']))
                ids = [r['id'] for r in cur.fetchall()]
                if not ids:
                    continue
                ph = ','.join(['%s'] * len(ids))
                cur.execute(f'DELETE FROM alert_status_log WHERE alert_id IN ({ph})', ids)
                cur.execute(f'DELETE FROM alert_responses WHERE alert_id IN ({ph})', ids)
                cur.execute(f'DELETE FROM alert_queue WHERE id IN ({ph})', ids)
                to_delete += cur.rowcount
            conn.commit()
            print(f'Deleted {to_delete} duplicate alert rows.')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
