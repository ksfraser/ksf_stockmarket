#!/usr/bin/env bash
# run_tv_screener.sh — cron wrapper for tv_screener.py (RESILIENT VERSION)
#
# FIXES: Shorter timeouts + retry logic + smaller query batches to avoid
# the 600s cron timeout. TradingView API is slow (~2-3 min per screen).
#
set -uo pipefail
REPO_DIR="/home/ksf_stockmarket/ksf_stockmarket"
cd "$REPO_DIR" || exit 1
export PYTHONPATH="$REPO_DIR/python/src:$REPO_DIR/python"
if [[ -f ".env" ]]; then
    set -a && . ./.env && set +a
fi

echo "=== TradingView Screener (Resilient) ==="
echo "Run: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> /tmp/tv_screener_cron.log 2>&1

# Run the Python script (which has retry logic + shorter timeouts)
python3 -u "$REPO_DIR/scripts/tv_screener_resilient.py" 2>&1
EXIT_CODE=$?

echo "TradingView screener exit code: $EXIT_CODE" >> /tmp/tv_screener_cron.log 2>&1
exit $EXIT_CODE
