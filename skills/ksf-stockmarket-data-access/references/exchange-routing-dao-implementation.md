# Exchange-routing DAO implementation — stockmarket app, 2026-09-11

Concrete implementation of the per-exchange storage routing model described in
this skill's SKILL.md. Captures the module structure, the DAO pattern, the
dual-write decision, the storage-tier rules, and the AGENTS.md DB rules
established in this session, so a future session does not re-derive them.

## What was built

### Exchange routing module — `python/src/db/exchange_routing.py`

The single place where exchange names become database names and where exchange
connections are opened. All consumers go through this module; no script
hardcodes `ksfraser_sm_<exchange>` or opens its own exchange connection.

Functions:

- **`normalise_exchange(raw: str) -> str`** — DB-safe exchange suffix.
  Mirrors the stored-proc logic: `REPLACE(exchange, '.', '_')`, plus a broader
  sanitisation that collapses any non-identifier characters to underscores.
  `TSX.V -> tsx_v`. Case-insensitive, whitespace-trimmed, double-periods
  collapse (`TSX..V -> tsx_v`). Raises on empty/whitespace-only input.

- **`exchange_db_name(exchange_raw: str) -> str`** — formulaic routing:
  `f"ksfraser_sm_{normalise_exchange(exchange_raw)}"`. Examples:
  `TSX.V -> ksfraser_sm_tsx_v`, `TSX -> ksfraser_sm_tsx`,
  `NYSE -> ksfraser_sm_nyse`.

- **`resolve_exchange_for_symbol(symbol, conn=, default_exchange="tsx") -> str`**
  — looks up `symbol_master.exchange` for the symbol, caches per session,
  falls back to *default_exchange* when the symbol isn't in `symbol_master` or
  has no exchange. Non-fatal on lookup failure (logs warning, uses default) —
  the caller still writes to the central DB; only the optional exchange-db
  write may route to the wrong exchange DB in that case.

- **`resolve_exchange_db_name_for_symbol(symbol, ...) -> str`** — convenience
  wrapper that returns the DB name without opening a connection.

- **`get_exchange_connection(symbol, conn=, default_exchange="tsx",
  database=) -> Connection`** — opens a live pymysql connection to the exchange
  DB for *symbol*. Today: `host=ksfraser.ca`, `port=3306` (from `DB_PORT`),
  `user=ksfraser_stockmarket` (from `DB_USER`), `password=DB_PASS` (from
  `DB_PASS`), `database=ksfraser_sm_<normalised>`. If *database* is passed
  explicitly it is used as-is (useful for testing or when the caller already
  resolved the name).

#### Credential sharing (important architectural detail)

The module reads `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS` from the
environment — the same env vars `python/db_connector.get_connection()` (the
common connector) reads. It does **not** `import db_connector`, because
`db_connector` lives at `python/db_connector.py` (repo root) while this module
lives at `python/src/db/exchange_routing.py` and the two are not on the same
import path. The credential source of truth is the environment, which is
shared — that is what "use the common connector" means here: one source of
truth for credentials, no hardcoded passwords, and if `db_connector` ever
changes how it sources credentials, `_default_host()/_default_user()/
_default_password()` are updated to match in one place.

This is a deliberate alternative to importing the common connector: same
credential source, no import-path coupling.

#### Multi-host / per-exchange host-user-db stub

`get_exchange_connection` has a documented `except` block (marked
`# -- multi_host_stub --`) that catches connection failures and logs where a
future lookup would go. It does **not** try any lookup today. The intended
sources, documented in the stub for when we activate one:

- **(a) DB table `ksf_exchange_routing`** — `exchange_raw, host, user,
  password, database, active`. Looked up once per exchange, cached. Lives on
  the central DB so every writer sees the same mapping. Password stored
  encrypted at rest or via Ansible Vault at deploy time.
- **(b) JSON file `config/exchange_routing.json`** — loaded at startup, re-read
  on SIGHUP or file-watch polling. Good when routing lives with app config
  rather than the DB.
