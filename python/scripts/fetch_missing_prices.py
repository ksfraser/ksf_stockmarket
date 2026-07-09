#!/usr/bin/env python3
"""Fetch prices for active symbols that don't have any price data."""
import sys
from pathlib import Path

_PYTHON_DIR = Path(__file__).resolve().parent.parent.parent
_PYTHON_SRC = _PYTHON_DIR / 'python' / 'src'
for _p in (str(_PYTHON_DIR), str(_PYTHON_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pymysql
import pymysql.cursors
import re
import subprocess
import os
from config_loader import Config

cfg = Config(str(_PYTHON_DIR / 'config.yaml'))
MYSQL = dict(
    host=cfg.data.db_host,
    user=cfg.data.db_user,
    password=cfg.db_password,
    database=cfg.data.db_name,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=20,
    read_timeout=120,
    write_timeout=120,
)

conn = pymysql.connect(**MYSQL)
with conn.cursor() as c:
    c.execute("SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
    all_syms = [r['symbol'] for r in c.fetchall()]
    c.execute("SELECT DISTINCT symbol FROM stockprices")
    existing = {r['symbol'] for r in c.fetchall()}
conn.close()

def is_yfinance_resolvable(sym):
    if sym.startswith('AMEX:') or sym.startswith('OTC:') or sym.startswith('NYSE:') or sym.startswith('NASDAQ:'):
        return False
    if '/' in sym:
        return False
    if re.search(r'\.[A-Z]\.TO$', sym):
        return False
    if re.search(r'/PD\.TO$|/PB\.TO$|/PE\.TO$|/PF\.TO$|/PG\.TO$|/PH\.TO$|/PI\.TO$|/PJ\.TO$|/PK\.TO$|/PL\.TO$|/PM\.TO$|/PN\.TO$|/PO\.TO$|/PQ\.TO$|/PS\.TO$|/PT\.TO$', sym):
        return False
    return True

missing = sorted(set(all_syms) - existing)
resolvable = [s for s in missing if is_yfinance_resolvable(s)]
print(f"Missing total: {len(missing)}")
print(f"Resolvable: {len(resolvable)}")

if not resolvable:
    print("Nothing to fetch.")
    sys.exit(0)

print(f"Running fetch for {len(resolvable)} symbols...")
fetch_script = str(_PYTHON_DIR / 'python' / 'fetch_prices.py')
manifest_path = str(_PYTHON_DIR / 'results' / 'fetch_missing_prices_manifest.csv')
os.makedirs(str(_PYTHON_DIR / 'results'), exist_ok=True)
cmd = [
    sys.executable,
    fetch_script,
    '--symbols', ','.join(resolvable),
    '--manifest', manifest_path,
]
print(f"Running fetch for {len(resolvable)} symbols...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
print(result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-2000:])
print(f"Exit code: {result.returncode}")
