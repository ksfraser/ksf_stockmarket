# UC-15: Stock Price Storage Refactor — Migration, Dual-Write, Routing Validation

**BABOK v2.0** | **Category:** Use Case | **Parent:** BR-15 / FR-15
**Module:** Stock Price Storage / Nightly Ingestion
**Author:** KSF | **Status:** Draft | **Date:** 2026-09-09

## UC-15a: Migrate existing price history into per-symbol / per-exchange storage

**Actor:** System administrator / deployment pipeline
**Preconditions:**
- `symbol_master` is populated and current (every active symbol has an `exchange` value).
- The exchange databases (`ksfraser_sm_tsx`, `_nasdaq`, `_nyse`, `_v`, `_cse`, `_amex`) exist or are creatable through the schema manager.
- The old `stockprices` table is still present and readable.
- A fallback database for minor exchanges (`ksfraser_sm_other`) exists.

**Steps:**
1. System reads the distinct set of exchanges from `symbol_master.exchange`.
2. For each exchange with active symbols, system ensures the exchange database exists (`SchemaManager::ensureExchangeDatabase`).
3. For each active symbol, system ensures its per-symbol history table exists (`SchemaManager::ensurePriceHistoryTable`).
4. For each exchange, system ensures the recent table exists (`SchemaManager::ensureRecentTable`).
5. System reads `stockprices` rows grouped by symbol.
6. For each symbol, system writes all historical rows into `stockprices_<symbol>` in the correct exchange database, computing `split_factor` cumulatively from the existing `split_ratio` column as it goes.
7. System writes the most recent N days (1 year / 200 trading days) of rows for each symbol into `stockprices_recent_<exchange>`.
8. System sets `symbol_master.split_factor_current` for each symbol to the latest `split_factor` from its history table.
9. System reports: total rows migrated, symbols processed, any symbols skipped (e.g. insufficient history for the recent window, or exchange without a destination database).

**Postconditions:**
- Every active symbol has a `stockprices_<symbol>` table in its exchange database with full history and correct `split_factor` per row.
- Every exchange database has a `stockprices_recent_<exchange>` table with the last N days of prices for all active symbols in that exchange.
- `symbol_master.split_factor_current` is populated for every active symbol.

**Success criteria:**
- Total rows across all per-symbol tables = original `stockprices` row count (validates no data loss in the history migration).
- Recent tables contain exactly the last N days per symbol (validates retention window).
- Adjusted-price spot-check passes for a sample of split-history symbols (validates `split_factor` backfill).

**Error handling:**
- If a symbol's exchange has no destination database, the symbol is skipped and listed in the error report for manual resolution (add a database, or correct the exchange code).
- If a symbol has special characters in its name that can't be sanitized for a table name, it is skipped and flagged for cleanup.

---

## UC-15b: Nightly dual-write ingestion (history + recent)

**Actor:** Nightly price ingestion pipeline
**Preconditions:**
- Per-symbol history tables and per-exchange recent tables exist for all active symbols (UC-15a complete).
- The price source (yfinance / other) has returned new price rows for today.
- The ingestion service is configured with the router and schema manager.

**Steps:**
1. For each new price row:
   a. Resolve the route for the symbol (`SymbolTableRouter::routeForSymbol`).
   b. Begin a transaction on the exchange database.
   c. Insert/replace the row into `stockprices_<symbol>`.
   d. Insert/replace the row into `stockprices_recent_<exchange>`.
   e. If the recent table now has more than N days for this symbol, delete the oldest row for this symbol.
   f. Update `symbol_master.split_factor_current` for this symbol if the new row's `split_factor` is higher than the current value.
   g. Commit.
2. After all rows are written, update `stock_performance_windows` short windows (1Q, 4W, 12W, 24W, 52W, YTD) from the recent table via the lightweight nightly rollup.
3. Report: symbols updated, rows written, any failures.

**Postconditions:**
- The per-symbol history table has the new price row for each symbol.
- The recent table has the new price row and is trimmed to retention.
- Short performance windows are refreshed.

**Success criteria:**
- No rows lost: every source price row appears in both the history table and the recent table (for symbols within retention).
- Recent table retention enforced: no symbol has rows older than N days in the recent table.
- Transaction atomicity: if a write fails, neither the history table nor the recent table is left partially updated for that symbol.

---

## UC-15c: Routing validation (formulaic from symbol_master)

**Actor:** Automated test suite / deployment validation
**Preconditions:**
- `symbol_master` is populated.
- Exchange databases exist.

**Steps:**
1. For every active symbol in `symbol_master`, call `SymbolTableRouter::routeForSymbol`.
2. Verify the returned `db_name` matches the expected exchange database for that symbol's `exchange` value (against the exchange→db mapping derived from `symbol_master`).
3. Verify the returned `history_table` equals `'stockprices_' . sanitized_symbol`.
4. Verify the returned `recent_table` equals `'stockprices_recent_' . exchange_suffix`.
5. Verify the returned `connection` connects to the correct database.
6. Report any mismatches.

**Postconditions:**
- Routing is validated as formulaic from `symbol_master` — no hardcoded names.

**Success criteria:**
- 100% of active symbols route correctly.
- No hardcoded database or table names are used in the routing layer.

---

## UC-15d: Performance window recalculation (quarterly / post-earnings)

**Actor:** Scheduled performance-window job
**Preconditions:**
- Per-symbol history tables exist with full history.
- `stock_performance_windows` table exists.

**Steps (quarterly long-window recalculation):**
1. For each active symbol, read the per-symbol history table.
2. Compute `perf_2a`, `perf_3a`, `perf_5a`, `perf_10a` from `MAX(price_date)` back to the target dates.
3. Upsert into `stock_performance_windows` with `last_recomputed = NOW()`.
4. Skip symbols with insufficient history; log them.

**Steps (post-earnings tenet recalculation):**
1. Detect symbols with a new earnings release since last recompute (from the Zacks / fundamental feed).
2. For each such symbol, recalculate Buffett tenets and fundamental scores.
3. Store results with `last_recomputed`.

**Steps (nightly short-window rollup):**
1. After nightly ingestion, read the recent table.
2. Recalculate short windows (1Q, 4W, 12W, 24W, 52W, YTD) for all active symbols.
3. Upsert into `stock_performance_windows`.

**Success criteria:**
- Long windows are no more than one quarter stale.
- Tenet-based scores are recalculated after each earnings release.
- Short windows are current as of the most recent nightly ingestion.

---

## UC-15e: Backtest cross-symbol audit (follow-up phase)

**Actor:** Developer / QA
**Preconditions:**
- The refactor is in place (per-symbol history tables, recent tables, router, repository).

**Steps:**
1. Review the Advisor backtest and portfolio-selection code for any query that reads prices across multiple symbols in a single SQL statement.
2. For each such query, determine whether it can be rewritten to use the recent table or a scratch table, or whether it genuinely needs multi-symbol raw history.
3. Where a scratch table is needed, create a purpose-built scratch table (persistent or temp) and add it to the repository interface.
4. Run the backtest against the new storage and verify results match the old behavior.

**Postconditions:**
- All backtest/advisor code works against the new storage.
- Any cross-symbol scratch tables are documented and managed through the schema manager.

**Success criteria:**
- Backtest results match pre-refactor results for a sample portfolio/screen.
- No query directly accesses the old `stockprices` table.
