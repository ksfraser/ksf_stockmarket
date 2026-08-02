#!/bin/bash
set -euo pipefail

cd /home/ksf_stockmarket/ksf_stockmarket

# Source environment variables
if [ -f ".env" ]; then
    export DB_HOST="$(grep '^DB_HOST=' .env | cut -d= -f2)"
    export DB_NAME="$(grep '^DB_NAME=' .env | cut -d= -f2)"
    export DB_USER="$(grep '^DB_USER=' .env | cut -d= -f2)"
    export DB_PASS="$(grep '^DB_PASS=' .env | cut -d= -f2)"
    export DB_PASSWORD="$(grep '^DB_PASS=' .env | cut -d= -f2)"
    export DB_CHARSET="$(grep '^DB_CHARSET=' .env | cut -d= -f2)"
fi

export PYTHONPATH="/home/ksf_stockmarket/ksf_stockmarket:python:python.src"

echo "$(date): Starting nightly analyst ratings population"
python3.10 python/populate_analyst_ratings.py 2>&1 | tee /tmp/populate_analyst_ratings.log
echo "$(date): Nightly analyst ratings population complete" | tee -a /tmp/populate_analyst_ratings.log
