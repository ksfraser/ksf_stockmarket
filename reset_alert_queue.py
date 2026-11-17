#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'data', 'analysis_results.db'
)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('DELETE FROM alert_queue')
conn.commit()
cur.execute('SELECT COUNT(*) FROM alert_queue')
count = cur.fetchone()[0]
print(f'Reset alert_queue table - now {count} rows')
conn.close()
