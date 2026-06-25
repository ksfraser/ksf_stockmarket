#!/usr/bin/env python3
"""
fix_symbols.py — Fix common symbol format issues in symbol_master and
deactivate symbols that are genuinely delisted / unfixable.

Transformations applied:
  * TSX:SYM   -> SYM.TO
  * NEO:SYM   -> SYM.TO
  * SYM-HK.HK -> SYM.HK
  * SYM.HK.HK -> SYM.HK

After transformation, each candidate is spot-checked with yfinance.
Symbols that still fail are set is_active = 0 with a reason.
"""
import sys
import re
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

DRY_RUN = False

_SPOT_START = (date.today() - timedelta(days=120)).isoformat()
_SPOT_END = date.today().isoformat()

_TRANSFORMS = [
    (re.compile(r"^TSX:(.+)$"), lambda m: m.group(1) if m.group(1).endswith(".TO") else m.group(1) + ".TO"),
    (re.compile(r"^NEO:(.+)$"), lambda m: m.group(1) if m.group(1).endswith(".TO") else m.group(1) + ".TO"),
    (re.compile(r"^(.+)-HK\.HK$"), r"\1.HK"),
    (re.compile(r"^(.+)\.HK\.HK$"), r"\1.HK"),
]


def _propose_fix(symbol: str):
    for pattern, replacement in _TRANSFORMS:
        if pattern.match(symbol):
            if callable(replacement):
                return replacement(pattern.match(symbol))
            return pattern.sub(replacement, symbol)
    return None


def _yf_ok(symbol: str) -> bool:
    try:
        hist = yf.Ticker(symbol).history(start=_SPOT_START, end=_SPOT_END, auto_adjust=False)
        return hist is not None and len(hist) >= 5
    except Exception:
        return False


def main() -> int:
    conn = pymysql.connect(**MYSQL)
    cur = conn.cursor()

    cur.execute("SELECT symbol FROM symbol_master WHERE is_active = 1")
    active = {r["symbol"] for r in cur.fetchall()}

    to_fix = []
    for sym in sorted(active):
        fix = _propose_fix(sym)
        if fix and fix != sym:
            if fix in active:
                print(f"SKIP {sym} -> {fix} (already exists)")
                to_fix.append((sym, "duplicate-format", fix))
            else:
                to_fix.append((sym, fix, None))

    print(f"Candidates to fix: {len(to_fix)}")

    ok = fail = skip = 0
    for sym, fix, existing in to_fix:
        if existing:
            reason = f"duplicate format; canonical={existing}"
            if not DRY_RUN:
                cur.execute(
                    "UPDATE symbol_master SET is_active = 0, deactivated_reason = %s, deactivated_at = NOW() WHERE symbol = %s",
                    (reason, sym),
                )
            print(f"DEACTIVATE {sym} -> {reason}")
            skip += 1
            continue

        if not _yf_ok(fix):
            reason = "delisted/unresolvable after format fix"
            if not DRY_RUN:
                cur.execute(
                    "UPDATE symbol_master SET is_active = 0, deactivated_reason = %s, deactivated_at = NOW() WHERE symbol = %s",
                    (reason, sym),
                )
            print(f"DEACTIVATE {sym} -> {fix} ({reason})")
            fail += 1
            continue

        if not DRY_RUN:
            # Check if target already exists to avoid PK collision
            cur.execute("SELECT COUNT(*) as n FROM symbol_master WHERE symbol = %s", (fix,))
            if cur.fetchone()["n"] > 0:
                reason = f"duplicate format after fix; canonical={fix}"
                cur.execute(
                    "UPDATE symbol_master SET is_active = 0, deactivated_reason = %s, deactivated_at = NOW() WHERE symbol = %s",
                    (reason, sym),
                )
                print(f"DEACTIVATE {sym} -> {fix} (duplicate after fix)")
                skip += 1
                continue
            cur.execute(
                "UPDATE symbol_master SET symbol = %s WHERE symbol = %s",
                (fix, sym),
            )
        print(f"FIX {sym} -> {fix}")
        ok += 1

    conn.commit()
    conn.close()

    print(f"\nDone. ok={ok}, fail={fail}, skip={skip}, dry_run={DRY_RUN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
