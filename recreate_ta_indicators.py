#!/usr/bin/env python3
import sqlite3
import pymysql

sq = sqlite3.connect('/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db')
sq_cur = sq.cursor()

MDB = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market')
mdb_cur = MDB.cursor()

# Get all column names
sq_cur.execute("PRAGMA table_info(ta_indicators)")
cols = [row[1] for row in sq_cur.fetchall()]

# Drop and recreate table
mdb_cur.execute("DROP TABLE IF EXISTS ta_indicators")

# Build column definitions
col_defs = []
for col in cols:
    if col == 'symbol':
        col_defs.append(f"    `{col}` VARCHAR(50)")
    elif col == 'price_date':
        col_defs.append(f"    `{col}` VARCHAR(20)")
    else:
        col_defs.append(f"    `{col}` DOUBLE")

create_sql = "CREATE TABLE ta_indicators (\n" + ",\n".join(col_defs) + ",\n    PRIMARY KEY (symbol, price_date)\n) DEFAULT CHARSET=utf8mb4;"
mdb_cur.execute(create_sql)
MDB.commit()
print("Created ta_indicators with", len(cols), "columns")

MDB.close()
sq.close()