# BR-15: Stock Price Storage Refactor — Per-Symbol Tables in Per-Exchange Databases

**BABOK v2.0** | **Category:** Business Requirement | **Priority:** Must Have
**Module:** Stock Price Storage / Nightly Ingestion
**Author:** KSF | **Status:** Draft | **Date:** 2026-09-09
**DB constraint:** The database host provider has requested the database stay **smaller than 1 GB**. The current `ksfraser_stock_market` is approximately 187 MB; the pressure is on growth trajectory and on the single large `stockprices` table (10.7M rows, ~174 MB, ~93% of DB size). See §8 for the size picture.

## Statement

The monolithic `stockprices` table (one row per symbol per date, shared across all exchanges) shall be replaced with a **per-symbol price table inside a per-exchange database**, owned and routed entirely through `symbol_master` so that no consumer hardcodes a database or table name.

Concretely:
1. **One database per exchange** (e.g. `ksfraser_sm_tsx`, `ksfraser_sm_nasdaq`, `ksfraser_sm_nyse`, `ksfraser_sm_v`, `ksfraser_sm_cse`, `ksfraser_sm_amex`). A symbol's exchange in `symbol_master.exchange` determines its database.
2. **One price-history table per symbol** inside its exchange database (e.g. `AAPL` in `ksfraser_sm_nasdaq` gets table `stockprices_AAPL`). Long-run price history lives here.
3. **One recent-price table per exchange database** holding the last N days of prices for all active symbols in that exchange, for cross-symbol filtering / MACD / recent-return calculations. This is the table the filter engine, screen runner, and Advisor backtest hit for "current" price work.
4. **Precomputed performance/return windows** (`perf_1q`, `perf_5y`, `perf_10y`, Buffett tenets, etc.) become their own tables, recalculated **quarterly or after earnings**, not nightly — because they change only when fundamentals release.
5. **Nightly ingestion writes to both the recent table and the per-symbol history table** at the same time, so trimming the bottom of the recent table never loses history (history is already safely in the per-symbol table).
6. **All schema maintenance (CREATE / ALTER / DROP of price tables)** goes through a centralized routing + schema-management layer; no raw SQL with hardcoded `stockprices_<symbol>` table names anywhere in the codebase.

## Rationale

