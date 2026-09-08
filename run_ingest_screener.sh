#!/usr/bin/env bash
# run_ingest_screener.sh — cron wrapper for ingest_screener_symbols.py
# Sources .env for DB creds, runs the ingestion, logs to stdout.
set -uo pipefail
REPO_DIR="/home/ksf_stockmarket/ksf_stockmarket"
cd "$REPO_DIR"
if [[ -f ".env" ]]; then
    set -a && . ./.env && set +a
fi
exec python3 -u python/ingest_screener_symbols.py 2>&1
