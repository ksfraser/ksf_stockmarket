#!/usr/bin/env python3
import sqlite3
import pymysql

sq = sqlite3.connect('/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db')
sq_cur = sq.cursor()

MDB = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market')
mdb_cur = MDB.cursor()

# Check MariaDB ta_indicators count
mdb_cur.execute("SELECT COUNT(*) FROM ta_indicators")
mdb_count = mdb_cur.fetchone()[0]
print(f"MariaDB ta_indicators: {mdb_count}")

# Clear if needed
if mdb_count > 0:
    mdb_cur.execute("TRUNCATE TABLE ta_indicators")
    MDB.commit()

# Batch migrate ta_indicators
sq_cur.execute("SELECT * FROM ta_indicators")
batch_size = 1000
batch = []
count = 0

while True:
    rows = sq_cur.fetchmany(batch_size)
    if not rows:
        break
    
    # Get column names from cursor description
    cols = [desc[0] for desc in sq_cur.description]
    cols_sql = ', '.join([f'`{c}`' for c in cols])
    placeholders = ', '.join(['%s'] * len(cols))
    
    for row in rows:
        batch.append(tuple(row))
    
    mdb_cur.executemany(f"INSERT INTO ta_indicators ({cols_sql}) VALUES ({placeholders})", batch)
    MDB.commit()
    count += len(batch)
    batch = []
    print(f"Migrated {count} rows...")

print(f"Total migrated: {count}")
MDB.close()
sq.close()