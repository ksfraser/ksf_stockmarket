# FR-15: Stock Price Storage Refactor — Per-Symbol Tables in Per-Exchange Databases

**BABOK v2.0** | **Category:** Functional Requirement | **Parent:** BR-15
**Module:** Stock Price Storage / Nightly Ingestion
**Author:** KSF | **Status:** Draft | **Date:** 2026-09-09

## Statement

The system shall store stock price history in **per-symbol tables inside per-exchange databases**, routed entirely through `symbol_master.exchange` and `symbol_master.symbol`, with a bounded **recent-price table per exchange** for cross-symbol filtering, and shall recalculate expensive price-change windows on a **quarterly / post-earnings** cadence rather than nightly.

## Affected Components

- **New:** `src/Model/SymbolTableRouter.php` — derives (db_name, history_table, recent_table, exchange) from a symbol using `symbol_master.exchange` and `symbol_master.symbol`.
- **New/modified:** `src/Service/StockPriceRepository.php` — per-symbol and recent price reads/writes using the router; no hardcoded table names.
- **New/modified:** `src/Service/PriceIngestionService.php` — nightly ingestion dual-writes to per-symbol history table + recent table per exchange, in a single per-exchange transaction, and trims the recent table to retention.
- **New/modified:** `src/Service/PerformanceWindowService.php` — recalculates `stock_performance_windows` on a quarterly / post-earnings cadence instead of nightly; short-window rollup nightly from the recent table.
- **New/modified:** `scripts/migrate_prices_to_exchange_dbs.php` — migration script that splits the existing `stockprices` rows into per-symbol tables and recent tables across the exchange databases.
- **New:** Centralized schema management (`src/Model/SchemaManager.php` or equivalent) — CREATE/ALTER/DROP of price tables goes through this layer; no raw SQL with hardcoded table names anywhere.
- **Affected (reads):** Any code that currently reads `stockprices` directly (filter engine, Zacks screen runner, Advisor backtest, MACD/indicator calculations) — these are migrated to the repository interface.
- **Affected (config):** `config.yaml` gains per-exchange database blocks (or a single block + exchange→db mapping) so the router can resolve connection params per exchange.

## Schema (To-Be)

### Per-symbol history table (one per active symbol, in the symbol's exchange DB)

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

`<symbol>` is the sanitized symbol string from `symbol_master.symbol`, derived by the router at migration time and at runtime for any per-symbol operation. `split_factor` is the cumulative split adjustment factor as of this row.

### Recent (cross-symbol) price table (one per exchange DB)

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

### exchange database inventory (live verified)

| Database (to-be) | exchange value(s) routed here | Active symbols (live) | Notes |
|---|---|---|---|
| `ksfraser_sm_tsx` | TSX | 880 | |
| `ksfraser_sm_nasdaq` | NASDAQ | 2,691 | Largest; monitor size |
| `ksfraser_sm_nyse` | NYSE, NYQ (and AMEX-coded if any appear) | 184 | NYSE + NYSE-American |
| `ksfraser_sm_v` | TSX.V | 15 | |
| `ksfraser_sm_cse` | CSE | 0 (today) | Future-proofing |
| `ksfraser_sm_amex` | AMEX | 0 (today) | Future-proofing |
| `ksfraser_sm_other` | OTC, TOR, EUR, GBP, CNY, HKD, and all other minor codes | ~20 | Fallback for exchanges without a dedicated DB |

### symbol_master additions

- `split_factor_current` DOUBLE NULL — the current cumulative split factor for the symbol (cached convenience; derived from the latest row in `stockprices_<symbol>`). Populated/updated by the ingestion service after each nightly run.

### stock_performance_windows refresh cadence