- **(c) Environment variables** — `DB_HOST_<EXCHANGE>`, `DB_USER_<EXCHANGE>`,
  `DB_NAME_<EXCHANGE>` where `<EXCHANGE>` is the normalised name uppercased.
  Simple but noisy; good for a small number of split exchanges.

When we activate one, replace the stub contents with the lookup + retry and
remove the stub comment. Today: log and re-raise so the caller (repository)
can decide whether to skip the exchange-db write and rely on the nightly
migrate proc.

### StockPrices DAO — `python/src/db/stockprice_repository.py` (pattern)

Abstract interface + MySQL implementation that writes to the central
`ksfraser_stock_market.stockprices` and optionally also to the exchange DB.

- **`StockPricesDAO` (abstract)** — interface with `upsert_prices(prices,
  *, conn=None) -> int` (and any read methods needed). All price writes go
  through this, not raw `INSERT INTO stockprices` scattered across scripts.
- **`CentralStockPricesDAO`** — writes to `ksfraser_stock_market.stockprices`
  (mandatory). Uses the common connector for credentials.
- **`ExchangeStockPricesDAO`** — thin wrapper that delegates to the routing
  layer to find the exchange DB, then upserts into
  `ksfraser_sm_<exchange>.stockprices`. Uses `get_exchange_connection()` from
  the routing module.
- **`DualStockPricesDAO`** — composes central + exchange, writes to both.
  Controlled by a `write_to_exchange: bool` flag, **default off**. When off,
  the repository writes only to the central DB and relies on the nightly
  `migrate_stockprices` stored proc to sync new rows to the exchange DBs.

The dual-write flag is the seam for the decision Kevin made mid-session:
default to central-only (let the nightly proc sync), with an explicit switch
to turn dual-write back on if wanted. The stored procs (`migrate_stockprices`,
`cleanup_delete_stockprice`, `cleanup_count_stockprice`) remain the backstop
and monthly cleanup regardless.

### Storage-tier rules (established this session)

Documented in `AGENTS.md` at the repo root and in the architecture docs:

- **Sub-day / intraday data → SQLite** (`price_intraday`), never MySQL. The
  `/15` intraday cron (`ae8aabf91e15`) passes `--sqlite` so
  `sync_stock_prices.py` writes to SQLite `price_intraday` (ephemeral cache at
  `ANALYTICS_DB`), not MariaDB. Omitting `--sqlite` writes to MariaDB
  `stockprices` via `MariaDBStockPriceRepository` — a materially different
  target.
- **Daily OHLCV + fundamentals + calculated values → MySQL**, unless the value
  is only valid for the day (e.g. an intraday signal that resets). Calculated
  values go into MySQL unless they are same-day-only.
- **All MySQL writes go through a StockPricesDAO / repository** — no raw SQL in
  business scripts. The existing raw-SQL writers (`data_importer.py`,
  `import_historical_prices.py`, `sync_stock_prices.py`, etc.) are migrated to
  route through the DAO.

### AGENTS.md DB rules (canonical, repo-level)

Added to the repo's `AGENTS.md` so every agent session picks them up:

- All DB access goes through the common connector + repositories/DAOs. No raw
  SQL in business logic.
- Sub-day data → SQLite. Daily + calculated values → MySQL unless only valid
  for the day.
- Credentials from the common connector (env vars), never hardcoded.
- The exchange routing module is the only place exchange DB names are composed.
- The `ksfraser_` prefix is retained even if we move back to self-hosting, to
  keep the move impact minimal.

## Dual-write decision (recorded for the record)

Session decision (Kevin, mid-session): the repository writing price inserts
does **not** write to the exchange versions by default. It writes to the
central `ksfraser_stock_market.stockprices` (mandatory). The nightly
`migrate_stockprices` stored proc copies new rows from central into the
appropriate `ksfraser_sm_<exchange>.stockprices` (run nightly). The
`cleanup_delete_stockprice` proc deletes symbols from central whose
symbol/date is also in the appropriate exchange DB (run monthly). The
`cleanup_count_stockprice` proc is a non-destructive count variant of delete
(used to test queries before running delete).

Rationale: we can't write to the exchange versions directly during migration
(because the migrate proc is the mechanism that copies central → exchange), so
central-only + nightly proc sync is the primary path. Dual-write is available
as an option (`write_to_exchange=True`) but is off by default.

