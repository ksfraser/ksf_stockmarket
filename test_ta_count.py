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

# Batch migrate ta_indicators
sq_cur.execute("SELECT * FROM ta_indicators")

count = 0
while True:
    rows = sq_cur.fetchmany(1000)
    if not rows:
        break
    
    count += len(rows)
    print(f"Processing batch: {count} rows...")

print(f"Total rows to migrate: {count}")
MDB.close()
sq.close()