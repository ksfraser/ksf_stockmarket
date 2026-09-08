#!/usr/bin/env bash
# run_tv_screener.sh — cron wrapper for tv_screener.py
# Sources .env for DB creds, runs the screener, logs to stdout.
set -uo pipefail
REPO_DIR="/home/ksf_stockmarket/ksf_stockmarket"
cd "$REPO_DIR"
if [[ -f ".env" ]]; then
    set -a && . ./.env && set +a
fi
exec python3 -u tv_screener.py 2>&1
