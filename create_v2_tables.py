#!/usr/bin/env python3
import pymysql
import sqlite3

MDB = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market')
mdb_cur = MDB.cursor()

# Create backtest_runs_v2
mdb_cur.execute("""
CREATE TABLE IF NOT EXISTS backtest_runs_v2 (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_date DATE,
    start_date DATE,
    end_date DATE,
    symbols BIGINT,
    trades BIGINT,
    initial_capital DOUBLE,
    final_value DOUBLE,
    pnl DOUBLE,
    pnl_pct DOUBLE,
    max_drawdown DOUBLE,
    sharpe DOUBLE
)
""")

# Create backtest_trades_v2
mdb_cur.execute("""
CREATE TABLE IF NOT EXISTS backtest_trades_v2 (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_id BIGINT,
    trade_date DATE,
    symbol VARCHAR(50),
    action VARCHAR(10),
    shares BIGINT,
    price DOUBLE,
    commission DOUBLE
)
""")

MDB.commit()
print("Created v2 tables")
MDB.close()

# Get ta_indicators full schema
sq = sqlite3.connect('/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db')
sq.row_factory = sqlite3.Row
cur = sq.cursor()
cur.execute("PRAGMA table_info(ta_indicators)")
cols = [(r[1], 'price_date' if r[1] == 'price_date' else 'symbol' if r[1] == 'symbol' else 'DOUBLE') for r in cur.fetchall()]
print(f"ta_indicators columns: {len(cols)}")
sq.close()