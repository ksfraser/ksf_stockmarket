#!/usr/bin/env python3
"""Read-only query of the event_queue table for queue-state checks."""
import pymysql
import sys

conn = pymysql.connect(
    host='ksfraser.ca', port=3306, database='ksfraser_stock_market',
    user='ksfraser_stockmarket', password='Zaqwsx9sm1@', charset='utf8mb4', autocommit=True,
    cursorclass=pymysql.cursors.DictCursor,
)

try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT event_type,
                   COUNT(*) AS n,
                   SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                   SUM(CASE WHEN status='running' THEN 1 ELSE 0 END) AS running,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed
            FROM event_queue
            GROUP BY event_type
        """)
        rows = cur.fetchall()
        print("--- event_type tallies ---")
        for r in rows:
            print(r)
        cur.execute("SELECT COUNT(*) AS n_pending FROM event_queue WHERE status='pending'")
        print("TOTAL pending:", cur.fetchone()['n_pending'])
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
finally:
    conn.close()
