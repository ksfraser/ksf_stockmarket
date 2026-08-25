#!/usr/bin/env bash
# Annual seg-fund pipeline (runs in Feb). Same as monthly PLUS the calendar-year
# rollover that captures the previous year's return into a new yr_<YEAR> column.
set -u
REPO=/home/ksf_stockmarket/ksf_stockmarket
LOG=/tmp/segfund_annual.log
cd "$REPO" || exit 1
echo "[$(date -u +%FT%TZ)] annual seg-fund run start" | tee -a "$LOG"
bash scripts/run_seg_fund_monthly.sh >> "$LOG" 2>&1 || true
python3 scripts/rollover_calendar_year.py >> "$LOG" 2>&1 || true
python3 scripts/calc_pipeline.py >> "$LOG" 2>&1 || true
echo "[$(date -u +%FT%TZ)] annual seg-fund run done" | tee -a "$LOG"
