#!/usr/bin/env python3
"""Runtime verification for the investment-agent symbol / data-access layer.

Proves a symbol-layer fix ACTUALLY works, not just that it compiles or passes
the guard. The guard only catches *bypasses* of the shared layer (raw
`yf`/`sqlite3`); it does NOT catch logic regressions (stale duplicate resolver,
read/write symbol mismatch). Run from the investment-agent repo root:

    python3 /root/.hermes/skills/investment-agent-data-access/scripts/verify_symbol_contract.py

Or set INVESTMENT_AGENT_ROOT=/path/to/repo. Exits non-zero on any failure.
"""
import os
import sys
import tempfile

REPO_ROOT = os.environ.get("INVESTMENT_AGENT_ROOT") or os.getcwd()
for p in ("src/indicators", "python/src", "src/db", "src"):
    full = os.path.join(REPO_ROOT, p)
    if os.path.isdir(full) and full not in sys.path:
        sys.path.insert(0, full)

from src.indicators.investment_monitor import SymbolResolver
from src.db.sqlite_price_repository import SQLitePriceRepository
from src.db.stock_price_dto import StockPriceDTO
from datetime import date

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: got={got!r} want={want!r}")
    if not ok:
        failures.append(label)


print("=== canonical SymbolResolver.resolve (was mangling these) ===")
r = SymbolResolver()
check("resolve('RY')", r.resolve('RY'), 'RY')            # NYSE, NOT RY.TO
check("resolve('CM')", r.resolve('CM'), 'CM')            # NYSE, NOT CM.TO
check("resolve('SU')", r.resolve('SU'), 'SU.TO')          # TSX base
check("resolve('AGF.B')", r.resolve('AGF.B'), 'AGF-B.TO')  # .B -> -B.TO
check("resolve('CNR')", r.resolve('CNR'), 'CNR.TO')       # TSX
check("resolve('MX')", r.resolve('MX'), 'MX')             # NYSE (US_SHORT_NO_SUFFIX)
check("resolve('BIP.UN')", r.resolve('BIP.UN'), 'BIP-UN.TO')
check("resolve('AW-UN.TO')", r.resolve('AW-UN.TO'), 'AW-UN.TO')

print("=== SQLitePriceRepository write/read canonical round-trip ===")
d = tempfile.mkdtemp()
repo = SQLitePriceRepository(os.path.join(d, 'verify.db'))
repo.save(StockPriceDTO(symbol='SU', price_date=date.today(),
                        open=39.0, high=41.0, low=38.0, close=40.0, volume=1_000_000))
got = repo.get_latest('SU')  # reader resolves SU -> SU.TO
check("get_latest('SU') finds 1 row", len(got), 1)
if got:
    check("get_latest('SU') row symbol == 'SU.TO'", got[0].symbol, 'SU.TO')

print()
if failures:
    print(f"FAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("ALL SYMBOL-LAYER CHECKS PASSED")
