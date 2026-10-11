#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/.hermes/workspace/investment-agent/src')
sys.path.insert(0, '/root/.hermes/workspace/investment-agent/src/db')
sys.path.insert(0, '/root/.hermes/workspace/investment-agent/config')
from connection import DataSource

conn = DataSource.mariadb_connection()
cursor = conn.cursor()

# Look for tables that might have price/indicator data
cursor.execute("SHOW TABLES")
all_tables = [row[0] for row in cursor.fetchall()]
print(f'Total tables: {len(all_tables)}')

# Tables related to backtest analysis
keywords = ['backtest', 'signal', 'indicator', 'dividend', 'analyst', 'event', 'earnings', 'announcement', 'recommendation', 'forecast', 'target', 'position', 'portfolio', 'price', 'daily', 'candle', 'history', 'stock', 'fund', 'equity', 'ticker', 'instrument', 'asset', 'transaction', 'trade']
print(f'\n--- Tables using keywords: {keywords} ---')
for t in sorted(all_tables):
    tl = t.lower()
    if any(kw in tl for kw in keywords):
        try:
            cursor.execute(f'SELECT COUNT(*) FROM `{t}`')
            count = cursor.fetchone()[0]
            cursor.execute(f'DESCRIBE `{t}`')
            cols = [c[0] for c in cursor.fetchall()]
            has_price = any(kw in c.lower() for kw in ['price', 'close', 'open', 'high', 'low', 'volume', 'indicator', 'dividend', 'ratio', 'return', 'target', 'daily', 'history', 'quote'])
            if has_price:
                print(f'  [{t}] {count} rows, cols={cols}')
        except Exception:
            pass

# Check daily_indicators fully
print(f'\n--- daily_indicators ---')
cursor.execute('SHOW FULL COLUMNS FROM daily_indicators')
cols = cursor.fetchall()
for col in cols:
    print(f'  {col[0]}: {col[1]}')

cursor.execute('SELECT COUNT(DISTINCT symbol) FROM daily_indicators')
print(f'Tickers: {cursor.fetchone()[0]}')

# Check other tables
for t in ['dividend_history', 'dividends', 'corporate_events', 'analyst_targets', 'backtest_runs', 'backtest_trades', 'analyst_recommendations', 'analyst_estimates']:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM `{t}`')
        count = cursor.fetchone()[0]
        print(f'\n  {t}: {count} rows')
    except Exception as e:
        print(f'\n  {t}: ERROR {e}')