1. **Size is dominated by one table.** `stockprices` is 10.7M rows and ~174 MB — roughly 93% of the current database. Splitting it across databases and per-symbol tables is the only structural change that addresses the host's size concern. Everything else (fundamentals, zacks_*, perf windows, symbol_master, user_screens, settings) is collectively a few MB and does not need splitting.
2. **There are no cross-symbol price calculations in the current code.** The price data is used for per-symbol lookups (latest close, MACD, per-symbol return windows) and for the precomputed window table. Cross-symbol work is limited to comparisons (sector-relative, exchange-relative) that read the *recent* table or the precomputed window table — not raw history across symbols in one query. This makes per-symbol tables a natural fit: the common case is "give me prices for symbol X," and per-symbol tables are cheap and easy to maintain.
3. **Exchange is already a first-class attribute.** `symbol_master.exchange` exists and is stable. Routing by exchange is formulaic and already mirrors how Kev has organized the exchange databases (`ksfraser_sm_tsx`, `_nasdaq`, `_nyse`, `_v`, `_cse`, `_amex`). Using `symbol_master` as the routing source of truth means the DAO/Repository builds the query at runtime by substitution — no hardcoded names.
4. **History does not change shape.** The price-history schema (`open, high, low, close, volume, adj_close, dividend, split_ratio`) has been stable for 5+ years. Splitting into per-symbol tables does not increase schema-change risk — it decreases it, because each symbol's table is small and independently maintainable.
5. **Precomputed windows are expensive nightly for little gain.** A 10-year return or a Buffett-tenet score changes only when earnings/fundamentals are released. Recomputing nightly for all 3,600 symbols wastes CPU and writes. Moving these to their own tables, refreshed quarterly (or after earnings for the tenet-based ones), keeps the nightly pipeline fast and still keeps the filter engine's data fresh enough.
6. **Advisor backtests are mostly per-portfolio or per-screen, not "give me all prices for all symbols in one query."** Where a backtest does need cross-symbol price history (e.g. a portfolio's combined drawdown, or a screen that ranks across sectors), it can use the recent table or a temporary/scratch table built for that run. We validate this during the backtest-audit phase (§7) and add permanent scratch tables only where they're actually needed.

## Current State (As-Is)

- One table `stockprices` in `ksfraser_stock_market`: `id, symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency`. ~10.7M rows, ~174 MB.
- All price reads go through this one table with `WHERE symbol = ?` or `WHERE symbol IN (...)`.
- `symbol_master.exchange` is present (NASDAQ, TSX, NYSE, TOR, TSX.V, OTC, NYQ, and ~20 minor exchange codes) but is not used to route price storage.
- Performance/return windows (`perf_1q`, `perf_5y`, etc.) are either computed at runtime from `stockprices` (expensive) or stored in `stock_performance_windows` and refreshed nightly.
- Zacks data is current-point-in-time only (no historical rating archive exists, and Zacks does not expose a historical ratings feed). Zacks_* columns in `fundamentals` are latest-fetch only.
- No adjusted-price split-factor tracking beyond the existing `adj_close` and `split_ratio` columns.
- Schema maintenance is ad-hoc SQL; there is no centralized layer that derives per-symbol table names from `symbol_master`.

## Target State (To-Be)

### 5.1 Per-exchange databases

| Database | Exchange (from `symbol_master.exchange`) | Active symbols (live) | Notes |
|---|---|---|---|
| `ksfraser_sm_tsx` | TSX | 880 | Includes TSX main board |
| `ksfraser_sm_nasdaq` | NASDAQ | 2,691 | Largest; will be the biggest DB |
| `ksfraser_sm_nyse` | NYSE, NYQ (and AMEX-coded where they exist) | 184 | NYSE + NYSE-American; see §5.9 on AMEX |
| `ksfraser_sm_v` | TSX.V and other TSX-venture codes | 15 | Small today; exists for future growth |
| `ksfraser_sm_cse` | CSE | 0 (today) | Exists for future; no symbols yet |
| `ksfraser_sm_amex` | AMEX-coded symbols | 0 (today) | Exists for future; see §5.9 |

Databases that have zero active symbols today (`cse`, `amex`) are created anyway so the routing table is complete and future symbols on those exchanges land correctly without a schema change.

### 5.2 Per-symbol price-history table

Inside each exchange database, each active symbol gets its own table:

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
    split_factor   DOUBLE          DEFAULT 1,  -- cumulative factor as of this row
    currency       VARCHAR(3)      NOT NULL DEFAULT 'USD',
    PRIMARY KEY (price_date),
    INDEX idx_close (close)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

`<symbol>` is the literal symbol string from `symbol_master.symbol`, sanitized for use as a table name (the routing layer handles this). `split_factor` is the cumulative split adjustment factor as of this row — see §5.7.

### 5.3 Recent (cross-symbol) price table per exchange

One table per exchange database holding the last N days of prices for all active symbols in that exchange. This is the table the filter engine, screen runner, MACD, and Advisor backtest hit for "current" price work:

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

Retention: keep the last **1 year** of daily prices (or last **200 trading days** for indicators like MACD 200 that need 200 rows). When a new row is inserted for a symbol, the oldest row for that symbol beyond the retention window is dropped. This keeps the recent table bounded and small — roughly (active symbols in exchange) × (retention days) rows.

Nightly ingestion writes each new price row to **both** the per-symbol `stockprices_<symbol>` table (permanent history) and the recent table (bounded working set) in the same transaction per exchange.

### 5.4 Precomputed performance / return windows (own tables)

The price-change windows and fundamental-based scores that the filter engine and screens currently compute nightly move to their own tables, refreshed on a **quarterly** cadence (or after earnings for tenet-based scores):

- `stock_performance_windows` is retained but its refresh cadence drops from nightly to **quarterly** (or after earnings release for the symbol). For the short windows (1Q, 4W, etc.) that the filter engine needs "now," the recent table + a lightweight nightly rollup is sufficient.
- Buffett-tenet scores, Warren-Buffett-style fundamental scores, and any other quarterly/annual recompute move to their own tables with a `last_recomputed` timestamp and an earnings-aware refresh trigger.

This cuts nightly compute for these windows from "all symbols every night" to "only symbols that had an earnings release or hit a quarterly boundary."

### 5.5 Zacks data (current only — no history)

Zacks ratings and fundamental attributes are **point-in-time only**. There is no historical Zacks rating archive available, and Zacks does not expose a feed that lets us see what rank a stock had on a past date. The `zacks_*` columns in `fundamentals` remain latest-fetch only. This is accepted as a limitation — the system does not claim to show historical Zacks ratings. (If a historical Zacks feed becomes available in the future, it would get its own archive table in the relevant exchange DB.)

### 5.6 Routing layer (DAO/Repository builds queries by substitution)

All database and table name derivation goes through `symbol_master`. A routing helper (`SymbolTableRouter`) takes a symbol and returns the (db_name, history_table_name, recent_table_name) tuple computed from `symbol_master.exchange` and `symbol_master.symbol`. Consumers never hardcode `stockprices_<symbol>` or `ksfraser_sm_<exchange>`.

```php
// Example — actual implementation lives in src/Model/SymbolTableRouter.php
$route = SymbolTableRouter::routeForSymbol('AAPL');
// $route->dbName       = 'ksfraser_sm_nasdaq'
// $route->historyTable = 'stockprices_AAPL'
// $route->recentTable  = 'stockprices_recent_nasdaq'
// $route->exchange     = 'NASDAQ'
```

The DAO / Repository layer (e.g. `StockPriceRepository`) uses the router to build queries at runtime. No raw SQL with hardcoded table names anywhere in the codebase.

### 5.7 Adjusted prices and split-factor tracking

The current `stockprices` has `adj_close` and `split_ratio` but no explicit cumulative split-factor tracking. The refactor adds `split_factor` per row (cumulative factor as of that row) so that `adj_close` is always derivable and verifiable:

- `split_factor` on row N = product of all `split_ratio` values from row 1 through row N, applied in reverse (i.e. divided out to get adjusted prices).
- `symbol_master` holds the **current** cumulative `split_factor` per symbol as a convenience (so the latest adjusted close is always available without scanning the whole table).
- Nightly ingestion recomputes `adj_close` and `split_factor` for the new row from the prior row's `split_factor` × the new row's `split_ratio`.

This makes adjusted-price accuracy auditable and survives splits correctly.

### 5.8 Nightly ingestion (dual-write)

Nightly price ingestion writes each new price row to **both**:
1. The per-symbol `stockprices_<symbol>` table in the symbol's exchange database (permanent history, unbounded).
2. The `stockprices_recent_<exchange>` table for that exchange (bounded, last 1 year / 200 days).

Both writes happen in the same per-exchange transaction. The recent table's oldest rows are trimmed as part of the same pass (delete rows older than retention for that symbol before inserting the new one, or use a priority-insert pattern). This means we never need a separate "move history" pass after trimming — history is already safely in the per-symbol table.

### 5.9 AMEX / NYSE routing

NYSE and AMEX merged under NYSE Euronext. In the live `symbol_master`, NYSE-coded symbols are 176 and NYQ-coded are 8; there are currently **zero** symbols coded explicitly as AMEX. For routing purposes:
- Symbols with `exchange = 'NYSE'` or `exchange = 'NYQ'` route to `ksfraser_sm_nyse`.
- If a symbol ever appears with `exchange = 'AMEX'`, it routes to `ksfraser_sm_amex` (the database exists; today it's empty).
- The `amex` database is retained for future-proofing even though it has no symbols today.

### 5.10 Backtest cross-symbol needs (validated later)

Advisor backtests and portfolio selection that need cross-symbol price data use:
- The recent table for "current" cross-symbol comparisons.
- Temporary or permanent scratch tables for calculated cross-symbol values (e.g. a portfolio's combined drawdown, a screen's cross-sector ranking) built at run time.
- We audit the existing backtest/advisor code in a later phase (§7.4) to confirm whether any path truly needs raw multi-symbol history in one query; if so, we add a purpose-built scratch table rather than reintroducing a monolithic `stockprices`.

## Acceptance Criteria

1. **Routing is formulaic from `symbol_master`.** Given any active symbol, `SymbolTableRouter::routeForSymbol()` returns the correct (db, history table, recent table) based on `symbol_master.exchange` and `symbol_master.symbol`, with no hardcoded names.
2. **Per-symbol history table exists for every active symbol** in the correct exchange database, with the schema in §5.2 and the `split_factor` column.
3. **Recent table exists per exchange** with the schema in §5.3, holding the last 1 year / 200 trading days of prices for all active symbols in that exchange.
4. **Nightly ingestion dual-writes** to both the per-symbol table and the recent table, in the same per-exchange transaction, and trims the recent table to retention.
5. **Adjusted prices are accurate.** `adj_close` is derivable from `close` and `split_factor` and matches the pre-refactor values for a sample of symbols that have had splits.
6. **Schema maintenance is centralized.** No raw SQL with hardcoded `stockprices_<symbol>` or `ksfraser_sm_<exchange>` names anywhere; all CREATE/ALTER/DROP goes through the centralized schema-management layer.
7. **Performance windows are recalculated quarterly (or after earnings)**, not nightly, and the filter engine still gets current-enough values from the recent table + lightweight rollup.
8. **The database host's size target is addressed.** After migration, the per-exchange databases are individually smaller and the largest (NASDAQ) is bounded; the recent tables are bounded by retention; the primary `ksfraser_stock_market` database shrinks as `stockprices` is moved out.

## Stakeholders

- Kevin Fraser (advisor / end user; also the architect driving the refactor)
- DB provider (constraint: < 1 GB preference)
- Advisors (backtest / portfolio users — their cross-symbol needs must be validated in §7.4)
- The nightly ingestion pipeline (must be updated to dual-write)

## Risks

- **NASDAQ DB size.** NASDAQ has 2,691 active symbols — the largest exchange DB. Even with per-symbol tables, the NASDAQ database will be the biggest. Per-symbol tables make this manageable (each symbol's table is small and independently maintainable), but we should monitor the NASDAQ DB size and be ready to split it further (e.g. by symbol range A–M / N–Z) if the host pushes back. This is a future concern, not a blocker.
- **Routing bugs on obscure exchange codes.** `symbol_master.exchange` has ~25 distinct values today; only 6 exchange databases exist. Symbols on exchanges without a dedicated DB (e.g. OTC, TOR, EUR, etc.) need a fallback destination. The router must have an explicit "other" destination (e.g. `ksfraser_sm_other` or route to the closest match) and the requirement is incomplete until that's defined. (Suggested: route minor exchanges into a `ksfraser_sm_other` database, or aggregate by geography.)
- **Backtest cross-symbol assumptions.** If the Advisor backtest currently runs queries that join prices across symbols in one query (we haven't confirmed it doesn't), the refactor could break it. The backtest audit in §7.4 must happen before the migration is declared complete.
- **Dual-write atomicity.** Writing to two tables in two databases (per-symbol is in the exchange DB, recent is also in the exchange DB — same DB, so actually a single DB transaction covers both) is straightforward per exchange, but the ingestion script must handle per-exchange transactions correctly when a symbol's exchange DB is different from another's. Within one exchange DB, the recent table and the per-symbol table are in the same database, so a single transaction works.
- **`split_factor` backfill.** Existing symbols that have had splits need their `split_factor` history backfilled correctly. This is a migration task, not a blocker for the schema design, but it must be done before the adjusted-price accuracy acceptance criterion (§6.5) can be verified.

## Related

- BR-14: Zacks RW Screen Pipeline (Zacks_* data is current-only; the screen runner reads recent prices + `stock_performance_windows`)
- FR-14: Zacks RW Pipeline (schema for `stock_performance_windows`, `fundamentals`, `zacks_*` columns)
- BR-11 / FR-11: Seg-Fund filters (filter engine pattern — this refactor changes the price side the filter engine reads, not the filter engine itself)
- `symbol_master` (routing source of truth — exchange + symbol)
- `stock_performance_windows` (precomputed windows — refresh cadence changes to quarterly)
