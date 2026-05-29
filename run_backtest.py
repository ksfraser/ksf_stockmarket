#!/usr/bin/env python3
"""
run_backtest.py — Wrapper to run backtest_engine against SQLite dev DB
"""
import sys
sys.path.insert(0, '/home/ksf_stockmarket/ksf_stockmarket')

# Inject mysql.connector shim BEFORE any other imports
import sys, types
if 'mysql.connector' not in sys.modules:
    _mc = types.ModuleType('mysql.connector')
    _mc.connect = lambda *a, **kw: None
    _mc.Error = Exception
    _mc.MySQLError = Exception
    _mc.errors = types.ModuleType('mysql.connector.errors')
    _mc.errors.InterfaceError = Exception
    _mc.errors.DatabaseError = Exception
    _mc.errors.OperationalError = Exception
    sys.modules['mysql'] = types.ModuleType('mysql')
    sys.modules['mysql.connector'] = _mc
    sys.modules['mysql.connector.errors'] = _mc.errors

# Force SQLite mode in db_connector before anything imports it
import python.db_connector as dbc
dbc.DB_CONFIG = {'backend': 'sqlite', 'path': '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'}
dbc.USE_SQLITE = True

from datetime import date
from python.db_connector import get_connection
from python.backtest_engine import BacktestEngine

conn = get_connection()

config = {
    'strategy': 'combined',
    'start_date': date(2014, 1, 1),
    'end_date': date(2025, 12, 31),
    'initial_capital': 100000,
    'commission': 9.95,
    'max_position_pct': 0.10,  # 10% max per position (1% was too conservative)
    'frequency': 'monthly',
}

print(f"Running backtest: {config['start_date']} → {config['end_date']}")
print(f"  Strategy: {config['strategy']}, Capital: ${config['initial_capital']:,.0f}")
print(f"  Commission: ${config['commission']}, Max position: {config['max_position_pct']*100:.0f}%")
print()

engine = BacktestEngine(
    conn=conn,
    strategy=config['strategy'],
    start_date=config['start_date'],
    end_date=config['end_date'],
    initial_capital=config['initial_capital'],
    commission=config['commission'],
    max_position_pct=config['max_position_pct'],
    frequency=config['frequency'],
)

results = engine.run()
conn.close()

print("\n" + "=" * 70)
print("BACKTEST RESULTS SUMMARY")
print("=" * 70)
for k, v in results.items():
    print(f"  {k:30s}: {v}")
