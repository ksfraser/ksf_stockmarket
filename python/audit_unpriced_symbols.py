#!/usr/bin/env python3
"""
audit_unpriced_symbols.py — Check pending active symbols (no price data yet)
and keep only the resolvable ones; deactivate everything else.

Run once in dry mode to inspect, then again with APPLY=1 to commit.
"""
import sys, os, re
from pathlib import Path
from datetime import date, timedelta

import pymysql
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import Config

_cfg = Config("config.yaml")
MYSQL = {
    "host": _cfg.data.db_host,
    "user": _cfg.data.db_user,
    "password": _cfg.db_password,
    "database": _cfg.data.db_name,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

APPLY = os.environ.get("APPLY", "0") == "1"
_SPOT_START = (date.today() - timedelta(days=120)).isoformat()
_SPOT_END = date.today().isoformat()

_FIX_TRANSFORMS = [
    (re.compile(r"^\.\.\.$"), None),  # placeholder
    # Dot-variants like ACO-X.TO -> ACO-X.TO (no fix needed; just verify)
]


def _yf_ok(symbol: str) -> bool:
    try:
        hist = yf.Ticker(symbol).history(start=_SPOT_START, end=_SPOT_END, auto_adjust=False)
        return hist is not None and len(hist) >= 5
    except Exception:
        return False


def main() -> int:
    conn = pymysql.connect(**MYSQL)
    cur = conn.cursor()

    cur.execute("""
        SELECT sm.symbol
        FROM symbol_master sm
        LEFT JOIN stockprices sp ON sm.symbol = sp.symbol
        WHERE sm.is_active = 1 AND sp.symbol IS NULL
        ORDER BY sm.symbol
    """)
    pending = [r["symbol"] for r in cur.fetchall()]

    keep, deactivate = [], []
    for sym in pending:
        if _yf_ok(sym):
            keep.append(sym)
        else:
            deactivate.append(sym)

    print(f"Pending: {len(pending)}  keep={len(keep)}  deactivate={len(deactivate)}")
    print(f"  KEEP: {keep}")
    print(f"  DEACTIVATE: {deactivate}")

    if APPLY:
        for sym in deactivate:
            cur.execute(
                "UPDATE symbol_master SET is_active = 0, deactivated_reason = %s, deactivated_at = NOW() WHERE symbol = %s",
                ("no price data / delisted", sym),
            )
        conn.commit()
        print("Committed deactivations.")
    else:
        print("Dry run — set APPLY=1 to commit.")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
