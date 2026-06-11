#!/usr/bin/env python3
"""
migrate_sqlite_to_mysql.py — ONE-TIME MIGRATION SCRIPT (COMPLETED)

This script migrated analytics data from SQLite to MariaDB. Migration was completed.
All critical data (ta_indicators: 61,336 rows, indicators_json: 212,969 rows) now exists
in MariaDB and is actively maintained.

The SQLite DB (analysis_results.db) is now empty and no longer referenced.

For ongoing indicator calculations, use:
  python/indicator_calculator.py (writes to MariaDB ta_indicators/indicators_json)
"""
import sys
print("Migration completed. Use python/indicator_calculator.py for ongoing indicator updates.", file=sys.stderr)
sys.exit(0)