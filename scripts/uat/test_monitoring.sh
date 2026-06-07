#!/bin/bash
# UAT Tests for ksf_stockmarket monitoring system
# Run from /opt/stockmarket directory

set -e

SCRIPTS_DIR="/opt/stockmarket/python/src/monitoring"
LOG_DIR="/var/log/stockmarket"

echo "=== ksf_stockmarket Monitoring UAT ==="
echo "Date: $(date)"
echo

# Test 1: Database Connection
echo "Test 1: Database Connection"
python3 -c "
import sys
sys.path.insert(0, '/opt/stockmarket/python/src')
from database import get_connection
try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT 1')
    print('  ✓ Database connection successful')
    conn.close()
except Exception as e:
    print(f'  ✗ Database connection failed: {e}')
    sys.exit(1)
" || exit 1
echo

# Test 2: Symbol Resolver
echo "Test 2: Symbol Resolver Module"
python3 -c "
import sys
sys.path.insert(0, '/opt/stockmarket/python/src')
from symbol_resolver import resolve_for_yfinance, detect_ticker_type

tests = [
    ('RY.TO', 'RY.TO'),
    ('SPY', 'SPY'),
    ('XIC', 'XIC'),
]
for input_sym, expected in tests:
    result = resolve_for_yfinance(input_sym)
    if result == expected:
        print(f'  ✓ {input_sym} → {result}')
    else:
        print(f'  ✗ {input_sym} → {result} (expected {expected})')
        sys.exit(1)
" || exit 1
echo

# Test 3: Volume Spike Script
echo "Test 3: Volume Spike Script"
if [ -f "$SCRIPTS_DIR/volume_spike.py" ]; then
    python3 "$SCRIPTS_DIR/volume_spike.py" --ticker RY.TO --json > /tmp/volume_test.json 2>&1
    if python3 -c "
import json
with open('/tmp/volume_test.json') as f:
    r = json.load(f)
assert 'timestamp' in r
assert 'n_checked' in r
assert isinstance(r['n_checked'], int)
print(f'  ✓ Volume spike check works (checked {r[\"n_checked\"]} symbol)')
"; then
        :
    else
        echo "  ✗ Volume spike JSON output invalid"
        cat /tmp/volume_test.json
        exit 1
    fi
else
    echo "  ⚠ Volume spike script not found (will be created during migration)"
fi
echo

# Test 4: Directory Structure
echo "Test 4: Directory Structure"
for dir in /opt/stockmarket /opt/stockmarket/python/src/monitoring "$LOG_DIR"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir exists"
    else
        echo "  ⚠ $dir does not exist (will be created)"
    fi
done
echo

# Test 5: Environment Variables
echo "Test 5: Environment Configuration"
if [ -f "/opt/stockmarket/.env" ]; then
    if grep -q "DB_HOST" /opt/stockmarket/.env; then
        echo "  ✓ .env file present with DB_HOST"
    else
        echo "  ✗ .env missing DB_HOST"
        exit 1
    fi
else
    echo "  ⚠ .env not found (will be created from vault)"
fi
echo

echo "=== UAT Complete ==="
echo "All tests passed. Ready for deployment."