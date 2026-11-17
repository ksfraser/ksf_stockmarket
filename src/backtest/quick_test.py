#!/usr/bin/env python3
"""
Quick test: verify GA works with max_days=500 (2-year data)
"""
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/indicators')
sys.path.insert(0, 'src/backtest')
sys.path.insert(0, 'src/optimization')
sys.path.insert(0, 'src/db')
sys.path.insert(0, '.')

import sqlite3
from backtest.optimize import BacktestEngine, GeneticOptimizer, PORTFOLIO_TICKERS
from db.data_cache import DataCache
from datetime import datetime, timedelta

# Use DB cache
cache = DataCache()
engine = BacktestEngine(cache)

# Check data for RY
prices = cache.get_prices('RY')
print(f'RY full data: {len(prices)} days, range: {prices.index[0].date()} to {prices.index[-1].date()}')

# Test with max_days=500
from datetime import datetime, timedelta
cutoff = (datetime.now() - timedelta(days=730)).date().isoformat()
print(f'Using last 2 years (from {cutoff}) for faster GA')
MAX_DAYS = 500

# Create SQLite connection for the optimizer
db_conn = sqlite3.connect('analysis_results.db')

# Run GA with max_days=500
ga = GeneticOptimizer(engine, db_conn, population_size=5, generations=3, mutation_rate=0.20, elite_fraction=0.1, max_days=MAX_DAYS)

print(f'\nRunning GA test...')
result = ga.optimize('RY')
print(f'Result: fitness={result.get("fitness", 0):.2f}, return={result.get("total_return", 0):.2f}%')
print(f'Optimal weights: {result.get("optimal_weights", {})}')
print('Done.')
