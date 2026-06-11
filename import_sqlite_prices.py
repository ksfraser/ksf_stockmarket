#!/usr/bin/env python3
"""
import_sqlite_prices.py — ONE-TIME MIGRATION SCRIPT (COMPLETED)

This script migrated historical price data from SQLite to MariaDB.
Migration was completed on 2025-06-10. The SQLite DB (analysis_results.db)
is now empty and no longer needed.

For ongoing price updates, use:
  python/fetch_prices.py (writes directly to MariaDB partitioned stockprices table)
"""
import sys
print("Migration completed. This script is no longer needed.", file=sys.stderr)
sys.exit(0)