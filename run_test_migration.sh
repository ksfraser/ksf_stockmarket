#!/usr/bin/env bash
set -uo pipefail
cd /var/www/stockmarket-app
if [[ -f .env ]]; then
    set -a && . .env && set +a
fi
if [[ -z "$DB_PASS" ]]; then
    echo "DB_PASS still empty after sourcing .env" >&2
    exit 1
fi
echo "DB_PASS length: $(echo -n "$DB_PASS" | wc -c)"
php test_symbol_migration.php 2>&1
echo ""
echo "EXIT=$?"