- Short windows (1Q, 4W, 12W, 24W, 52W, YTD) → refreshed nightly from the recent table via a lightweight rollup (cheap: small table, bounded rows).
- Long windows (2Y, 3Y, 5Y, 10Y) → recalculated **quarterly** or after earnings release for the symbol. Stored in `stock_performance_windows` with a `last_recomputed` timestamp.
- Buffett-tenet / fundamental-based scores → recalculated **quarterly** or **after earnings**, stored in their own table(s) with `last_recomputed`.

## Routing (formulaic from symbol_master)

`SymbolTableRouter::routeForSymbol(string $symbol): array` returns:

```php
[
    'db_name'       => 'ksfraser_sm_nasdaq',   // from exchange → db mapping
    'history_table' => 'stockprices_AAPL',      // 'stockprices_' . sanitize($symbol)
    'recent_table'  => 'stockprices_recent_nasdaq', // 'stockprices_recent_' . db_exchange_suffix
    'exchange'      => 'NASDAQ',
    'connection'    => $pdoForExchange('NASDAQ'),
]
```

The exchange→db mapping is derived from `symbol_master.exchange` at migration time and stored as a lookup that the router uses. No hardcoded exchange→db pairs in code; the mapping is data, derived from the live `symbol_master` contents. If a new exchange appears, the mapping is regenerated and a database is created for it through the schema manager.

Sanitization of symbol for table name: allow `[A-Za-z0-9._-]` only; reject symbols with other characters (should not happen in practice; if it does, the symbol is flagged for cleanup rather than given a table name with special chars).

## Nightly ingestion (dual-write, per-exchange transaction)

For each new price row ingested:

1. Resolve the route for the symbol (db + history table + recent table).
2. Within a transaction on the **exchange database** (which contains both the per-symbol table and the recent table — same DB, so one transaction covers both):
   - Insert/replace the row into `stockprices_<symbol>`.
   - Insert/replace the row into `stockprices_recent_<exchange>`.
   - If the recent table exceeds retention for this symbol (oldest row beyond 1 year / 200 trading days), delete the oldest row for this symbol.
   - Update `symbol_master.split_factor_current` for this symbol to the latest `split_factor` value.
3. Commit.

Both writes are in the same database and same transaction, so atomicity is guaranteed per symbol per night. There is no cross-database transaction needed because each exchange's recent table and its symbols' history tables all live in that exchange's database.

## Adjusted prices and split-factor logic

- `split_factor` on row N = `split_factor` on row N-1 × `split_ratio` on row N (for a forward split; for a reverse split the ratio is <1 and the factor decreases). Actually correct direction: `split_factor` accumulates so that `adj_close = close / split_factor` (or `close × split_factor` depending on convention — the convention must be consistent and documented; implement as `adj_close = close / cumulative_split_factor` where cumulative starts at 1 and is multiplied by split_ratio on each split row).
- `symbol_master.split_factor_current` = `split_factor` from the latest row for that symbol.
- Backfill: for existing symbols, compute `split_factor` history from the existing `split_ratio` column in the old `stockprices` during migration.

## Performance window recalculation

### Quarterly cadence (long windows)

A scheduled job (quarterly, e.g. aligned with calendar quarters) recalculates:
- `perf_2a`, `perf_3a`, `perf_5a`, `perf_10a`
- Buffett-tenet / fundamental-based scores

For each active symbol, read the per-symbol history table, compute the window from `MAX(price_date)` back to the target date, and upsert into `stock_performance_windows`. Only symbols that have data covering the full window are updated; symbols with insufficient history are skipped (and flagged).

### Post-earnings cadence (tenet-based scores)

A scheduled job watches for earnings-release dates (from the Zacks / fundamental feed) and, for symbols that had an earnings release since the last recompute, recalculates:
- Buffett tenets
- Any fundamental score that depends on the latest reported figures

### Nightly rollup (short windows)

Nightly, after ingestion, a lightweight job refreshes only the short windows (1Q, 4W, 12W, 24W, 52W, YTD) for all active symbols from the recent table. This is cheap because the recent table is bounded and small per symbol. The filter engine and screen runner read these short windows.

## DB size target

