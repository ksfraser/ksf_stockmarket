#!/usr/bin/env python3
"""
Run Phase 3 Genetic Algorithm — narrow optimization (per-ticker optimization).
"""
import sys, os, sqlite3, json, random
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/indicators')
sys.path.insert(0, 'src/backtest')
sys.path.insert(0, 'src/optimization')
sys.path.insert(0, 'src/db')
sys.path.insert(0, '.')

from db.data_cache import DataCache
from backtest.optimize import BacktestEngine, GeneticOptimizer, PORTFOLIO_TICKERS

print("=" * 80)
print("PHASE 3 — GENETIC ALGORITHM OPTIMIZATION")
print("Narrow per-ticker optimization")
print("=" * 80)

cache = DataCache()
engine = BacktestEngine(cache)

# Verify DB has data for all tickers
missing = []
for ticker in PORTFOLIO_TICKERS:
    prices = cache.get_prices(ticker)
    if prices.empty or len(prices) < 250:
        missing.append((ticker, len(prices)))

if missing:
    print(f"\nWARNING: Missing data for {len(missing)} tickers:")
    for t, n in missing:
        print(f"  {t}: {n} rows")
    MAX_DAYS = 2500
else:
    print(f"\nDB cache: {len(PORTFOLIO_TICKERS)} tickers with sufficient data")
    MAX_DAYS = 500

import sqlite3
db_conn = sqlite3.connect('/tmp/ga_narrow_per_ticker_results.db')
db_conn.row_factory = sqlite3.Row
db_conn.execute("PRAGMA journal_mode=WAL")
db_conn.execute("PRAGMA busy_timeout=5000")
db_conn.execute("PRAGMA foreign_keys=ON")

ga = GeneticOptimizer(engine, db_conn, population_size=5, generations=3, mutation_rate=0.20, elite_fraction=0.1, max_days=MAX_DAYS)

results = {}
for ticker in PORTFOLIO_TICKERS:
    print(f"\n  Processing: {ticker}")
    try:
        result = ga.optimize(ticker)
        results[ticker] = result
        print(f"    -> Best fitness: {result.get('fitness', 0):.2f}, Return: {result.get('total_return', 0):.2f}%, Sharpe: {result.get('sharpe', 0):.4f}")
        weights = result.get('optimal_weights', {})
        if weights:
            print(f"    -> Optimal weights: {weights}")
    except Exception as ex:
        print(f"    ERROR on {ticker}: {ex}")
        results[ticker] = {'error': str(ex)}

import json
with open('/tmp/ga_narrow_per_ticker_results.json', 'w') as f:
    output = {}
    for k, v in results.items():
        if isinstance(v, dict):
            output[k] = {kk: vv for kk, vv in v.items() if kk != 'trades' and isinstance(vv, (float, int, str, bool, list, dict))}
        else:
            output[k] = str(v)
    json.dump(output, f, indent=2, default=str)

print(f"\nNarrow pass complete. Results saved to /tmp/ga_narrow_per_ticker_results.json")
print("Done.")
