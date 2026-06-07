#!/usr/bin/env python3
import sqlite3
import pymysql

sq = sqlite3.connect('/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db')
sq.row_factory = sqlite3.Row
sq_cur = sq.cursor()

MDB = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market')
mdb_cur = MDB.cursor()

# Migrate backtest_runs
sq_cur.execute("SELECT * FROM backtest_runs")
columns = [desc[0] for desc in sq_cur.description]
cols_sql = ', '.join([f'`{c}`' for c in columns])
placeholders = ', '.join(['%s'] * len(columns))

for row in sq_cur:
    values = tuple(row[c] for c in columns)
    mdb_cur.execute(f"INSERT INTO backtest_runs ({cols_sql}) VALUES ({placeholders})", values)
MDB.commit()
print("Migrated backtest_runs")

# Migrate backtest_trades
sq_cur.execute("SELECT * FROM backtest_trades")
columns = [desc[0] for desc in sq_cur.description]
cols_sql = ', '.join([f'`{c}`' for c in columns])

for row in sq_cur:
    values = tuple(row[c] for c in columns)
    mdb_cur.execute(f"INSERT INTO backtest_trades ({cols_sql}) VALUES ({placeholders})", values)
MDB.commit()
print("Migrated backtest_trades")

# Verify
mdb_cur.execute("SELECT COUNT(*) FROM backtest_runs")
print(f"backtest_runs MariaDB now: {mdb_cur.fetchone()[0]}")
mdb_cur.execute("SELECT COUNT(*) FROM backtest_trades")
print(f"backtest_trades MariaDB now: {mdb_cur.fetchone()[0]}")

MDB.close()
sq.close()