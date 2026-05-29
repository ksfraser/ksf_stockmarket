#!/bin/bash
# Nightly pipeline — runs at 6 AM after market close
# 1. Import latest price data from yfinance
# 2. Update Tier 2 scoring (evalsummary)
# 3. Generate Layer 1 signals

cd /home/ksf_stockmarket/ksf_stockmarket

# Step 1: Data import (last 5 days to catch any revisions)
echo "$(date): Starting nightly data import"
python3 scripts/update_prices.py --days 5 2>&1 || echo "WARNING: price import failed"

# Step 2: Scoring (evalsummary)
echo "$(date): Starting Tier 2 scoring"
python3 python/sqlite_scoring.py 2>&1 || echo "WARNING: scoring failed"

# Step 3: Layer 1 — generate walk-forward signals for all strategies
echo "$(date): Running v3 pipeline walk-forward"
python3 trading_pipeline_v3.py \
  --start 2014-01-01 \
  --end $(date +%Y-%m-%d) \
  --sweep \
  --output-table pipeline_v3_walkforward \
  2>&1 || echo "WARNING: pipeline failed"

echo "$(date): Nightly pipeline complete"
