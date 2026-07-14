#!/usr/bin/env bash
# run_one_advisor_backtest.sh
# Pops one advisor slug from a queue file and runs its backtest.
# Queue file: ~/.hermes/.advisor_backtest_queue

QUEUE_FILE="${HOME}/.hermes/.advisor_backtest_queue"
REPO_DIR="/home/ksf_stockmarket/ksf_stockmarket"
START_DATE="2022-01-01"
END_DATE="2026-07-12"
FREQUENCY="weekly"
INITIAL="100000"
LOG_DIR="${HOME}/.hermes/cron/logs"
mkdir -p "$LOG_DIR"

if [[ ! -f "$QUEUE_FILE" ]]; then
    echo "No queue file at $QUEUE_FILE" >&2
    exit 1
fi

SLUG=$(head -n 1 "$QUEUE_FILE" | tr -d '[:space:]')
if [[ -z "$SLUG" ]]; then
    echo "Queue empty." >&2
    exit 0
fi

tail -n +2 "$QUEUE_FILE" > "${QUEUE_FILE}.tmp" && mv "${QUEUE_FILE}.tmp" "$QUEUE_FILE"

LOG_FILE="${LOG_DIR}/advisor_backtest_${SLUG}_$(date +%Y%m%d_%H%M%S).log"
cd "$REPO_DIR"
PYTHONPATH=".:python:python/src" python3 python/advisor_backtest.py \
    --slug "$SLUG" \
    --start "$START_DATE" \
    --end "$END_DATE" \
    --frequency "$FREQUENCY" \
    --initial "$INITIAL" \
    > "$LOG_FILE" 2>&1
echo "Advisor $SLUG backtest completed. Log: $LOG_FILE"
exit 0
