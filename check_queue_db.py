#!/usr/bin/env python3
import pymysql

cfg = {
    'host': 'ksfraser.ca',
    'port': 3306,
    'database': 'ksfraser_stock_market',
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

try:
    conn = pymysql.connect(**cfg)
    print('DB connection OK')
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM event_queue WHERE status='pending'")
        print('Pending jobs:', cur.fetchone()['cnt'])
        cur.execute("SELECT event_id, event_type, occurred_at, status FROM event_queue ORDER BY occurred_at ASC LIMIT 10")
        rows = cur.fetchall()
        for r in rows:
            print(r)
except Exception as e:
    print('DB error:', repr(e))
