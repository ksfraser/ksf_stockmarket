#!/bin/bash
set -euo pipefail

REPO_DIR="/home/ksf_stockmarket/ksf_stockmarket"

# Source DB credentials
if [[ -f "${REPO_DIR}/.env" ]]; then
    export DB_HOST="$(grep '^DB_HOST=' "${REPO_DIR}/.env" | cut -d= -f2)"
    export DB_NAME="$(grep '^DB_NAME=' "${REPO_DIR}/.env" | cut -d= -f2)"
    export DB_USER="$(grep '^DB_USER=' "${REPO_DIR}/.env" | cut -d= -f2)"
    export DB_PASS="$(grep '^DB_PASS=' "${REPO_DIR}/.env" | cut -d= -f2)"
    export DB_PASSWORD="$(grep '^DB_PASS=' "${REPO_DIR}/.env" | cut -d= -f2)"
    export DB_CHARSET="$(grep '^DB_CHARSET=' "${REPO_DIR}/.env" | cut -d= -f2)"
fi

cd "${REPO_DIR}"
export PYTHONPATH="${REPO_DIR}:python:python/src"

echo "$(date): Starting nightly indicator calculator"
python3.10 python/indicator_calculator.py --limit 5 --verbose 2>&1 | tee /tmp/nightly_indicator_calculator.log
echo "$(date): Nightly indicator calculator complete" | tee -a /tmp/nightly_indicator_calculator.log
