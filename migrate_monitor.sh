#!/bin/bash
# MIGRATION MONITOR — indicators_json → indicators columnar migration watchdog
# Runs every 15 minutes via cron.
# Self-removes when indicators_json reaches 0 rows.

set -euo pipefail

MONITOR_LOG="/tmp/migrate_monitor.log"
MIGRATION_SCRIPT="/home/ksf_stockmarket/ksf_stockmarket/migrate_indicators_json_to_columnar.py"
MIGRATION_LOG="/tmp/migrate_indicators.log"
WORK_DIR="/home/ksf_stockmarket/ksf_stockmarket"

# DB credentials
DB_HOST="ksfraser.ca"
DB_PORT="3306"
DB_USER="ksfraser_stockmarket"
DB_PASS="Zaqwsx9sm1@"
DB_NAME="ksfraser_stock_market"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$MONITOR_LOG"
}

# Step 1: Check if migration process is running
if pgrep -f "migrate_indicators_json_to_columnar.py" > /dev/null 2>&1; then
    log "migration alive — doing nothing"
    exit 0
fi

# Step 2: Migration NOT running — check if work remains
JSON_COUNT=$(cd "$WORK_DIR" && DB_PASS="$DB_PASS" DB_USER="$DB_USER" DB_NAME="$DB_NAME" \
    python3 -c "
import pymysql, os
conn = pymysql.connect(
    host=os.environ.get('DB_HOST', '$DB_HOST'),
    port=int(os.environ.get('DB_PORT', '$DB_PORT')),
    user=os.environ.get('DB_USER', '$DB_USER'),
    password=os.environ.get('DB_PASS', '$DB_PASS'),
    db=os.environ.get('DB_NAME', '$DB_NAME'),
    connect_timeout=10,
)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM indicators_json')
count = cur.fetchone()[0]
conn.close()
print(count)
" 2>&1)

if [ -z "$JSON_COUNT" ] || ! [[ "$JSON_COUNT" =~ ^[0-9]+$ ]]; then
    log "ERROR: failed to query indicators_json count: $JSON_COUNT"
    exit 1
fi

if [ "$JSON_COUNT" -eq 0 ]; then
    # Step 3a: No work remaining — remove this cron job and exit
    log "indicators_json empty (count=0) — removing cron job"
    (crontab -l 2>/dev/null | grep -v "MIGRATION MONITOR" || true) | crontab -
    log "cron job removed — migration complete"
    exit 0
fi

# Step 3b: Work remains — restart the migration
log "indicators_json has $JSON_COUNT rows — restarting migration"
cd "$WORK_DIR"
DB_PASS="$DB_PASS" DB_USER="$DB_USER" DB_NAME="$DB_NAME" \
    nohup python3 -u "$MIGRATION_SCRIPT" >> "$MIGRATION_LOG" 2>&1 &
NEW_PID=$!
log "migration restarted with PID $NEW_PID (json_count=$JSON_COUNT)"
exit 0
