#!/bin/bash
# ============================================================================
# ksf_stockmarket — Per-Table Backup Script
# ============================================================================
# Solves the 2013 4GB truncation problem: each table is dumped separately
# so a failure only affects one table, not the whole database.
#
# Usage: ./backup.sh [full|incremental|critical]
#   full       — All tables (weekly)
#   incremental — Only tables with recent changes (daily)
#   critical   — Only small, critical tables (daily, fast)
# ============================================================================

set -euo pipefail

DB_NAME="ksf_stockmarket"
DB_USER="ksf_stockmarket"
DB_PASS="${DB_PASS:-ksfuser2024!}"
BACKUP_BASE="/backup/ksf_stockmarket"
DATE=$(date +%Y%m%d)
BACKUP_DIR="${BACKUP_BASE}/${DATE}"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

LOG_FILE="${BACKUP_DIR}/backup.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=========================================="
echo "Backup started: $(date)"
echo "Mode: ${1:-full}"
echo "Database: ${DB_NAME}"
echo "Backup dir: ${BACKUP_DIR}"
echo "=========================================="

# Function: backup a single table
backup_table() {
    local table=$1
    local compress=$2  # "yes" or "no"
    local outfile="${BACKUP_DIR}/${table}.sql"
    
    echo -n "  Backing up ${table}... "
    
    if mysqldump \
        --single-transaction \
        --quick \
        --lock-tables=false \
        --set-gtid-purged=OFF \
        -u"${DB_USER}" -p"${DB_PASS}" \
        "${DB_NAME}" "${table}" > "${outfile}" 2>/dev/null; then
        
        local size=$(stat -c%s "${outfile}" 2>/dev/null || echo 0)
        
        if [ "${compress}" = "yes" ] && [ "${size}" -gt 1048576 ]; then
            gzip "${outfile}"
            size=$(stat -c%s "${outfile}.gz" 2>/dev/null || echo 0)
            echo "OK (compressed, $(numfmt --to=iec ${size}))"
        else
            echo "OK ($(numfmt --to=iec ${size}))"
        fi
    else
        echo "FAILED"
        echo "ERROR: Failed to backup ${table}" >> "${LOG_FILE}"
    fi
}

# Function: backup a specific partition
backup_partition() {
    local table=$1
    local partition=$2
    local outfile="${BACKUP_DIR}/${table}_${partition}.sql"
    
    echo -n "  Backing up ${table} partition ${partition}... "
    
    if mysqldump \
        --single-transaction \
        --quick \
        --lock-tables=false \
        --set-gtid-purged=OFF \
        -u"${DB_USER}" -p"${DB_PASS}" \
        "${DB_NAME}" "${table}" \
        --where "price_year = ${partition#p_}" > "${outfile}" 2>/dev/null; then
        
        local size=$(stat -c%s "${outfile}" 2>/dev/null || echo 0)
        if [ "${size}" -gt 1048576 ]; then
            gzip "${outfile}"
            size=$(stat -c%s "${outfile}.gz" 2>/dev/null || echo 0)
        fi
        echo "OK ($(numfmt --to=iec ${size}))"
    else
        echo "FAILED"
    fi
}

# Critical tables: small, change frequently, must not be lost
CRITICAL_TABLES=(
    "users" "roles" "transactiontype" "accounttype"
    "portfolio" "transaction" "watchlists" "watchlist_symbols"
    "alerts" "alertsraised"
    "backtest_strategies" "backtest_runs"
)

# Reference tables: small, rarely change
REFERENCE_TABLES=(
    "stockexchange" "bondrate" "alerttype"
    "symbol_status" "data_import_log"
)

# Indicator tables: medium size, regenerable
INDICATOR_TABLES=(
    "daily_indicators" "technicalanalysis" "ratios"
    "signal_weights" "backtest_trades" "backtest_positions"
)

# Price data: large, partitioned
PRICE_TABLES=(
    "stockprices"
)

# Fundamental data: medium, changes quarterly
FUNDAMENTAL_TABLES=(
    "stockinfo" "fin_statement" "portfolio_history"
)

MODE="${1:-full}"

case "${MODE}" in
    critical)
        echo ""
        echo "=== Critical Tables (daily) ==="
        for table in "${CRITICAL_TABLES[@]}"; do
            backup_table "${table}" "no"
        done
        ;;
    
    incremental)
        echo ""
        echo "=== Critical Tables ==="
        for table in "${CRITICAL_TABLES[@]}"; do
            backup_table "${table}" "no"
        done
        
        echo ""
        echo "=== Reference Tables ==="
        for table in "${REFERENCE_TABLES[@]}"; do
            backup_table "${table}" "no"
        done
        
        echo ""
        echo "=== Current Year Price Partition ==="
        CURRENT_YEAR=$(date +%Y)
        backup_partition "stockprices" "p_${CURRENT_YEAR}"
        
        echo ""
        echo "=== Recent Indicator Data ==="
        for table in "${INDICATOR_TABLES[@]}"; do
            backup_table "${table}" "yes"
        done
        ;;
    
    full)
        echo ""
        echo "=== Critical Tables ==="
        for table in "${CRITICAL_TABLES[@]}"; do
            backup_table "${table}" "no"
        done
        
        echo ""
        echo "=== Reference Tables ==="
        for table in "${REFERENCE_TABLES[@]}"; do
            backup_table "${table}" "no"
        done
        
        echo ""
        echo "=== Fundamental Tables ==="
        for table in "${FUNDAMENTAL_TABLES[@]}"; do
            backup_table "${table}" "yes"
        done
        
        echo ""
        echo "=== Indicator Tables ==="
        for table in "${INDICATOR_TABLES[@]}"; do
            backup_table "${table}" "yes"
        done
        
        echo ""
        echo "=== Price Data (all partitions) ==="
        # Get list of partitions from information_schema
        PARTITIONS=$(mysql -u"${DB_USER}" -p"${DB_PASS}" -N -e "
            SELECT PARTITION_NAME 
            FROM INFORMATION_SCHEMA.PARTITIONS 
            WHERE TABLE_SCHEMA='${DB_NAME}' 
              AND TABLE_NAME='stockprices' 
              AND PARTITION_NAME IS NOT NULL
            ORDER BY PARTITION_NAME" 2>/dev/null)
        
        for partition in ${PARTITIONS}; do
            backup_partition "stockprices" "${partition}"
        done
        ;;
    
    *)
        echo "Usage: $0 [full|incremental|critical]"
        exit 1
        ;;
esac

# Cleanup old backups
echo ""
echo "=== Cleanup (keeping last ${RETENTION_DAYS} days) ==="
find "${BACKUP_BASE}" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} \; -print

echo ""
echo "Backup completed: $(date)"
echo "Backup size: $(du -sh ${BACKUP_DIR} | cut -f1)"
echo "=========================================="
