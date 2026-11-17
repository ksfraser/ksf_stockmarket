---
name: ksf-stockmarket-data-access
description: Patterns for the ksf_stockmarket database layer — StockPricesDAO, exchange routing, schema-aware DTO defaults, script wiring, and migration monitoring.
---

# ksf-stockmarket-data-access

Patterns for working with the ksf_stockmarket database layer: `StockPricesDAO` design, exchange routing, schema-aware DTO defaults, script wiring, and migration monitoring.

## When to use

- Building or modifying the `StockPricesDAO` / exchange routing layer (`python/src/db/`)
- Wiring existing Python scripts through the central DAO instead of raw SQL
- Handling schema constraints (NOT NULL, defaults) in DAO DTOs
- Managing the indicators migration (`migrate_indicators_json_to_columnar.py`) and its watchdog cron
- Recovering from log bloat in `/tmp` caused by the migration logger
- **Verifying ticker→company identity before writing stock analysis** (see `references/ticker-identity-verification.md`)

## StockIdentity verification — mandatory checkpoint before any stock analysis

**Do not write any analysis of a stock (fundamentals, competitor comparison, sell/hold verdict, sector outlook) without first verifying the ticker→company identity from an authoritative source.**

A 2026-09-18 ATR sweep analysis produced **six wrong identities in 14 stocks** (43% error rate) because each was assumed from the ticker, searched for the wrong company name, and written up for whatever came back. See `references/ticker-identity-verification.md` for the full post-mortem, the corrected workflow, and the price-sanity-check heuristic that catches most errors.

**The minimal pre-analysis checklist:**
1. Pull DB price data (last 10-15 rows) for the symbol — gives you a price level to sanity-check
2. Confirm identity from the company's own IR page, TMX Money, or stockanalysis.com
3. Check the price against what you'd expect for the company type you assumed
4. Search for `ticker + "TSX"` (not `ticker GuessedCompanyName`)
5. Verify the business description matches what the price/volume suggests

**Critical rule:** never search for `"TICKER WrongCompanyName"` and trust the results. If your company guess is wrong, you get articles about the wrong company, and you write the analysis for the wrong company. The six errors in that session came from this exact pattern for every one of them.

## StockPricesDAO — the standard write path

All writes to `ksfraser_stock_market.stockprices` go through `CentralStockPricesDAO` in `python/src/db/stockprice_dao.py`. No script should issue raw `INSERT INTO stockprices` against the central DB.

### Factory pattern

```python
from db.stockprice_dao import create_central_stockprice_dao, PriceRow
from datetime import date
from decimal import Decimal

# From env vars (standard — reads DB_HOST, DB_USER, DB_PASS, DB_NAME)
dao = create_central_stockprice_dao()

# Reusing an existing pymysql connection
dao = create_central_stockprice_dao(central_db=existing_conn)

# Write one or many rows
row = PriceRow(
    symbol='RY.TO',
    price_date=date(2026, 9, 15),
    open=Decimal('95.00'),
    high=Decimal('96.50'),
    low=Decimal('94.25'),
    close=Decimal('95.75'),
    volume=1_200_000,
    adj_close=Decimal('95.75'),
    currency='CAD',
    dividend=None,
    split_ratio=Decimal('1'),
)
affected = dao.write_prices([row])  # INSERT ... ON DUPLICATE KEY UPDATE
```

### What the DAO handles

- **Central write (mandatory):** `INSERT ... ON DUPLICATE KEY UPDATE` against `ksfraser_stock_market.stockprices`
- **Optional dual-write:** each row also written to `ksfraser_sm_<exchange>.stockprices` if `_write_to_exchange=True`
- **Exchange resolution:** looks up `symbol_master.exchange` per symbol (cached per session), falls back to a default (e.g. `tsx`)
- **Type safety:** all monetary values are `Decimal` matching `DECIMAL(12,4)` schema columns

## PriceRow — schema-aware DTO defaults

The `PriceRow` dataclass fields MUST match the actual DB schema. Before finalizing defaults, check the table:

