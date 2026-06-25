#!/usr/bin/env python3
"""
cleanup_unresolvable_symbols.py — Deactivate symbols yfinance can't resolve.
"""
import re, sys, pymysql
from datetime import datetime
from config_loader import Config

def is_bad(sym: str) -> bool:
    if sym.startswith('AMEX:') or sym.startswith('OTC:') or sym.startswith('NYSE:') or sym.startswith('NASDAQ:'):
        return True
    if '/' in sym:
        return True
    if re.search(r'\.[A-Z]\.TO$', sym):
        return True
    if re.search(r'/PD\.TO$|/PB\.TO$|/PE\.TO$|/PF\.TO$|/PG\.TO$|/PH\.TO$|/PI\.TO$|/PJ\.TO$|/PK\.TO$|/PL\.TO$|/PM\.TO$|/PN\.TO$|/PO\.TO$|/PQ\.TO$|/PS\.TO$|/PT\.TO$', sym):
        return True
    return False

def main():
    cfg = Config('config.yaml')
    conn = pymysql.connect(host=cfg.data.db_host, user=cfg.data.db_user, password=cfg.db_password, database=cfg.data.db_name, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM symbol_master WHERE is_active = 1")
    rows = [r['symbol'] for r in cur.fetchall()]
    bad = [s for s in rows if is_bad(s)]
    print(f"Scanning {len(rows)} active symbols, found {len(bad)} bad patterns")
    if not bad:
        conn.close()
        return
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    placeholders = ','.join(['%s'] * len(bad))
    cur.execute(f"UPDATE symbol_master SET is_active = 0, deactivated_reason = 'unresolvable_yfinance', last_updated = %s WHERE symbol IN ({placeholders})", [now] + bad)
    conn.commit()
    print(f"Deactivated {cur.rowcount} symbols")
    conn.close()

if __name__ == '__main__':
    main()
