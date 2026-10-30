#!/bin/bash
#
# MIGRATION MONITOR — watches migrate_indicators_json_to_columnar.py
# Runs every 15 minutes via cron.
#

set -euo pipefail

SCRIPT_DIR="/home/ksf_stockmarket/ksf_stockmarket"
MIGRATE_SCRIPT="migrate_indicators_json_to_columnar.py"
MONITOR_LOG="/tmp/migrate_monitor.log"
MIGRATE_LOG="/tmp/migrate_indicators.log"

# DB credentials
DB_HOST="ksfraser.ca"
DB_PORT="3306"
DB_USER="ksfraser_stockmarket"
DB_PASS="Zaqwsx9sm1@"
DB_NAME="ksfraser_stock_market"

# Timestamp helper
ts() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Log helper
log() {
    echo "$(ts) $1" >> "$MONITOR_LOG"
}

# --- Step 1: Check if migration process is running ---
if pgrep -f "migrate_indicators_json_to_columnar.py" > /dev/null 2>&1; then
    PID=$(pgrep -f "migrate_indicators_json_to_columnar.py" | head -1)
    log "Status: ALIVE (PID $PID) — migration still running, no action."
    exit 0
fi

# --- Step 2: Migration not running. Query indicators_json row count ---
JSON_COUNT=$(mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
    -N -e "SELECT COUNT(*) FROM indicators_json;" 2>/dev/null || echo "QUERY_FAILED")

if [ "$JSON_COUNT" = "QUERY_FAILED" ] || [ -z "$JSON_COUNT" ]; then
    log "Status: DEAD — migration not running, DB query failed. Retrying next cycle."
    exit 1
fi

# --- Step 3a: If indicators_json is empty, remove this cron job and exit ---
if [ "$JSON_COUNT" -eq 0 ] 2>/dev/null; then
    log "Status: DEAD — indicators_json count = 0. Migration complete."
    log "Removing this cron job (MIGRATION MONITOR)."
    crontab -l | grep -v "MIGRATION MONITOR" | crontab -
    log "Cron job removed. Exiting."
    exit 0
fi

# --- Step 3b: indicators_json still has rows — restart migration ---
log "Status: DEAD — migration not running, indicators_json has $JSON_COUNT rows remaining. Restarting."

cd "$SCRIPT_DIR"

nohup python3 -u "$MIGRATE_SCRIPT" >> "$MIGRATE_LOG" 2>&1 &
NEW_PID=$!

log "Restarted migration script (PID $NEW_PID). $JSON_COUNT rows remaining in indicators_json."

exit 0
