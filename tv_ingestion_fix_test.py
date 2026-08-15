#!/usr/bin/env python3
"""
Regression tests for the TradingView ingestion pipeline fixes.

Bug 1 (symbol mangling): _translate_symbol must NOT append ".TO" to
US/OTC tickers (NASDAQ:HOPE -> HOPE); only Canadian (TSX/NEO) ones get the
suffix. The old code appended ".TO" to everything, corrupting ~3,300 US
dividend/value/quality tickers into invalid Toronto symbols.

Bug 2 (run-window): _latest_run must return the FULL latest screener run,
not just the single newest run_at second. The live check is gated behind
TV_LIVE_TEST=1 because it touches the production MariaDB.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO_ROOT)

import tv_screener as tv


def test_translate_symbol():
    cases = [
        ("NASDAQ:HOPE", "HOPE"),
        ("NYSE:WY", "WY"),
        ("OTC:BXBLY", "BXBLY"),
        ("TSX:WTE", "WTE.TO"),
        ("TSX:RY", "RY.TO"),
        ("NEO:CIA", "CIA.TO"),
        ("TSX:XYZ.UN", "XYZ.UN.TO"),
        ("NEO:ABC.UN", "ABC.UN.TO"),
        ("HOPE.TO", "HOPE.TO"),          # already-canonical pass-through
        ("XYZ.UN.TO", "XYZ.UN.TO"),      # already-canonical pass-through
        ("", ""),
        ("TSE:XYZ", "XYZ"),              # non-Canadian exchange -> bare
        ("TSX:SLF.PR.G", "SLF.PR.G.TO"),
    ]
    failures = []
    for raw, expected in cases:
        got = tv._translate_symbol(raw)
        if got != expected:
            failures.append((raw, got, expected))
    return failures


def test_latest_run_live():
    """Gated behind TV_LIVE_TEST so it does not run on import / in CI."""
    if os.environ.get("TV_LIVE_TEST") != "1":
        return "SKIPPED (set TV_LIVE_TEST=1 to run against the live DB)"
    from python.ingest_screener_symbols import _connect, _latest_run
    conn = _connect()
    try:
        latest = _latest_run(conn)
    finally:
        conn.close()
    rc = latest.get("row_count", 0)
    assert rc > 100, f"Expected full run (>100 rows), got {rc}"
    return f"PASS (row_count={rc}, window {latest.get('window_start')} -> {latest.get('window_end')})"


if __name__ == "__main__":
    fails = test_translate_symbol()
    if fails:
        print("TRANSLATE TESTS: FAIL")
        for raw, got, exp in fails:
            print(f"  {raw!r} -> {got!r} (expected {exp!r})")
        sys.exit(1)
    print("TRANSLATE TESTS: PASS (13/13)")
    live = test_latest_run_live()
    print("LIVE WINDOW TEST:", live)
    sys.exit(0)
