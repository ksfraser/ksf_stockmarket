#!/usr/bin/env python3
import sqlite3
import pymysql

sq = sqlite3.connect('/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db')
sq.row_factory = sqlite3.Row
sq_cur = sq.cursor()

MDB = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market')
mdb_cur = MDB.cursor()

# Migrate backtest_runs_v2
sq_cur.execute("SELECT * FROM backtest_runs_v2")
columns = [desc[0] for desc in sq_cur.description]
cols_sql = ', '.join([f'`{c}`' for c in columns])
placeholders = ', '.join(['%s'] * len(columns))

count = 0
for row in sq_cur:
    values = tuple(row[c] for c in columns)
    mdb_cur.execute(f"INSERT INTO backtest_runs_v2 ({cols_sql}) VALUES ({placeholders})", values)
    count += 1
MDB.commit()
print(f"Migrated backtest_runs_v2: {count} rows")

# Migrate backtest_trades_v2
sq_cur.execute("SELECT * FROM backtest_trades_v2")
columns = [desc[0] for desc in sq_cur.description]
cols_sql = ', '.join([f'`{c}`' for c in columns])
placeholders = ', '.join(['%s'] * len(columns))

count = 0
for row in sq_cur:
    values = tuple(row[c] for c in columns)
    mdb_cur.execute(f"INSERT INTO backtest_trades_v2 ({cols_sql}) VALUES ({placeholders})", values)
    count += 1
MDB.commit()
print(f"Migrated backtest_trades_v2: {count} rows")

MDB.close()
sq.close()