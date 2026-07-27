#!/bin/bash
# Nightly pipeline — runs at 6 AM after market close
# 1. Prices + indicators via unified daily runner
# 2. Advisor signals + alert watcher + notifications via unified daily runner
# 3. Legacy walk-forward backtest (heavy — consider moving to weekly cron)

export PYTHONPATH="/home/ksf_stockmarket/ksf_stockmarket:python:python/src"
cd /home/ksf_stockmarket/ksf_stockmarket

echo "$(date): Starting daily_run stages"
python3 python/scripts/daily_run.py --stages ingest_prices,calc_indicators,advisor_signals,alert_watcher \
    || echo "WARNING: daily_run reported failures — check ~/.hermes/cron/output/daily_run_latest.json"

echo "$(date): Legacy v3 walk-forward backtest"
python3 trading_pipeline_v3.py \
  --start 2014-01-01 \
  --end $(date +%Y-%m-%d) \
  --sweep \
  --output-table pipeline_v3_walkforward \
  2>&1 || echo "WARNING: pipeline v3 failed"

echo "$(date): Nightly pipeline complete"
