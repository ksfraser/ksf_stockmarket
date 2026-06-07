#!/usr/bin/env python3
import sqlite3
import pymysql
import math

sq = sqlite3.connect('/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db')
sq_cur = sq.cursor()

MDB = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market')
mdb_cur = MDB.cursor()

# Clear and migrate strategy_pipeline_results
mdb_cur.execute("TRUNCATE TABLE strategy_pipeline_results")

sq_cur.execute("SELECT * FROM strategy_pipeline_results")
cols = [desc[0] for desc in sq_cur.description]
cols_sql = ', '.join([f'`{c}`' for c in cols])
placeholders = ', '.join(['%s'] * len(cols))

total = 0
while True:
    rows = sq_cur.fetchmany(500)
    if not rows:
        break
    
    # Convert inf/NaN to None (NULL)
    cleaned = []
    for row in rows:
        cleaned_row = []
        for val in row:
            if isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
                cleaned_row.append(None)
            else:
                cleaned_row.append(val)
        cleaned.append(tuple(cleaned_row))
    
    mdb_cur.executemany(f"INSERT INTO strategy_pipeline_results ({cols_sql}) VALUES ({placeholders})", cleaned)
    MDB.commit()
    total += len(rows)
    print(f"Migrated {total} rows...")

print(f"Total: {total}")
MDB.close()
sq.close()