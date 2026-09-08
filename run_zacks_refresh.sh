#!/usr/bin/env bash
# run_zacks_refresh.sh — cron wrapper for zacks_scraper.py
# Sources .env for DB creds, runs the Zacks scraper for all active symbols.
set -uo pipefail
REPO_DIR="/var/www/stockmarket-app"
cd "$REPO_DIR"
if [[ -f ".env" ]]; then
    set -a && . ./.env && set +a
fi
exec python3 -u python/zacks_scraper.py --all 2>&1
