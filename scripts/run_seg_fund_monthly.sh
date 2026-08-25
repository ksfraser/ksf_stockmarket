#!/usr/bin/env bash
# Monthly seg-fund pipeline (runs on the 15th).
# Refreshes the LIVE-API carriers' data, snapshots performance_history, and
# recomputes the analytics (calc_pipeline.py -> seg_fund_metrics).
#
# NOTE: BMO / Canada Life / Empire Life / Equitable are seeded from prod
# metadata and are intentionally EXCLUDED here -- re-running their seeders
# could re-introduce the decimal-unit corruption that was normalised in place.
# Their refresh is manual until a verified headless seeder exists.
set -u
REPO=/home/ksf_stockmarket/ksf_stockmarket
LOG=/tmp/segfund_monthly.log
cd "$REPO" || exit 1
echo "[$(date -u +%FT%TZ)] monthly seg-fund run start" | tee -a "$LOG"
for s in seed_rbc_local seed_rbc_trailing seed_sunlife_local seed_manulife_local seed_ia_local; do
  echo "-- $s" | tee -a "$LOG"
  python3 "scripts/$s.py" >> "$LOG" 2>&1 || echo "  WARN: $s failed" | tee -a "$LOG"
done
python3 scripts/snapshot_perf_history.py >> "$LOG" 2>&1 || true
python3 scripts/calc_pipeline.py >> "$LOG" 2>&1 || true
echo "[$(date -u +%FT%TZ)] monthly seg-fund run done" | tee -a "$LOG"
