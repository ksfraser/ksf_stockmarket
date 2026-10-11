#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/root/.hermes/workspace/investment-agent/src')
sys.path.insert(0, '/root/.hermes/workspace/investment-agent/src/db')
sys.path.insert(0, '/root/.hermes/workspace/investment-agent/config')
from connection import DataSource

conn = DataSource.mariadb_connection()
cursor = conn.cursor()

# Check what tables are actually in MariaDB with substantial data
tables_with_data = []
cur = conn.cursor()
cur.execute('SHOW TABLES')
for row in cur.fetchall():
    t = row[0]
    try:
        cur2 = conn.cursor()
        cur2.execute(f'SELECT COUNT(*) FROM `{t}`')
        count = cur2.fetchone()[0]
        tables_with_data.append((t, count))
    except Exception:
        pass

# Sort by count
tables_with_data.sort(key=lambda x: x[1], reverse=True)
print(f'=== Tables with data ({len(tables_with_data)} total) ===')
for t, count in tables_with_data:
    print(f'  {t}: {count} rows')

# Check for price/indicator related tables
print(f'\n=== Tables with price/indicator data ===')
keywords = ['price', 'indicator', 'dividend', 'daily', 'market', 'quote', 'historical', 'history']
for t, count in tables_with_data:
    tl = t.lower()
    if any(kw in tl for kw in keywords):
        cursor.execute(f'DESCRIBE `{t}`')
        cols = [c[0] for c in cursor.fetchall()]
        print(f'  {t}: {count} rows, cols={cols}')
