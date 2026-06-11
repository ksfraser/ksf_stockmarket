#!/usr/bin/env python3
"""
run_backtest.py — LEGACY SCRIPT (SUPPRESSED - USE MARIADB VERSION)

This script forced SQLite backend. The MariaDB version is at:
  python/ga_optimizer.py or python/allocation_backtester.py

See cron job "ATR Stop Backtest Sweep" for active backtesting.
"""
import sys
print("This script is deprecated. Use python/ga_optimizer.py or python/allocation_backtester.py instead.", file=sys.stderr)
sys.exit(0)