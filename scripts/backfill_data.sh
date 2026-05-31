#!/bin/bash
# backfill_data.sh — Fetch historical data for all symbols missing from the DB.

LOG="/home/ksf_stockmarket/ksf_stockmarket/data_fetch_progress.log"
PY="/usr/bin/python3"
DIR="/home/ksf_stockmarket/ksf_stockmarket"
BATCH=10
SLEEPPERBATCH=30
MAXRETRIES=3

echo "===== Data Backfill Started: $(date) ====" >> $LOG

# Get symbols without any price data
SYMS=$($PY -c "
import pymysql
conn = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market', cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()
c.execute('''
    SELECT sm.symbol FROM symbol_master sm
    LEFT JOIN (SELECT DISTINCT symbol FROM stockprices) sp ON sm.symbol = sp.symbol
    WHERE sp.symbol IS NULL
    ORDER BY sm.symbol
''')
for r in c.fetchall():
    print(r['symbol'])
conn.close()
" 2>/dev/null)

TOTAL=$(echo "$SYMS" | wc -l)
echo "Symbols to fetch: $TOTAL" | tee -a $LOG

COUNT=0
FAILCOUNT=0
BATCHCOUNT=0

for SYM in $SYMS; do
    COUNT=$((COUNT + 1))
    BATCHCOUNT=$((BATCHCOUNT + 1))

    SUCCESS=0
    for RETRY in $(seq 1 $MAXRETRIES); do
        OUTPUT=$($PY $DIR/python/daily_pipeline.py --mode backfill --symbol "$SYM" --start 2000-01-01 --end 2026-05-31 2>&1)
        if echo "$OUTPUT" | grep -q "Added\|rows\|up to date"; then
            SUCCESS=1
            break
        fi
        sleep 5
    done

    if [ $SUCCESS -eq 1 ]; then
        echo "[$COUNT/$TOTAL] OK: $SYM" >> $LOG
    else
        FAILCOUNT=$((FAILCOUNT + 1))
        echo "[$COUNT/$TOTAL] FAIL: $SYM" >> $LOG
    fi

    if [ $((COUNT % 10)) -eq 0 ]; then
        echo "Progress: $COUNT/$TOTAL done, $FAILCOUNT failures" | tee -a $LOG
    fi

    if [ $BATCHCOUNT -ge $BATCH ]; then
        BATCHCOUNT=0
        sleep $SLEEPPERBATCH
    fi
done

echo "" >> $LOG
echo "===== Indicators: $(date) ====" >> $LOG
$PY $DIR/python/daily_pipeline.py --mode indicators 2>&1 | tee -a $LOG
echo "" >> $LOG
echo "===== DONE: $(date) =====" >> $LOG