If we later want to flip to dual-write, the `DualStockPricesDAO` seam makes it
a one-flag change, not a rewrite.

## Schema verification (live, 2026-09-11)

All exchange DBs that exist use the same `stockprices` schema as the central
table — same columns, types, indexes, yearly partitioning. Verified live
against `ksfraser_sm_tsx_v`, `ksfraser_sm_tsx`, `ksfraser_sm_nyse` (and
`ksfraser_sm_amex` had a `SHOW CREATE TABLE` permission error but is
treated as matching). The DAO can target any of them interchangeably because
the schema is identical; the only variable is the database name.

Note: `ksfraser_sm_amex` returned `(1142, "SHOW command denied to user
'ksfraser_stockmarket'@...' for table `ksfraser_sm_amex`.`stockprices`")` on
`SHOW CREATE TABLE` — a permission restriction on that command, not a schema
mismatch. The DAO connect path still works against it (the user can connect to
the DB), so treat amex as matching unless a real schema divergence is found.

## Existing exchange DBs (live, 2026-09-11)

Confirmed to exist on `ksfraser.ca` / `ksfraser_stockmarket`:

- `ksfraser_sm_tsx_v` — ✅ exists, schema matches
- `ksfraser_sm_tsx` — ✅ exists, schema matches
- `ksfraser_sm_nyse` — ✅ exists, schema matches
- `ksfraser_sm_amex` — ✅ exists (connect works; `SHOW CREATE TABLE` denied)

Others (e.g. `ksfraser_sm_nasdaq`, `ksfraser_sm_v`, `ksfraser_sm_cse`) may or
may not exist — verify live before assuming. The routing module does not
assume any specific exchange DB exists; it just constructs the name and lets
the connect fail if the DB is missing (the caller decides whether to skip the
exchange-db write).

## Documentation alignment (this session)

Three artifacts updated in one pass:

1. **Code** — `python/src/db/exchange_routing.py` + `python/src/db/
   stockprice_repository.py` (pattern) + unit tests.
2. **Architecture** — `docs/ARCHITECTURE_PYTHON.md` §11 (storage-tier rules +
   DB access rules) and `docs/ARCHITECTURE.md` (DB adapter layer note).
3. **Requirements** — `docs/requirements/FR-stockprices-exchange-routing.md`
   (functional requirement for the exchange-routed DAO) and the
   `AGENTS.md` DB rules.

The `AGENTS.md` rules are the part most likely to be missed if left as a
separate later task — they are written in the same pass as the code and the
architecture docs.

## Pitfalls captured

- **Import-path coupling trap.** `python/src/db/exchange_routing.py` cannot
  `import db_connector` because they're on different import paths
  (`python/src/db/` vs `python/`). Reading the same env vars is the correct
  alternative — same credential source, no coupling. Don't try to force the
  import; it will break the module's importability.
- **Dual-write vs proc-sync confusion.** The migrate proc copies central →
  exchange, so writing to the exchange DB during migration would be redundant
  or conflict with the proc. Central-only + nightly proc is the primary path;
  dual-write is an opt-in seam, not the default.
- **`SHOW CREATE TABLE` permission ≠ schema mismatch.** A permission error on
  `SHOW CREATE TABLE` for a specific exchange DB does not mean the schema
  differs. The connect path is the real test; `SHOW CREATE TABLE` is only a
  verification aid. Don't block on a `SHOW CREATE TABLE` denial.
- **Stored-proc replace logic must stay in sync with code.** The procs do
  `REPLACE(exchange, '.', '_')`; the code's `normalise_exchange` does the same
  (plus broader sanitisation). If the proc logic ever changes, update the code
  to match — they must produce the same DB names.
- **Symbol-master exchange fallback.** `symbol_master.exchange` may be blank
  or missing for some symbols. `resolve_exchange_for_symbol` falls back to a
  default (currently `"tsx"`) so the central write always works; only the
  optional exchange-db write may route to the wrong DB in that case. The
  fallback value is a config point, not a hardcoded assumption.
