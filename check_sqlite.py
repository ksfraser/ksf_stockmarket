import sqlite3
import json
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'analysis_results.db')
print("DB path:", db_path)
print("Exists:", os.path.exists(db_path))

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Show schema
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name='alert_queue'")
row = cur.fetchone()
if row:
    print("\nSCHEMA:")
    print(row[1])
else:
    print("\nNO alert_queue table found")
    # List all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("Tables:", [r[0] for r in cur.fetchall()])

# Count rows
try:
    cur.execute('SELECT COUNT(*) FROM alert_queue')
    print("\ntotal rows:", cur.fetchone()[0])
except Exception as e:
    print("\ncount error:", e)

# Count by alert_type
try:
    cur.execute("SELECT alert_type, COUNT(*) FROM alert_queue GROUP BY alert_type ORDER BY COUNT(*) DESC")
    print("\nCount by alert_type:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")
except Exception as e:
    print("\ngroupby error:", e)

# Sample alert
try:
    cur.execute("SELECT id, alert_type, symbol, severity, status FROM alert_queue LIMIT 3")
    print("\nSample rows:")
    for r in cur.fetchall():
        print("  ", r)
except Exception as e:
    print("\nsample error:", e)

conn.close()