The refactor must bring the system into compliance with the host's preference for the database to stay **under 1 GB**. Specifically:
- Move `stockprices` out of `ksfraser_stock_market` into the per-exchange databases.
- Keep `ksfraser_stock_market` (or its successor active DB) under 1 GB by removing the largest table.
- Ensure each exchange DB is individually manageable; the largest (NASDAQ) must not grow unbounded — per-symbol tables make this manageable, and the recent tables are bounded by retention.

## Database maintenance (centralized)

All price-table schema operations go through a centralized schema manager:
- `SchemaManager::ensurePriceHistoryTable(string $symbol, string $exchange)`: creates `stockprices_<symbol>` if it doesn't exist, in the correct exchange database.
- `SchemaManager::ensureRecentTable(string $exchange)`: creates `stockprices_recent_<exchange>` if it doesn't exist.
- `SchemaManager::ensureExchangeDatabase(string $exchange)`: creates the exchange database if it doesn't exist.
- `SchemaManager::dropPriceHistoryTable(string $symbol, string $exchange)`: drops a per-symbol table (used when a symbol is deactivated/permanently removed).
- No raw SQL with hardcoded `stockprices_<symbol>` or `ksfraser_sm_<exchange>` names anywhere in the codebase. The router and schema manager are the only places that compose these names.

## Tests / Validation

1. **Routing correctness:** For every active symbol in `symbol_master`, `SymbolTableRouter::routeForSymbol()` returns a db name that matches the symbol's exchange, and a history table name that matches the symbol. Verify against the live exchange→db mapping.
2. **Migration completeness:** After `migrate_prices_to_exchange_dbs.php` runs, the total row count across all per-symbol tables + recent tables equals the original `stockprices` row count (within the retention drop for recent tables — recent tables will have fewer rows because older history is only in the per-symbol tables).
3. **Adjusted price accuracy:** For a sample of symbols that have had splits (e.g. symbols where `split_ratio < 1` exists in the old data), verify `adj_close = close / cumulative_split_factor` holds for every row in the new per-symbol table.
4. **Nightly dual-write:** Run one night's ingestion; verify both the per-symbol table and the recent table received the new rows, and the recent table was trimmed to retention.
5. **Performance window recalculation:** After a quarterly recalculation, verify `stock_performance_windows` has recent `last_recomputed` timestamps and the values are consistent with manual calculation for a sample symbol.
6. **Filter engine / screen runner still work:** Run the existing filter and screen code against the new repository interface and verify results match the old behavior for a sample query.
7. **Backtest audit (later phase):** Confirm the Advisor backtest and portfolio-selection code either works against the new repository or is migrated; document any cross-symbol price queries that required scratch tables (§5.10).

## Risks

- **NASDAQ size monitoring.** NASDAQ has 2,691 active symbols. If the host later demands further splitting, NASDAQ can be subdivided (e.g. by symbol prefix A–M / N–Z) without changing the routing model — just add more exchange databases and extend the mapping. This is a future concern, not a phase-1 blocker.
- **Minor-exchange fallback.** Exchanges with few symbols (OTC, TOR, EUR, etc.) route to `ksfraser_sm_other`. This is fine for now, but if `ksfraser_sm_other` grows large, it too can be subdivided later.
- **Backtest cross-symbol queries.** If the Advisor backtest currently runs queries joining prices across symbols, it must be audited and migrated to use scratch tables where needed. This is a phase-2 validation item (§7.4 in BR-15), not a blocker for the schema migration.
- **Backfill correctness for `split_factor`.** The migration must correctly compute cumulative split factors from the existing `split_ratio` column. Test against known-split symbols before running on the full dataset.

## Related

- BR-15 (parent)
- BR-14 / FR-14: Zacks RW pipeline (reads recent prices + performance windows)
- `symbol_master` table (routing source of truth)
- `stock_performance_windows` table (refresh cadence change to quarterly)
- config.yaml `data:` blocks (per-exchange DB connection config)
