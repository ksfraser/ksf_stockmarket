# mysql.connector → pymysql migration notes

Session context: multiple scripts in `ksf_stockmarket/` were written for `mysql.connector`
but the codebase standard (and the DAO factory) uses `pymysql`. When porting a script or
writing a new one, use this table to translate patterns.

## API translation table

| mysql.connector pattern | pymysql equivalent | Notes |
|--------------------------|--------------------|-------|
| `import mysql.connector` | `import pymysql` | |
| `from mysql.connector import Error` | `from pymysql import err as pymysql_err` | or just catch `Exception` |
| `mysql.connector.connect(host=..., user=..., password=..., database=...)` | `pymysql.connect(host=..., user=..., password=..., database=..., charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)` | pymysql requires `charset` and `cursorclass` for DictCursor behavior |
| `conn.is_connected()` | `conn.open` | pymysql exposes `.open` as a bool attribute |
| `conn.autocommit = True` | not available — call `conn.commit()` explicitly after each write | pymysql autocommit handling differs; explicit commit is the pattern used by the DAO |
| `conn.cursor(dictionary=True)` | `conn.cursor(cursorclass=pymysql.cursors.DictCursor)` | pass at connect time or per-cursor |
| `cursor.lastrowid` | same | works identically |
| `cursor.fetchone()[0]` | same | works identically on DictCursor (but prefer named access: `row['column']`) |
| `conn.rollback()` | same | works identically |
| `conn.close()` | same | works identically |
| `Error` (caught as `mysql.connector.Error`) | `pymysql.err.MySQLError` or `pymysql.err.OperationalError` etc. | catch `Exception` if the handler is generic |

## Common mistakes when porting

1. **Leaving `DB_CONFIG` dict intact.** A script that reads from `DB_CONFIG = {'host': 'localhost', 'password': 'change_me', ...}` will connect to localhost with a dummy password. Replace with env-var reads matching what `db_connector.py` does: `os.environ.get('DB_HOST', 'localhost')`, etc.

   **Multi-location cleanup:** `DB_CONFIG` references scatter across a file — not just `get_conn()`. Check ALL of:
   - Docstrings referencing `DB_CONFIG` (e.g. "opened using DB_CONFIG")
   - Function bodies: `cfg = db_config or DB_CONFIG`
   - CLI `default=` args: `default=DB_CONFIG['host']`
   - Comments: `# Override DB_CONFIG with CLI args`
   - Any other string mention

   A single `sed` or patch on `get_conn()` is not enough. Count occurrences first: `grep -c "DB_CONFIG" script.py` and eliminate each one. For docstrings/comments, textual replacement is fine. For code references, replace with env-var lookups or inline dicts.

2. **Using `is_connected()` on a pymysql connection.** Raises `AttributeError`. Replace with `conn.open` (a bool) or just wrap the close in `try/except` if the goal is "close if still open". Check ALL occurrences — `grep -c "is_connected()" script.py`. Typically appears in 2-3 places (after fetch, after import, in finally blocks).

3. **Passing `autocommit=False` or `use_unicode=True` to `pymysql.connect()`.** These are not pymysql params — they're silently ignored or raise TypeError. Remove them. pymysql defaults to no autocommit (you must commit), and unicode handling is automatic with `charset='utf8mb4'`.

4. **Catching `MySQLError` without importing from pymysql.** If the script does `from mysql.connector import Error as MySQLError` and then `except MySQLError`, the exception class won't match pymysql errors. Use `pymysql.err.MySQLError` or broad `Exception`. The import alias pattern is `from pymysql import err as pymysql_err` then `except pymysql_err.MySQLError`.

