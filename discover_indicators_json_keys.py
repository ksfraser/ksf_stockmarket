#!/usr/bin/env python3
"""
discover_indicators_json_keys.py — print the distinct key set + setter stubs
----------------------------------------------------------------
Scans the newest row per symbol in indicators_json (fast: 1 row per symbol
= 410 rows total). Prints every distinct JSON key with how many symbols
carry it, plus the setter stubs to paste into IndicatorDTO.

Requires: DB_PASS env or config.yaml data.db_password.
"""
import os, sys, json, collections

import yaml
import pymysql

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, 'config.yaml')
if not os.path.exists(CONFIG_PATH):
    raise SystemExit(f"config.yaml not found at {CONFIG_PATH}")

with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)
data_cfg = cfg.get('data', {})
DB_HOST = data_cfg.get('db_host', 'ksfraser.ca')
DB_PORT = int(data_cfg.get('db_port', 3306))
DB_NAME = data_cfg.get('db_name', 'ksf_stock_market')
DB_USER = data_cfg.get('db_user', 'root')
DB_PASS = os.environ.get('DB_PASS') or data_cfg.get('db_password', '')

if not DB_PASS:
    raise SystemExit("No DB password found. Set DB_PASS env or config.yaml data.db_password.")

conn = pymysql.connect(
    host=DB_HOST, port=DB_PORT, user=DB_USER,
    password=DB_PASS, database=DB_NAME,
    charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
)
try:
    cur = conn.cursor()

    cur.execute("SELECT COUNT(DISTINCT symbol) AS n FROM indicators_json")
    n_symbols = int((cur.fetchone() or {}).get('n') or 0)

    cur.execute("SELECT COUNT(*) AS cnt FROM indicators_json")
    total_rows = int((cur.fetchone() or {}).get('cnt') or 0)

    print(f"indicators_json: {total_rows:,} rows across {n_symbols:,} symbols")
    print(f"{'='*70}\n")

    print("Newest row per symbol — key discovery ...\n", flush=True)
    cur.execute(
        "SELECT ij.symbol, ij.data FROM indicators_json ij "
        "INNER JOIN (SELECT symbol, MAX(id) AS max_id FROM indicators_json GROUP BY symbol) g "
        "ON ij.symbol = g.symbol AND ij.id = g.max_id"
    )
    sym_rows = cur.fetchall()

    key_counts = collections.Counter()
    for row in sym_rows:
        try:
            d = json.loads(row['data'])
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(d, dict):
            for k in d.keys():
                key_counts[k] += 1

    print(f"Distinct keys from {len(sym_rows)} symbols' newest rows: {len(key_counts)}\n")
    print(f"{'#':>3}  {'#SYMS':>6}  KEY")
    print("-" * 60)
    for i, key in enumerate(sorted(key_counts.keys()), 1):
        cnt = key_counts[key]
        print(f"{i:>3}  {cnt:>6}  {key}")

    print(f"\n{'='*70}")
    print(f"\nSetter stubs to add to IndicatorDTO (copy everything below the line):")
    print("=" * 70)
    for key in sorted(key_counts.keys()):
        print(f"    @_setter")
        print(f"    def set_{key}(self, v):")
        print(f"        self.{key} = v")
        print(f"")
finally:
    conn.close()
