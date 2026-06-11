#!/usr/bin/env python3
"""
sqlite_scoring.py — LEGACY SCRIPT (SUPPRESSED - USE INDICATOR_CALCULATOR.PY)

This script wrote to SQLite. The MariaDB equivalent is:
  python/indicator_calculator.py (writes to ta_indicators/indicators_json)

For walk-forward scoring, see trading_pipeline_v3.py which has full L1/L2/L3 scoring.
"""
import sys
print("This script is deprecated. Use python/indicator_calculator.py instead.", file=sys.stderr)
sys.exit(0)