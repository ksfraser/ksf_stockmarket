# Data Importer.py — Full Port Worked Example

`python/data_importer.py` (819 lines) was the most complex `mysql.connector` → `pymysql` + DAO port in the ksf_stockmarket codebase. It had **all five** common mistakes from the migration reference simultaneously, plus a legacy `write_prices()` that targeted 14 columns (`day_open`, `day_high`, `day_low`, `day_close`, `previous_close`, `day_change`, `bid`, `ask`, `source`, `updated_at`) that don't exist in `ksfraser_stock_market.stockprices`.

This file is referenced from [mysql-to-pymysql-migration.md](mysql-to-pymysql-migration.md) as a worked example. This document captures the pre-fix state and the fix sequence for future sessions porting large scripts.

## Pre-fix state (what was broken)

| Issue | How detected | Count |
|-------|-------------|-------|
| `write_prices()` raw SQL targeting 14 non-existent columns | Read function body (lines 235-369) | 24 column references |
| Bare `except MySQLError` (not `pymysql_err.MySQLError`) | `grep -n "except MySQLError"` | 2 locations |
| `conn.is_connected()` on pymysql connection | `grep -n "is_connected()"` | 3 locations |
| `DB_CONFIG` references scattered across file | `grep -n "DB_CONFIG"` | 8 locations |
| Missing `logger = logging.getLogger(__name__)` | LSP diagnostics | 0 definitions |
| `write_prices()` uses raw `cursor.executemany` instead of DAO | Read function body | 1 function |

## Why not one big write_file

The fix was attempted as a single `write_file` of the complete 819-line corrected file. That write was truncated by a turn timeout + environment reset. The file reverted to its pre-fix state and the work had to be re-done.

Subsequent attempts used **targeted `patch` operations** on specific function bodies and line ranges. This survived the env-reset cycle because each patch is:

- Small enough to complete in one turn (no timeout risk)
- Idempotent — if the patch doesn't match (because a prior turn's patch already landed), you see the failure immediately and re-read to assess
- Verifiable with `grep` before moving to the next fix

## Fix sequence (in order)

1. **Rewrite `write_prices()` function body** — one patch from `def write_prices(` through the old `return inserted`. Replacement builds `PriceRow` objects and calls `create_central_stockprice_dao(central_db=conn).write_prices(rows)`.

2. **Remove old SQL tail** — the step-1 patch left a garbled `return affected, %s, %s, ...` line followed by the old SQL body. Second patch removes from that garbled line through the end of the old function body (the `batch = []` loop, `executemany`, counting logic, etc.).

3. **Fix `MySQLError`** — `replace_all=true`: `except MySQLError` → `except pymysql_err.MySQLError`.

4. **Fix `is_connected()`** — `replace_all=true`: `conn.is_connected()` → `_db_open(conn)`. Then fix the `finally` block which inherited a bad `close_after` variable reference from the patch context — change `if close_after and _db_open(conn)` → `if _db_open(conn)`.

5. **Fix `DB_CONFIG`** — four separate patches:
   - Docstring text: "opened using DB_CONFIG" → "opened using environment variables"
   - Docstring text: "override DB_CONFIG" → "override connection params (defaults to env vars)"
   - Code: `cfg = db_config or DB_CONFIG` → inline env-var dict with `os.environ.get()`
   - Comment + CLI defaults: `# Override DB_CONFIG with CLI args` → reworded; `default=DB_CONFIG['host']` → `default=os.environ.get('DB_HOST', 'ksfraser.ca')` etc.

6. **Add `logger` definition** — insert `logger = logging.getLogger(__name__)` after the `TSX_PATTERN` constant.

## Verification commands

```bash
cd /home/ksf_stockmarket/ksf_stockmarket
python3 -m py_compile python/data_importer.py && echo "COMPILES OK"

# Each of these should return 0 (or near-0 for CSV_COLUMN_MAP):
grep -c "day_open\|day_high\|day_low\|day_close\|previous_close\|day_change\|bid.*ask\|source.*updated_at" python/data_importer.py
grep -c "except MySQLError" python/data_importer.py
grep -c "is_connected()" python/data_importer.py
grep -c "DB_CONFIG" python/data_importer.py

# Each of these should return >0 or 1:
grep -c "create_central_stockprice_dao\|dao.write_prices\|PriceRow" python/data_importer.py
grep -c "^logger = " python/data_importer.py
grep -c "pymysql_err.MySQLError" python/data_importer.py
```

**Note on the 6 remaining `previous_close`/`day_change` references:** these are in `CSV_COLUMN_MAP` for reading external CSV files that *may* contain those columns as input data. They are NOT written to the DB. This is legitimate — the legacy SQL that targeted them as DB columns is gone.

## Pattern for large-file porting

When porting a 500+ line script with multiple scattered issues:

1. **Count before fixing** — `grep -c` each issue pattern to know the scope
2. **Patch in order of dependency** — fix the function that everything else depends on first (`write_prices()`), then the error handling, then the credential patterns
3. **Verify after each patch** — don't batch 5 patches and then discover #3 didn't match
4. **Re-read the file when a patch fails** — the file may have changed from a prior turn's partial fix
5. **Use `replace_all=true` for repeated patterns** — `is_connected()`, `MySQLError`, `DB_CONFIG` each appear multiple times
6. **Watch for context bleed** — a patch that replaces a multi-line block can leave variables from the old block referenced in the new code (e.g. `close_after` in the `finally` block)
