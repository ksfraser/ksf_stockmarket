#!/bin/bash
# Nightly pipeline — runs at 6 AM after market close
# 1. Import latest price data from yfinance
# 2. Update Tier 2 scoring (evalsummary)
# 3. Generate Layer 1 signals
# 4. Fetch financial news from RSS feeds

cd /home/ksf_stockmarket/ksf_stockmarket

# Step 1: Data import (last 5 days to catch any revisions)
echo "$(date): Starting nightly data import"
python3 scripts/update_prices.py --days 5 2>&1 || echo "WARNING: price import failed"

# Step 2: TA Indicators (MariaDB version - writes to ta_indicators/indicators_json)
echo "$(date): Computing TA indicators"
python3 python/indicator_calculator.py 2>&1 || echo "WARNING: indicator calc failed"

# Step 3: Financial News from RSS feeds
echo "$(date): Fetching financial news"
python3 python/news_monitor.py 2>&1 || echo "WARNING: news fetch failed"

# Step 4: Layer 1 — generate walk-forward signals for all strategies
echo "$(date): Running v3 pipeline walk-forward"
python3 trading_pipeline_v3.py \
  --start 2014-01-01 \
  --end $(date +%Y-%m-%d) \
  --sweep \
  --output-table pipeline_v3_walkforward \
  2>&1 || echo "WARNING: pipeline failed"

echo "$(date): Nightly pipeline complete"
