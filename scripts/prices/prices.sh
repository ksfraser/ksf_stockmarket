#!/bin/sh
# LEGACY — original paths (/mnt/2/development/...) no longer exist.
# Modern equivalent: python/scripts/daily_pipeline.py / daily_run.py
# Kept for reference only; do not schedule without updating paths.

echo "LEGACY: prices/prices.sh references removed paths."
echo "Use python/scripts/daily_run.py --stages ingest_prices instead."
exit 1