```bash
DB_PASS="..." python3 -c "
import pymysql
conn = pymysql.connect(host='ksfraser.ca', port=3306,
    user='ksfraser_stockmarket', password='...',
    database='ksfraser_stock_market',
    cursorclass=pymysql.cursors.DictCursor, connect_timeout=10)
cur = conn.cursor()
cur.execute('DESCRIBE stockprices')
for r in cur.fetchall():
    print(f\"{r['Field']:20s} | {r['Type']:30s} | Null={r['Null']:4s} | Default={r['Default']}\")
conn.close()
"
```

**Critical rule:** if a column is `NOT NULL` with a `DEFAULT`, the DTO field must default to that DB default value — never `None`. Passing `None` for a `NOT NULL` column causes `IntegrityError (1048)`.

Example from this codebase — `stockprices.currency` is `varchar(3) NOT NULL DEFAULT=CAD`, so `PriceRow.currency` defaults to `'CAD'`, not `None`.

### DTO field list (matching `ksfraser_stock_market.stockprices`)

Always verify defaults against `DESCRIBE stockprices` before finalizing — the rule is: if a column is `NOT NULL` with a `DEFAULT`, the DTO field must default to that DB default value, never `None`.

| Field | Type | Nullable | DB Default | DTO Default |
|-------|------|----------|------------|-------------|
| symbol | str | NO | — | (required, no default) |
| price_date | date | NO | — | (required, no default) |
| open | Decimal | YES | — | `None` |
| high | Decimal | YES | — | `None` |
| low | Decimal | YES | — | `None` |
| close | Decimal | NO | — | (required) |
| volume | int | YES | — | `None` |
| adj_close | Decimal | YES | — | `None` |
| currency | varchar(3) | NO | `CAD` | `'CAD'` (matches DB default) |
| dividend | Decimal(10,6) | YES | `0.000000` | `None` |
| split_ratio | Decimal(8,4) | YES | `1.0000` | `None` |

**Why `currency` defaults to `'CAD'` in the DTO:** `stockprices.currency` is `NOT NULL DEFAULT=CAD`. If the DTO field defaults to `None` and the upsert SQL includes `currency` in the column list with `None` as the value, MySQL raises `IntegrityError (1048): Column 'currency' cannot be null`. The working approaches are:

- **(current — explicit):** DTO default is `'CAD'`, upsert SQL includes `currency = %s` with the CAD value. Works, explicit, matches DB default.
- **(alternative — let DB handle it):** DTO default stays `None`, but the upsert SQL builder excludes `currency` from both the INSERT column list and the ON DUPLICATE KEY UPDATE clause entirely. MySQL then applies `DEFAULT=CAD` on INSERT and leaves the existing value on UPDATE. Cleaner if currency is a pure schema property, but requires the SQL builder to be column-aware.

Pick one approach and be consistent across the DAO and all callers (e.g. `tv_screener.py` builds `PriceRow(..., currency='CAD', ...)`). Mixing approaches — some callers passing `None` and the SQL including `currency` — causes the 1048 error.

## Exchange routing

Exchange routing normalizes exchange names and maps them to per-exchange database names. The pattern lives in `python/src/db/exchange_routing.py`.

### Normalization

`normalise_exchange()` replaces `.` with `_` — the same logic as the stored procs:

| Raw exchange | Normalized |
|-------------|------------|
| `tsx` | `tsx` |
| `tsx.v` | `tsx_v` |
| `nyse` | `nyse` |

### Database name

`exchange_db_name(normalized_exchange)` → `ksfraser_sm_<normalized>` (e.g. `ksfraser_sm_tsx_v`, `ksfraser_sm_tsx`).

### Symbol → exchange lookup

`resolve_exchange_for_symbol(symbol, conn, default_exchange)` queries `symbol_master.exchange` for the symbol, normalizes the result, and caches it per session. Falls back to `default_exchange` (default `tsx`) on lookup failure.

### Multi-host stub

`get_exchange_connection(symbol)` connects to `ksfraser.ca` with the resolved exchange DB name. The `except` block is a documented stub where per-host lookup (table/JSON/env-based) can be inserted later when tables spread across hosts — the seam is already there, just not populated.

### Credential sharing

