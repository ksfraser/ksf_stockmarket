#!/usr/bin/env python3
"""Fast pre-guard verification for an investment-agent layered-refactor phase.

Necessary-but-not-sufficient checks (always ALSO run a runtime DataSource
round-trip per phase — see references/phase3-service-extraction.md):
  1. No residual guard-BLOCKED patterns in the edited modules.
  2. py_compile clean for all given files.
  3. Optional: import a service module (proves it loads through the layer).

NOTE: this is a fast substring scan. The real guard
(`scripts/guard_standardized_access.py --staged`) is the authoritative gate.
This script catches the obvious regressions before you stage.

Usage:
  python3 scripts/verify_phase_refactor.py \
      --files src/analysis/symbol_performance.py src/rules/rule_registry.py \
      --service src.services.symbol_performance_service \
      --repo-root /root/.hermes/workspace/investment-agent
"""
from __future__ import annotations

import argparse
import os
import sys
import subprocess

# Subset of the guard's BLOCKED patterns (substring scan). The authoritative list
# lives in scripts/guard_standardized_access.py + references/guard-allowlist.md.
BLOCKED = [
    "import yfinance", "yf.Ticker", "yfinance.download", ".history(",
    "pymysql.connect(", "sqlite3.connect(",
    "password='", 'password="',
    "import openai", "OpenAI(", "chat.completions",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--service", default=None, help="dotted module path to import")
    ap.add_argument("--repo-root", default=os.getcwd())
    args = ap.parse_args()
    root = args.repo_root
    ok = True

    # 1. residual blocked patterns
    for rel in args.files:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            print(f"MISSING {rel}")
            ok = False
            continue
        txt = open(p, encoding="utf-8").read()
        for pat in BLOCKED:
            if pat in txt:
                print(f"FAIL blocked pattern '{pat}' still present in {rel}")
                ok = False
    print("OK no residual guard-blocked patterns" if ok else "FAIL residual patterns")

    # 2. py_compile (does NOT catch undefined names — run a runtime smoke too)
    for rel in args.files:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        r = subprocess.run([sys.executable, "-m", "py_compile", p],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL py_compile {rel}:\n{r.stderr}")
            ok = False
    print("OK py_compile clean")

    # 3. optional service import
    if args.service:
        sys.path.insert(0, root)
        sys.path.insert(0, os.path.join(root, "src"))
        try:
            __import__(args.service)
            print(f"OK service import {args.service}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL service import {args.service}: {e!r}")
            ok = False

    print("VERIFY OK" if ok else "VERIFY FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