5. **DictCursor row access via index.** With `cursorclass=pymysql.cursors.DictCursor`, rows are dicts. Accessing via `row[0]` works if the query is `SELECT COUNT(*)` (that's a single-key dict), but for multi-column queries use `row['column_name']`. Mixing index and name access is fragile.

## Worked example: data_importer.py full rewrite

`python/data_importer.py` (819 lines) was the most complex port in the codebase. It had **all five** common mistakes simultaneously plus a legacy `write_prices()` that targeted 14 columns that don't exist in the DB. The fix was staged as targeted patches rather than one large `write_file` (which is fragile across turn boundaries with env resets).

### What was broken

| Issue | Location | How found |
|-------|----------|-----------|
| `write_prices()` targets 14 non-existent columns (`day_open`, `day_high`, `day_low`, `day_close`, `previous_close`, `day_change`, `bid`, `ask`, `source`, `updated_at`) | Lines 235-369 | `grep -c "day_open\|day_high\|..."` = 24 refs |
| Bare `MySQLError` (should be `pymysql_err.MySQLError`) | Lines 348, 493 | `grep -n "except MySQLError"` |
| `conn.is_connected()` (should be `conn.open` / `_db_open()`) | Lines 502, 649, 837 | `grep -n "is_connected()"` |
| `DB_CONFIG` references (8 locations: docstrings, code, CLI defaults, comments) | Lines 335, 610, 612, 790, 867-876 | `grep -n "DB_CONFIG"` |
| Missing `logger` definition | Top of file | LSP "logger is not defined" diagnostics |
| `write_prices()` raw SQL instead of DAO | Lines 235-369 | Read function body |

### Fix sequence (targeted patches, not one big write)

1. **Rewrite `write_prices()`** — replace the entire function body (old SQL → DAO). One patch covering the full function from `def write_prices(` through `return inserted`. The replacement builds `PriceRow` objects and calls `create_central_stockprice_dao(central_db=conn).write_prices(rows)`.

2. **Remove old SQL tail** — the previous patch left a garbled `return affected, %s, %s, ...` followed by the old SQL body. Second patch removes the tail from the garbled return through the end of the old function body.

3. **Fix `MySQLError`** — `replace_all=true` patch: `except MySQLError` → `except pymysql_err.MySQLError`.

4. **Fix `is_connected()`** — `replace_all=true` patch: `conn.is_connected()` → `_db_open(conn)` (3 locations). Then fix the `finally` block which got a bad `close_after` reference from the patch — change `if close_after and _db_open(conn)` → `if _db_open(conn)`.

5. **Fix `DB_CONFIG`** — 4 targeted patches:
   - Docstring: "opened using DB_CONFIG" → "opened using environment variables"
   - Docstring: "override DB_CONFIG" → "override connection params (defaults to env vars)"
   - Code: `cfg = db_config or DB_CONFIG` → inline env-var dict
   - Comment: "# Override DB_CONFIG with CLI args" → "# Override with CLI args (CLI args take priority over env vars)"
   - CLI defaults: `default=DB_CONFIG['host']` etc. → `default=os.environ.get('DB_HOST', 'ksfraser.ca')` etc.

6. **Add `logger` definition** — insert `logger = logging.getLogger(__name__)` after `TSX_PATTERN` definition.

### Verification

```bash
cd /home/ksf_stockmarket/ksf_stockmarket
python3 -m py_compile python/data_importer.py && echo "COMPILES OK"
# Confirm all legacy patterns are gone:
grep -c "day_open\|day_high\|day_low\|day_close\|previous_close\|day_change\|bid.*ask\|source.*updated_at" python/data_importer.py  # should be 0 (or only CSV_COLUMN_MAP references)
grep -c "except MySQLError" python/data_importer.py                    # should be 0
grep -c "is_connected()" python/data_importer.py                       # should be 0
grep -c "DB_CONFIG" python/data_importer.py                            # should be 0
grep -c "create_central_stockprice_dao\|dao.write_prices\|PriceRow" python/data_importer.py  # should be >0
grep -c "^logger = " python/data_importer.py                           # should be 1
grep -c "pymysql_err.MySQLError" python/data_importer.py              # should be 1
```

Note: 6 remaining references to `previous_close`/`day_change` are in `CSV_COLUMN_MAP` for reading external CSV files that may contain those columns as **input data** — they are not written to the DB. This is legitimate. The legacy SQL that targeted them as DB columns is gone.

### Lesson: patch in sections, not one big write

The `data_importer.py` fix was attempted as a single `write_file` of the full 819-line file but got truncated by turn timeout + env reset. Subsequent attempts used targeted `patch` operations on specific function bodies and line ranges. This is more resilient because:

- Each patch is small enough to complete in one turn
- A failed patch leaves the file in a known state (the old content is still there)
- You can `grep` for specific patterns to verify each fix landed before moving to the next
- If a turn gets interrupted, you re-read the file and pick up from the last verified state

For files under ~200 lines, a single `write_file` is fine. For 500+ line files with multiple scattered fixes, use targeted patches and verify between each.