Exchange connections read the same env vars as the central connector (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`) — no hardcoded passwords, no import coupling between files in different directories.

- **`pymysql` vs `mysql.connector` carryover:** if a script was written for `mysql.connector` (old `DB_CONFIG` dict, `is_connected()`, `autocommit` kwarg, `MySQLError` from wrong package), see [mysql-to-pymysql-migration.md](references/mysql-to-pymysql-migration.md) for the translation table and common mistakes.
- **Large-file patch strategy:** for scripts 500+ lines with multiple scattered fixes, use targeted `patch` operations verified with `grep -c` between each — not one big `write_file` which can be truncated by turn timeouts and env resets. See [large-file-patch-strategy.md](references/large-file-patch-strategy.md).

## Wiring an existing script through the DAO

When a script writes to `stockprices`:

1. **Import the DAO:** add `from db.stockprice_dao import PriceRow, create_central_stockprice_dao` (with `# noqa: E402` if PEP 8 complains about late import)
2. **Fix the import path:** ensure `python/src/` is on `sys.path` before the DAO import — typically `sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'python' / 'src'))`
3. **Build PriceRow objects** from the script's data structures
4. **Call `dao.write_prices(rows)`** instead of raw `cursor.executemany(insert_sql, batch)`
5. **Fix credentials:** remove any hardcoded `DB_CONFIG` dict with `change_me` or wrong host — use env vars or pass an existing connection to the factory

### When a script uses mysql.connector (not the DAO)

Scripts that open their own pymysql connections (not through the DAO factory) often have legacy patterns that need cleaning:

- **`mysql.connector` → `pymysql`:** the codebase standard is `pymysql`. Replace `import mysql.connector` and `mysql.connector.connect()` with `import pymysql` and `pymysql.connect()`.
- **`DB_CONFIG` dict → env vars:** remove any hardcoded `DB_CONFIG = {'host': 'localhost', 'password': 'change_me', ...}` dict. Replace with env-var lookup: `os.environ.get('DB_HOST', 'localhost')`, `os.environ.get('DB_USER', 'ksf_stockmarket')`, `os.environ.get('DB_PASS', '')`, `os.environ.get('DB_NAME', 'ksfraser_stock_market')`. The DAO factory already does this — non-DAO scripts must follow the same pattern.
- **`conn.is_connected()` → `conn.open`:** pymysql connections expose `.open` (a bool), not `.is_connected()`. The latter is `mysql.connector` API. Using `.is_connected()` on a pymysql connection raises `AttributeError`.
- **`autocommit` / `use_unicode` kwargs:** pymysql doesn't accept these — use `charset='utf8mb4'` and call `conn.commit()` explicitly. `autocommit` is not a pymysql connect param.
- **`MySQLError` → `pymysql.err.MySQLError`:** if the script catches `MySQLError` from `mysql.connector`, switch to `pymysql.err.MySQLError` (or just catch `Exception` if the error handling is generic).

### When a script has a schema mismatch

If the script's INSERT targets columns that don't exist in the real DB (e.g. `day_open`, `previous_close`, `day_change`, `bid`, `ask`, `source`, `updated_at`), the script's schema must be updated to match the DAO's expected columns before it can use the DAO. Don't force-fit the DAO to a legacy schema — fix the schema.

### Scripts wired in this session

| Script | Change |
|--------|--------|
| `python/fetch_prices.py` | Fully rewritten: DAO write path, env-based creds via `_build_mysql_config()`, `PriceRow` objects from DataFrame |
| `python/import_historical_prices.py` | Rewritten: removed hardcoded `DB_CFG` with `change_me`, DAO factory from env, `PriceRow` from CSV parse |
| `python/ingest_screener_symbols.py` | Import path fixed to make `python/src/` importable; `PriceRow`/`create_central_stockprice_dao` imported |
| `tv_screener.py` | `update_bond_average_from_db()`: raw `cur.execute(INSERT...)` → DAO write; `currency=None` → `currency='CAD'` |
| `python/data_importer.py` | Schema updated to match DAO columns, hardcoded `DB_CONFIG` replaced with env-based `get_conn()`, `mysql.connector` → `pymysql`, `write_prices()` now builds `PriceRow` and calls DAO |

## Stock analysis from DB signals — data-quality first (NEW)

- **Data quality first for signal-based analysis** — before writing any narrative from `analyst_targets` or any signal table, verify against independent data first: target vs real close (the yfinance scraper bug makes `target_price == current_price` in 99.96% of rows), targets plausible across time (ADR/currency confusion shows up as one-day 65% jumps), target vs trend (declining target below close = hidden sell), and existence check (ticker in symbol_master + stockprices + symbol_news). If signals are corrupted, the deliverable is the data-quality report + recommended fixes, not a fabricated narrative. See `references/analyst-signal-data-quality-checklist.md` and `references/sell-side-signal-analysis-2026-09-22.md` for the full worked example (2026-09-22: 257 strong_buy signals across 29 tickers, all contaminated; 5 bugs caught: target==current in 2289/2290 rows, CNR CAD/USD confusion, TFII hidden sell, phantom BLX.TO, 12 hidden sells).

### Source-of-truth authority for identity and signals

- **Company identity:** `symbol_master.name` / `symbol_master.sector` / `symbol_master.industry`
  is the DB authority. Never search the web for `ticker + guessed company name` and trust
  the results — if the guess is wrong you write the analysis for the wrong company.
  See `references/ticker-identity-verification.md`.
- **Signal data quality:** `analyst_targets`, `evalsummary`, and any signal table must be
  treated as **suspect until verified**, not as ground truth. The yfinance scraper that
  populates `analyst_targets` has a documented bug where `target_price == current_price`
  for every row (2,054 rows, all 0% upside) and recommendation labels are threshold-computed
  synthetic labels, not real analyst calls. See `references/analyst-signal-data-quality-checklist.md`.

## Migration monitoring

The indicators migration (`migrate_indicators_json_to_columnar.py`) is watched by cron job `59fc71e44a68` (`indicators-migration-monitor`), scheduled every 15 minutes. It:

1. Checks if the process is alive via `pgrep -f "migrate_indicators_json_to_columnar.py"`
2. If alive — does nothing, exits 0
3. If dead — restarts the migration (only if `indicators_json` still has rows)
4. Self-removes when `indicators_json` reaches 0

**This cron must stay active** until migration is confirmed complete (0 rows in `indicators_json`).

### Checking migration progress

```bash
DB_PASS="..." python3 -c "
import pymysql
conn = pymysql.connect(host='ksfraser.ca', port=3306,
    user='ksfraser_stockmarket', password='...',
    database='ksfraser_stock_market',
    cursorclass=pymysql.cursors.DictCursor, connect_timeout=10)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) AS cnt FROM indicators_json')
print(f'indicators_json: {cur.fetchone()[\"cnt\"]:,} remaining')
cur.execute('SELECT COUNT(*) AS cnt FROM indicators')
print(f'indicators: {cur.fetchone()[\"cnt\"]:,} rows')
conn.close()
"
```

## Log bloat recovery

When `/tmp/migrate_indicators.log` grows to multiple GB (the migration script logs every row processed), recover with a surgical trim that only touches that file:

```bash
# Trim to last N lines (preserves recent context, frees space)
tail -n 5000 /tmp/migrate_indicators.log > /tmp/migrate_indicators.log.tmp
mv /tmp/migrate_indicators.log.tmp /tmp/migrate_indicators.log
```

This is surgical — only `migrate_indicators.log` is touched. Other `/tmp` usage (editor caches, other logs, temp files) is left intact. Do NOT `rm -rf /tmp/*` or similar broad cleanup.

**Prevention:** the migration script logs every indicator field for every row. For long-running migrations, consider adding an errors-only mode or periodic-summary logging so the log doesn't grow unbounded. This session trimmed the log but the root cause (verbose per-row logging) remains in the script.

## Integration testing a DAO

The standard pattern for verifying DAO write + read end-to-end:

```python
dao = create_central_stockprice_dao()
test_row = PriceRow(symbol='DAO_TEST', price_date=date(2026, 9, 15),
                    open=Decimal('100'), close=Decimal('100.75'),
                    volume=500000, currency='CAD', split_ratio=Decimal('1'))
affected = dao.write_prices([test_row])
assert affected >= 1

# Read back
rows = dao.read_prices('DAO_TEST', use_central=True)
assert len(rows) == 1
r = rows[0]
assert r['close'] == Decimal('100.75')

# Cleanup — delete the test row
with dao._central_db.cursor() as cur:
    cur.execute("DELETE FROM stockprices WHERE symbol=%s", ('DAO_TEST',))
dao._central_db.commit()
dao._central_db.close()
```

Always clean up test rows after verification — the `stockprices` table is large and test data accumulates.

## Per-Entity Price Storage Refactor (absorbed from `per-entity-price-storage`)

When the DB is under a size constraint and the dominant table is a monolithic per-entity price history while real read patterns are mostly per-entity lookups plus a bounded cross-entity working set.

### Routing model (the key decision)

Route by a stable first-class attribute on the entity master table, not by one stored procedure per entity. For the stockmarket case that attribute is `symbol_master.exchange`, and the mapping is:

- One database per exchange (e.g. `ksfraser_sm_tsx`, `_nasdaq`, `_nyse`, `_v`, `_cse`, `_amex`, plus `_other` as fallback for minor/uncommon exchange codes).
- One price-history table per entity inside its exchange DB (`stockprices_<symbol>`), holding unbounded history.
- One recent cross-entity table per exchange DB (`stockprices_recent_<exchange>`), holding the last N days / N trading days per entity for the filter engine, screen runner, MACD, and backtest "current" work.

The mapping is derived at runtime from the master table, not hardcoded. A router helper (`SymbolTableRouter`) takes an entity key and returns the (db, history table, recent table, connection) tuple. No consumer hardcodes a db or table name.

### Schema pattern

**Per-entity history table:**

```sql
CREATE TABLE stockprices_<symbol> (
    price_date     DATE            NOT NULL,
    open           DOUBLE          NULL,
    high           DOUBLE          NULL,
    low            DOUBLE          NULL,
    close          DOUBLE          NULL,
    volume         BIGINT          NULL,
    adj_close      DOUBLE          NULL,
    dividend       DOUBLE          DEFAULT 0,
    split_ratio    DOUBLE          DEFAULT 1,
    split_factor   DOUBLE          DEFAULT 1,
    currency       VARCHAR(3)      NOT NULL DEFAULT 'USD',
    PRIMARY KEY (price_date),
    INDEX idx_close (close)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Recent cross-entity table per exchange:**

```sql
CREATE TABLE stockprices_recent_<exchange> (
    symbol         VARCHAR(20)     NOT NULL,
    price_date     DATE            NOT NULL,
    open           DOUBLE          NULL,
    high           DOUBLE          NULL,
    low            DOUBLE          NULL,
    close          DOUBLE          NULL,
    volume         BIGINT          NULL,
    adj_close      DOUBLE          NULL,
    dividend       DOUBLE          DEFAULT 0,
    split_ratio    DOUBLE          DEFAULT 1,
    PRIMARY KEY (symbol, price_date),
    INDEX idx_date (price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Ingestion (dual-write, single per-entity-DB transaction)

For each new price row: resolve the route, begin a transaction on the exchange DB, insert/replace into `stockprices_<symbol>`, insert/replace into `stockprices_recent_<exchange>`, trim oldest row if retention exceeded, commit. Both writes are in the same DB and same transaction — atomicity is per entity per ingestion cycle. The old monolithic table is dropped only after reads are fully cut over.

### Adjusted-price contract (split-factor tracking)

Add a `split_factor` column per row so adjusted prices are derivable and auditable: `split_factor` on row N = `split_factor` on row N-1 × `split_ratio` on row N (cumulative product). Convention: `adj_close = close / split_factor`. Cache the latest factor on the master row (`symbol_master.split_factor_current`). Nightly ingestion recomputes `adj_close` and `split_factor` for the new row from the prior row's factor and the new row's split_ratio.

### Tiered window cadence

- Short windows (1Q, 4W, 12W, 24W, 52W, YTD): refreshed nightly from the recent table via lightweight rollup.
- Long windows (2Y, 3Y, 5Y, 10Y): recalculated quarterly or after the entity's fundamentals/earnings release, stored in a precomputed window table with `last_recomputed` timestamp.
- Fundamental/score-based tenets: recalculated quarterly or after earnings.

This cuts nightly compute from "every entity every night" to "only entities that had an event or hit a boundary."

### DB size picture to verify before committing

Before writing requirements or migration scripts, get the real numbers: total DB size, size + row count of the monolithic price table, size + row count of everything else combined, size + row count per exchange, and a full `information_schema.tables` size report sorted descending. The obvious suspect (monolithic price table) may have been overtaken by something less visible (e.g. a JSON-blob indicators table). In the stockmarket case the DB grew from ~187 MB to ~11.5 GB between sessions and the dominant table shifted from `stockprices` (was 93%) to `indicators_json` (71% at time of review), so a stockprices-only refactor addresses only ~17% of the current size. A size-constrained refactor that starts from a stale "stockprices is 93% of the DB" premise will spend its whole budget on the 17% and miss the 71%.

### Documentation alignment pattern

When documenting a new capability, keep three artifacts in sync: requirements pack (BR + FR + UC), architecture note section, and traceability matrix rows. Write them together, not sequentially days apart.

### Intraday SQLite sync (absorbed from `price-sync-intraday`)

Intraday price sync via `sync_stock_prices.py --sqlite` writes daily OHLCV bars from yfinance into a local SQLite `price_intraday` table. This is an ephemeral cache — **no MariaDB writes occur** in this mode. The real SQLite target is `config.paths.ANALYTICS_DB` = `/root/.hermes/cache/analysis_results.db` — NOT a file in the workspace directory (which has a zero-byte decoy). The `--sqlite` flag guarantees the MariaDB branch is never taken. The storage-tier rule ("sub-day / intraday data → SQLite, never MySQL; daily + calculated → MySQL unless same-day-only") is now a canonical AGENTS.md rule across the stockmarket project.

**Reference files:** `references/stockmarket-case-2026-09-09.md`, `references/exchange-routing-dao-implementation.md`, `references/2026-09-11-intraday-sqlite-sync.md`.

### Key pitfalls

- **Hardcoded credentials in scripts:** `data_importer.py` had `password: 'change_me'`, `host: 'localhost'` — these must be replaced with env-based lookup before the script can connect to production. The DAO factory reads env vars; scripts that bypass the DAO must do the same.
- **Schema mismatch between script and DAO:** a script's INSERT column list must match the DAO's `PriceRow` fields and the actual DB schema. Legacy columns like `day_open`/`previous_close`/`bid`/`ask` don't exist in `ksfraser_stock_market.stockprices` — the script must be updated, not the DAO. **Real example (2026-09):** `data_importer.py`'s `write_prices()` targeted 14 non-existent columns: `day_open`, `day_high`, `day_low`, `day_close`, `previous_close`, `day_change`, `bid`, `ask`, `source`, `updated_at`. Detection: `grep -c` each legacy column name — 24 references found across the function body. Fix: rewrite the function to build `PriceRow` objects and call `dao.write_prices()`. Note: `CSV_COLUMN_MAP` may still reference `previous_close`/`day_change` for reading external CSV input — that's legitimate, the legacy SQL that wrote them to the DB is what must go.
- **NOT NULL without default in DTO:** `PriceRow.currency = None` when the DB column is `NOT NULL DEFAULT=CAD` → `IntegrityError`. Always check `DESCRIBE` output before setting DTO defaults.
- **Exchange routing for reads vs writes:** after the stockprices split, prices for a symbol live in `ksfraser_sm_<exchange>.stockprices`. Reads that need the latest price for a symbol should either read from central (still has all data pre-migration) or use exchange routing to find the right DB. The DAO's `read_prices()` supports both via `use_central=True/False`.
- **`conn.commit()` is mandatory in pymysql:** DML (INSERT/UPDATE/DELETE) rolls back on connection close if not committed. The DAO calls `commit()` internally after writes. Scripts that open their own connections and do raw SQL must commit explicitly.
- **One big `write_file` of large scripts is fragile:** `write_file` of 800+ line files can be truncated by turn timeout + environment reset, leaving a file that compiles (valid syntax) but has semantic bugs (half old code, half new). For 500+ line files with scattered fixes, use targeted `patch` operations with `grep -c` verification between each. See [large-file-patch-strategy.md](references/large-file-patch-strategy.md).
- **Non-ASCII characters block git commit in this repo:** any `.md` or `.py` file containing non-ASCII chars (em dashes `—`, arrows `→`, section signs `§`, box-drawing `│├└┌┘`, `≥`, `≤`, `✓`, `✗`, `×`, `·`, `▼`, `◄`) will cause `git commit` to fail or silently drop files. Always normalize before committing: run the script in [non-ascii-git-commit-pitfall.md](references/non-ascii-git-commit-pitfall.md), or detect with `grep -Pn '[^\x00-\x7F]' docs/`. This also covers the `patch` gotcha — when `patch` reports "Found N matches" for N > 1, the context isn't unique; read the full file and use `write_file` instead. See [non-ascii-git-commit-pitfall.md](references/non-ascii-git-commit-pitfall.md).
- **Wrong ticker→company identity before analysis:** searching for `"TICKER GuessedCompanyName"` and trusting results produces analysis of the wrong company. Six errors in one 2026-09-18 session (RUS≠Royal Bank, MX≠Maxar, SRV.UN≠Northland, PZA≠generic REIT, MTY≠Magna, WJX≠Waste Connections). Always verify identity from the company's own IR page or TMX/stockanalysis.com before writing. See [ticker-identity-verification.md](references/ticker-identity-verification.md).

## Stockmarket Nightly Pipeline (absorbed from `stockmarket-nightly-pipeline`)

The nightly pipeline for `/var/www/stockmarket-app` has three stages: scrape, detect, dispatch. This section covers the operational workflow that consumes the data-access layer documented above.

### Stage 1: Zacks Scrape

```bash
cd /var/www/stockmarket-app
set -a && . .env && set +a
python3 python/zacks_scraper.py --all
```

**Critical: scraper times out at 300s** — `--all` processes 3636 symbols at ~6s each = ~6 hours. Do NOT run `--all` as a foreground command with a 300s timeout. Use chunked batches (200-300 symbols per invocation) or background with `notify_on_complete=true`.

**Where data lands:** `fundamentals` (Zacks metrics), `zacks_ratios_history` (ratio trends), `zacks_broker_recommendations` (firm grades). There is NO `zacks_data` table.

**Signal coverage reality:** Only 3 symbols (RY, CM, RGLD) ever produce non-zero 4-week F1 EPS revisions. All other 3633 symbols return 404/empty/parse-failure pages. A typical nightly run surfaces 1-2 bullish (RY, CM) and 1 bearish (RGLD) signals — from the latest available scrape date, not tonight's.

### Stage 2: Signal Detection

Query the **latest non-zero** 4-week F1 EPS revision per symbol from the past several days — not just today's scrape, since the estimates page is often empty:

```sql
SELECT f.symbol, f.zacks_eps_change_f1_4w, f.forward_eps, f.fetch_date
FROM fundamentals f
INNER JOIN (
    SELECT symbol, MAX(fetch_date) as max_date
    FROM fundamentals
    WHERE zacks_eps_change_f1_4w IS NOT NULL AND zacks_eps_change_f1_4w != 0
    GROUP BY symbol
) latest ON f.symbol = latest.symbol AND f.fetch_date = latest.max_date
WHERE f.zacks_eps_change_f1_4w IS NOT NULL AND f.zacks_eps_change_f1_4w != 0
```

Split in app code: bullish (>0, DESC, top 5), bearish (<0, ASC, top 5). If fewer than 5 for either direction, send what you have.

### Stage 3: Discord Dispatch + Alert Queue

**Use curl, NOT Python urllib** — urllib returns HTTP 403; curl returns 204. See `references/discord-webhook-fallback.md`.

**alert_queue has a manual varchar(64) PK** — generate IDs with `uuid.uuid4().hex[:8]`:
```python
alert_id = f"zacks_eps_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
```

**Webhook URL:** read from `system_settings` where `setting_key = 'discord_alert_webhook'`. Target channel ID: `1516481638924812489`.

**Message templates:**
- Bullish: `📈 [SYMBOL] Zacks EPS revision alert: 4-week F1 EPS change = +[VALUE]...`
- Bearish: `📉 [SYMBOL] Zacks EPS revision alert: 4-week F1 EPS change = [VALUE]...`
- No signals: `📊 Zacks EPS watch: No significant 4-week F1 revisions...`

**Discord webhook ≠ bot API** — webhook = HTTP POST to `discord.com/api/webhooks/WEBHOOK_ID/TOKEN`; bot API = `discord.com/api/v10/channels/CHANNEL_ID/messages` with bot token. Mixing them up → 401.

See `references/2026-09-23-zacks-scrape.md`, `references/discord-webhook-fallback.md`, `references/sqlite-alert-consumer-protocol.md`.
