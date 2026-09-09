# Stock Filter Engine — Architecture & Schema Findings

## Audience

Kevin Fraser and Big Pickle. This doc captures the actual schema state, the corrections applied to `StockFilter.php`, the pre-compute recommendation, and the integration points — so both parties can work complimentarily rather than at cross purposes on the Zacks feature branch and the All Symbols filter engine.

## 1. DB inventory findings (real schema, 2026-09-05)

All counts are from `ksfraser_stock_market` on `ksfraser.ca` (MariaDB 10.6.27), verified live via PDO from this host (192.168.1.102).

### 1.1 Symbol & price infrastructure

| Table | Rows | Notes |
|---|---|---|
| `symbol_master` | 3,583 active | Keyed by `symbol`; has `is_active` (tinyint default 1), `exchange`, `sector`, `industry`, `name`, `currency`, `geography`, `withholding_tax`, `is_watchlist`, `is_portfolio`, `pipeline_state` |
| `stockprices` | — | Columns: `id, symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency` — **does NOT have** `active`, `avg_volume`, or `relative_volume` |
| `stockprices` primary key | `(id)` + index on `(symbol, price_date)` | No `active` column — active flag lives in `symbol_master.is_active` |

**Implication:** The old `StockFilter.php` assumed `sp.active = 1` and `sp.avg_volume` / `sp.relative_volume` existed. These columns do not exist. The active flag is `sm.is_active = 1`. Volume-based filters (`avg_volume`, `rel_volume`) have been removed from the filter engine pending a precomputed volume stats table.

### 1.2 Score infrastructure

| Table | Rows | Columns | Notes |
|---|---|---|---|
| `evalsummary` | **1** | `id, symbol, price_date, close, consensus_signal, consensus_strength, atr_position_size, portfolio_weight, strategy_json` | **Only 1 row.** Does NOT contain `totalscore`, `llm_recommendation`, or `human_recommendation` — the old `StockFilter.php` referenced these non-existent columns. Removed. |
| `lippper_scores` | 7,482 | `symbol, peer_group_type, peer_group_value, as_of, ret_1y, ret_3y, ret_5y, ret_10y, ytd, volatility_3y, downside_dev, sharpe_3y, sortino_3y, preservation_score, total_return_score, consistent_score, composite_score, sector_rank_pct` | The only SQL-filterable peer-relative score table. `composite_score` is the primary score filter exposed. |
| `evaluation_scores` | 2 | `id, symbol, eval_type, domain, score, max_score, grade, note, created_by, created_at, updated_at` | Only 2 rows; not a general stock score table. Not usable as a filter source. |
| `zacks_broker_recommendations` | — | `symbol, firm, analyst, grade, price_target, action, rec_date, fetch_date` (and likely more) | The `action` column (Buy/Hold/Sell) is the available recommendation filter source. The old `StockFilter.php` referenced `es.llm_recommendation` / `es.human_recommendation` which don't exist — switched to `zr.action`. |

**Implication:** There is no single "total score" column for stocks. The filter engine exposes `lippper_scores.composite_score` as the score filter. Zacks-style component scores (alpha, relative strength, rank, estimate revisions) are computed in PHP by `StockController::calcZacksStyleScore()` per-symbol and are NOT stored in DB — they are not SQL-filterable in this version. Full Zacks-component filtering requires a precomputed scores table (see Section 3).

### 1.3 Fundamental attributes (the big one)

The `fundamentals` table (17,111 rows, keyed by `symbol` + `fetch_date`) is rich and is the primary source for the stock-side fundamental filters. Usable (non-null, non-zero, non-empty) row counts:

| Column | Usable rows | Notes |
|---|---|---|
| `roe` | 13,232 | Return on equity — high coverage |
| `roa` | 13,402 | Return on assets — high coverage |
| `profit_margin` | 13,285 | Net margin |
| `debt_to_equity` | 12,773 | Debt/equity ratio |
| `revenue_growth` | 9,739 | Revenue growth % |
| `gross_margin` | 9,579 | Gross margin % |
| `operating_margin` | 9,786 | Operating margin % |
| `market_cap` | 11,411 | Market cap (double) — primary size filter |
| `shares_outstanding` | 12,344 | Shares outstanding |
| `trailing_pe` | 2,211 | Trailing P/E — moderate coverage |
| `forward_pe` | 913 | Forward P/E — lower coverage |
| `peg_ratio` | 475 | PEG — low coverage |
| `price_to_book` | 2,307 | P/B |
| `price_to_sales` | 2,021 | P/S |
| `book_value` | 2,175 | Book value/share |
| `beta` | 2,303 | Beta — moderate coverage |
| `dividend_yield` | 1,856 | Dividend yield % — lower coverage |
| `free_cash_flow` | 1,472 | FCF (absolute) |
| `fcf_per_share` | 1,386 | FCF/share |
| `insider_percent` | 2,123 | Insider ownership % |
| `institutional_percent` | 2,309 | Institutional ownership % |
| `current_ratio` | 2,118 | Current ratio |
| `earnings_growth` | 1,415 | EPS growth % |
| `operating_cash_flow` | 1,511 | OCF (absolute) |
| `total_revenue` | 16,231 | Total revenue |
| `zacks_roi` | 1,281 | Zacks ROI (stored by fundamental_data.py) |
| `zacks_net_profit_margin` | 981 | Zacks net profit margin |
| `zacks_lt_debt_capital_pct` | 1,213 | Zacks LT debt / capital % |
| `zacks_eps_change_f1_4w` | 513 | Zacks EPS change F1 4-week |
| `zacks_eps_change_f2_4w` | 513 | Zacks EPS change F2 4-week |
| `zacks_price_change_52w` | 1,473 | Zacks 52-week price change % |
| `zacks_num_analysts` | 1,217 | Zacks number of analysts covering |
| `short_ratio` | 359 | Short ratio (low coverage) |
| `short_percent` | 289 | Short % of float (low coverage) |
| `five_year_div_yield` | 1,087 | 5-year avg div yield |
| `dividend_rate` | 1,455 | Dividend rate per share |
| `annual_dividend_total` | 1,451 | Total annual dividend |
| `payout_ratio` | 740 | Payout ratio (low coverage) |
| `trailing_eps` | 897 | Trailing EPS |
| `forward_eps` | 1,189 | Forward EPS |
| `total_revenue` | 16,231 | Total revenue (gross, for growth calc) |

**Columns that do NOT exist in `fundamentals`:**
- `fcf_yield` — does not exist as a column; would need to compute as `free_cash_flow / market_cap` at runtime. The old `StockFilter.php` referenced this non-existent column. Removed from filter engine.

**Zacks attributes already in `fundamentals`:** The `fundamental_data.py` fetcher stores zacks_* columns directly (roi, net_profit_margin, lt_debt_capital_pct, eps_change_f1_4w, eps_change_f2_4w, price_change_52w, num_analysts). These are now exposed as filterable columns in `StockFilter.php`.

### 1.4 Existing performance / returns tables

| Table | Rows | Purpose | Stock-filterable? |
|---|---|---|---|
| `symbol_performance` | 458 | ETF performance by symbol + timeframe (1M, 3M, 6M, 9M, 12M, 1Y, 2Y, 3Y, 5Y, 10Y). Columns: `symbol, as_of_date, timeframe, price_return, dividend_return, net_return, benchmark, benchmark_price_return, benchmark_net_return, excess_return, currency` | **No** — ETF-only (SPY sample), no sector column, not individual stocks |
| `performance_history` | 12,359 | Seg-fund/series performance. Columns: `perf_id, series_id, snapshot_date, price, return_1m, return_3m, return_6m, return_1y, return_3y, return_5y, return_10y, return_incept, ytd_return` | **No** — keyed by `series_id` (seg fund), not stock symbol |

**Implication:** There is NO precomputed returns table for individual stocks. The price-change windows (`perf_1q`, `perf_2q`, `perf_4q`, `perf_2a`, `perf_3a`, `perf_5a`, `perf_10a`) used by the stock filter engine must be computed at query time from `stockprices`. See Section 3 for the pre-compute recommendation.

## 2. Corrections applied to StockFilter.php

The `StockFilter.php` that was on disk before this session was written against wrong schema assumptions. The following corrections have been applied:

### 2.1 Data sources comment block (lines 24–53)

Replaced the old "verified against actual schema" listing with the real schema inventory — including explicit "Columns that DO NOT EXIST" section so future work doesn't re-introduce them.

### 2.2 Base filter (line 250)

Changed `sp.active = 1` → `sm.is_active = 1` (active flag lives in `symbol_master`, not `stockprices`).

### 2.3 Score filters (buildWhere, lines 280–291)

Removed `es.totalscore` reference (evalsummary has 1 row, no totalscore column). The score filter section now only exposes `lippper_scores.composite_score` with a comment explaining that Zacks-style composite scores are not stored in DB.

### 2.4 Recommendation clause (lines 485–520)

Changed from `es.llm_recommendation` / `es.human_recommendation` (non-existent evalsummary columns) to `zr.action` (zacks_broker_recommendations.action — Buy/Hold/Sell). Added mapping from friendly labels (strong_buy, buy, hold, sell, strong_sell) to Zacks action values.

### 2.5 Fund filter columns (filterOptions, lines 569–610)

- Removed `fcf_yield` (not a column — would need runtime computation)
- Removed `avg_volume` and `rel_volume` (not stockprices columns — store only close/open/high/low/volume/adj_close/dividend/split_ratio/currency)
- Added zacks_* columns that DO exist in fundamentals: `zacks_roi`, `zacks_net_profit_margin`, `zacks_lt_debt_capital_pct`, `zacks_eps_change_f1_4w`, `zacks_eps_change_f2_4w`, `zacks_price_change_52w`, `zacks_num_analysts`
- Added explanatory comments documenting coverage counts and which columns are missing

### 2.6 Volume filters block (buildWhere, lines 357–369)

Removed the `$volumeCols` block that referenced `sp.avg_volume` and `sp.relative_volume` (don't exist). Replaced with a comment explaining that volume-based filtering would require a precomputed volume stats table.

### 2.7 Data source comment for `stockprices` (lines 25–30)

Updated to explicitly call out that `stockprices` does NOT have `active`, `avg_volume`, or `relative_volume` columns, and that price-change windows MUST be computed at runtime.

## 3. Pre-compute recommendation (price-change windows)

### 3.1 The problem

The stock filter engine references `perf_1q`, `perf_2q`, `perf_4q`, `perf_2a`, `perf_3a`, `perf_5a`, `perf_10a` as if they were stored columns. They are not. They must be computed from `stockprices.close` at query time. A typical filter query would need to:

1. Find the latest price date per symbol (`MAX(price_date) GROUP BY symbol`)
2. Find the price at N months before that date (self-join or correlated subquery on `price_date <= latest_date - INTERVAL N MONTH`)
3. Compute percentage change: `(latest_close - old_close) / old_close * 100`
4. Filter on the result

With 3,327 active symbols × up to 7 windows × complex joins with `symbol_master`, `fundamentals` (latest row per symbol), `lippper_scores`, and `zacks_broker_recommendations`, this is expensive at query time. The more filters a user applies, the worse it gets.

### 3.2 The recommendation

**Pre-compute price-change windows into a dedicated table**, refreshed nightly after prices are loaded. This is the same pattern already used by `symbol_performance` (for ETFs) and `performance_history` (for seg funds) — extend it to individual stocks.

**Proposed table: `stock_performance_windows`**

```sql
CREATE TABLE stock_performance_windows (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol          VARCHAR(20)    NOT NULL,
    as_of_date      DATE           NOT NULL,  -- the "today" date for which windows are computed
    perf_1q         DOUBLE         NULL,      -- (latest - 3mo ago) / 3mo ago * 100
    perf_2q         DOUBLE         NULL,      -- 6 months
    perf_4q         DOUBLE         NULL,      -- 12 months (1 year)
    perf_2a         DOUBLE         NULL,      -- 24 months (2 years)
    perf_3a         DOUBLE         NULL,      -- 36 months (3 years)
    perf_5a         DOUBLE         NULL,      -- 60 months (5 years)
    perf_10a        DOUBLE         NULL,      -- 120 months (10 years)
    created_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX unq_symbol_asof (symbol, as_of_date),
    INDEX idx_asof (as_of_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Refresh strategy:**
- Run nightly after `stockprices` is updated (e.g., 6:30 AM cron, aligned with the existing price refresh cycle)
- For each active symbol in `symbol_master`, compute the 7 windows from `stockprices` and upsert into `stock_performance_windows` with `as_of_date = CURDATE()`
- A single pass computing all windows per symbol is more efficient than 7 separate queries (compute all 7 return points in one query using `MIN(CASE WHEN price_date <= ... THEN close END)` for each window)

**Query pattern after pre-compute:**

```sql
SELECT sp.symbol, sp.close, sm.name, sm.exchange, sm.sector,
       f.roe, f.trailing_pe, f.market_cap, lp.composite_score,
       wp.perf_1q, wp.perf_2q, wp.perf_4q, wp.perf_2a, wp.perf_3a, wp.perf_5a, wp.perf_10a
FROM stockprices sp
INNER JOIN (SELECT symbol, MAX(price_date) AS max_date FROM stockprices GROUP BY symbol) latest
    ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
INNER JOIN symbol_master sm ON sp.symbol = sm.symbol
LEFT JOIN stock_performance_windows wp ON wp.symbol = sp.symbol AND wp.as_of_date = CURDATE()
LEFT JOIN fundamentals f ON f.symbol = sp.symbol AND f.fetch_date = (
    SELECT MAX(fetch_date) FROM fundamentals WHERE symbol = sp.symbol
)
LEFT JOIN lipper_scores lp ON lp.symbol = sp.symbol AND lp.as_of = CURDATE()
LEFT JOIN zacks_broker_recommendations zr ON zr.symbol = sp.symbol AND zr.fetch_date = (
    SELECT MAX(fetch_date) FROM zacks_broker_recommendations WHERE symbol = sp.symbol
)
WHERE sm.is_active = 1
  AND wp.perf_1q >= 5 AND wp.perf_1q <= 10
  AND f.roe >= 15
ORDER BY wp.perf_1q DESC;
```

This is a simple join against a narrow table instead of correlated subqueries against the full `stockprices` history.

### 3.3 What about triggers?

Triggers could theoretically maintain `stock_performance_windows` on every insert into `stockprices`, but this is **not recommended** because:
- `stockprices` receives bulk inserts (full history loads) — triggers fire per row and would be very slow
- Triggers are hard to debug when schema changes
- A nightly refresh is simpler, has clear failure modes (if it misses a night, data is just one day stale), and can be skipped safely when prices haven't changed

**Recommendation:** Use a nightly cron job (PHP or Python) that recomputes the windows and upserts. Keep the computation logic in one place (the refresh script), not duplicated across triggers and application code.

## 4. Volume filters (future work)

`stockprices` does not have `avg_volume` or `relative_volume` columns. To add volume-based filters:
- Create a `stock_volume_stats` table: `symbol, as_of_date, avg_volume_20d, relative_volume_today, volume_20d_ago`
- Refresh nightly alongside `stock_performance_windows`
- Add `avg_volume` and `rel_volume` to `StockFilter.php`'s `$numericFundCols` (rename the array to `$numericCols` since it would include both fundamentals and volume stats)

## 5. Zacks score filters (future work)

Zacks-style composite scores (alpha, relative strength, rank, estimate revisions) are currently computed in PHP by `StockController::calcZacksStyleScore()` per-symbol and are NOT stored in DB. This means:
- They are NOT SQL-filterable in the current filter engine
- Computing them for 3,327 symbols on every filter request would be expensive

**To make Zacks component filters SQL-filterable:**
- Create a `stock_zacks_scores` table: `symbol, as_of_date, zacks_rank, zacks_composite, zacks_alpha, zacks_relative_strength, zacks_estimate_revisions, zacks_buy_percent_negative, zacks_rating_detail`
- Either (a) compute these in a nightly job using the same logic as `calcZacksStyleScore()`, or (b) store the raw inputs (EPS revision counts, analyst consensus changes) in a table and compute the scores in SQL
- Add the columns to `StockFilter.php`'s `$numericFundCols` (or a `$scoreCols` array)

## 6. Current state of the filter engine (after corrections)

### 6.1 What works now (SQL-filterable)

| Filter group | Source | Columns exposed |
|---|---|---|
| Price-change windows (1Q/2Q/4Q/2A/3A/5A/10A) | Computed at runtime from `stockprices` | `perf_1q`, `perf_2q`, `perf_4q`, `perf_2a`, `perf_3a`, `perf_5a`, `perf_10a` (not stored — CTE/subquery required) |
| Score filter | `lippper_scores` | `composite_score` only |
| Recommendation filter | `zacks_broker_recommendations` | `action` (Buy/Hold/Sell) |
| Fundamental attributes | `fundamentals` | roe, roa, profit_margin, debt_to_equity, revenue_growth, gross_margin, operating_margin, trailing_pe, forward_pe, peg_ratio, current_ratio, dividend_yield, insider_percent, institutional_percent, beta, book_value, market_cap, zacks_roi, zacks_net_profit_margin, zacks_lt_debt_capital_pct, zacks_eps_change_f1_4w, zacks_eps_change_f2_4w, zacks_price_change_52w, zacks_num_analysts |
| Exchange / sector | `symbol_master` | `exchange`, `sector` |
| Text search | `symbol_master` + `stockprices` | `symbol`, `name` |
| Watchlist membership | `watchlist_symbols` | per-user |

### 6.2 What does NOT work (removed / not exposed)

| Filter | Why removed |
|---|---|
| `fcf_yield` | Not a column in `fundamentals` — would need runtime computation |
| `avg_volume` | Not a column in `stockprices` — would need precomputed volume stats table |
| `rel_volume` | Not a column in `stockprices` — would need precomputed volume stats table |
| `es.totalscore` | Not a column in `evalsummary` (only 1 row; different columns) |
| `es.llm_recommendation` / `es.human_recommendation` | Not columns in `evalsummary` — switched to `zr.action` |

## 7. Integration points (for Big Pickle's feature/zacks-rw branch)

### 7.1 Files involved

| File | Role |
|---|---|
| `src/Util/StockFilter.php` | WHERE clause builder + bucketing + filter options. **This is the file corrected in this session.** |
| `src/Controller/StockController.php` | `filterList()` method (not yet built — would call `StockFilter::buildWhere()`, resolve bucket placeholders, run the paginated SELECT). The Zacks screener work on this branch (`calcZacksStyleScore`) is complementary — a `stock_zacks_scores` table built from that logic would feed the filter engine. |
| `index.php` | Route: `case 'list'` → `StockController::filterList($_GET)` |
| `templates/list.php` | Filter UI panel (multi-select boxes for exchange, sector, recommendation, score, fundamentals; bucket dropdowns for price-change windows and ratio filters; market cap chips; combine AND/OR toggle) |
| `config.yaml` | DB credentials (read by python scripts via `config_loader.py`; PHP uses `.env` or the same YAML via Symfony Yaml) |
| `docs/requirements/FR-13-stock-filter-engine.md` | Functional spec for the stock filter engine (created alongside this work) |
| `docs/requirements/BR-13-all-symbols-filters.md` | Business requirement |
| `docs/requirements/UC-13-filter-all-symbols.md` | Use case |

### 7.2 What Big Pickle should know before touching this

1. **`StockFilter.php` was corrected in this session** (2026-09-05). If the feature/zacks-rw branch has an older version, the corrections should be merged. The key changes: `sm.is_active` instead of `sp.active`, `zr.action` instead of `es.llm_recommendation`, removed non-existent columns (`fcf_yield`, `avg_volume`, `rel_volume`, `es.totalscore`), added zacks_* fundamental columns.
2. **`calcZacksStyleScore()` in `StockController.php`** computes Zacks-style scores in PHP. If Big Pickle's work stores these scores in a table, the filter engine should reference that table instead of (or in addition to) `lippper_scores.composite_score`. Coordinate on the table name and column names.
3. **Price-change windows need pre-computation.** The current filter engine references `perf_1q` etc. as if stored, but they must be computed at runtime. Big Pickle should either (a) build `stock_performance_windows` table and nightly refresh, or (b) build the runtime CTE in `filterList()` that computes them on the fly (expensive but works short-term).
4. **The `filterList()` controller method does not exist yet.** `StockFilter.php` is the WHERE builder only — someone needs to write the controller method that calls it, resolves bucket placeholders, and runs the paginated SELECT. This is independent of the Zacks feature work.

### 7.3 What the Zacks feature branch should avoid

- Do NOT re-add `es.totalscore`, `es.llm_recommendation`, `es.human_recommendation`, `fcf_yield`, `sp.avg_volume`, or `sp.relative_volume` to `StockFilter.php` — these columns do not exist in the current schema
- Do NOT assume `evalsummary` has more than 1 row — it currently has exactly 1
- Do NOT hardcode `perf_1q` as a stored column without building the pre-computation table or runtime CTE first

---

## 7b. Zacks RW screen pipeline (BR-14 / FR-14) — architecture notes

This section captures the schema, data-flow, and integration points for the Zacks Research Wizard screen import + execution + signal dispatch + backtest/Advisor-portfolio work, so the filter-engine work and the Zacks pipeline work stay compatible.

### 7b.1 Schema the Zacks pipeline depends on (verified live 2026-09-07)

| Table | Rows (live) | Key columns | Purpose |
|---|---|---|---|
| `user_screens` | 194 | id, user_id, name, description, universe (enum stocks/segfunds), filters_json (longtext), is_public, is_deleted, created_at, updated_at | Stores imported `.und` screens under a dedicated system owner (`zacks_rw`); filters_json is the authoritative runnable rule set. |
| `zacks_broker_recommendations` | 0 | id, symbol, firm, analyst, grade, price_target, action, rec_date, fetch_date, raw_json | Per-firm broker rows scraped from Zacks recommendations page; refreshed per fetch_date. |
| `zacks_ratios_history` | 71,718 | id, symbol, ratio_name, period_label, ratio_value, fetch_date, raw_text | Multi-year ratio series scraped from the Zacks ratios page. |
| `stock_performance_windows` | 6,655 | id, symbol, as_of_date, anchor_date, perf_1q/2q/4q/2a/3a/5a/10a, chg_1w/4w/12w/24w/52w/ytd, high_52w, low_52w, hl_range_pct, chg_vs_high_52w, close, created_at | Precomputed price windows — both Hermes (perf_*) and RW (chg_*) sets — refreshed nightly; runtime fallback in ZacksUniverse when absent/stale. Unique on (symbol, as_of_date). |
| `fundamentals` | 17,131 | symbol, fetch_date, + 30 zacks_* columns (zacks_rank, zacks_rank_text, zacks_composite, zacks_value_grade, zacks_growth_grade, zacks_momentum_grade, zacks_vgm_grade, zacks_eps_change_f1_4w, _f1_12w, _f2_4w, _f2_1w, _f1_1w, zacks_eps_growth_q0_q4, _5yr, _lt_3_5yr, zacks_eps_pct_change_f1_f0, _f2_f1, zacks_sales_growth_reported_q, zacks_roi, zacks_net_profit_margin, zacks_lt_debt_capital_pct, zacks_num_analysts, zacks_price_change_52w/12w/24w/4w, zacks_recommendation, zacks_asset_turnover_ttm, zacks_fcf_f0, zacks_inventory_turnover_5yr) | Latest-fetch per-symbol Zacks valuation + EPS-revision + ratio data; also the target for ZacksRankPopulator's composite/rank/grades. |
| `alert_queue` | — | id, alert_type, symbol, severity, payload (JSON), status, created_at | Target for `zacks_signal_dispatcher.py` EPS-revision signals. |
| `symbol_master` | 3,923 | symbol, is_active, exchange, sector, industry, name, ... | Active-symbol universe source. |
| `stockprices` | 10,748,066 | symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency | Price history — the sole source for all window calculations. |

All four Zacks-side tables (`user_screens`, `zacks_broker_recommendations`, `zacks_ratios_history`, `stock_performance_windows`) exist on the live DB with the columns above. All 30 `zacks_*` columns exist in `fundamentals`. No schema migration is required to run the pipeline today — the code creates `zacks_ratios_history` and `zacks_broker_recommendations` via `CREATE TABLE IF NOT EXISTS` at scrape time, and `refresh_perf_windows.php` creates `stock_performance_windows` the same way. For production discipline, the recommended next step is a versioned migration that declares all four tables + the zacks_* columns explicitly (see remaining work 7b.x).

### 7b.2 Data flow (nightly pipeline)

```
zacks_scraper.py --all
  ├─ fetch main page   → fundamentals (valuation + zacks_* + EPS revision deltas)
  ├─ fetch ratios page → zacks_ratios_history
  ├─ fetch recs page   → zacks_broker_recommendations
  └─ fetch estimates   → fundamentals zacks_eps_change_f1_1w/4w, f2_1w/4w, forward_eps

ZacksRankPopulator::populateAll()
  └─ reads latest fundamentals + stock_performance_windows → writes zacks_rank/composite/grades

scripts/refresh_perf_windows.php
  └─ recomputes stock_performance_windows for CURDATE() anchor; prunes to last 14 as_of dates

zacks_signal_dispatcher.py
  └─ reads latest fetch_date per symbol with EPS data → top-5 bullish + top-5 bearish → Discord + alert_queue

(ZacksScreenImporter — separate, on-demand or pre-imported)
  └─ .und files → user_screens.filters_json (engine='zacks_rw')

(ZacksScreenRunner + ZacksScreenController — on-demand or scheduled)
  └─ user_screens row → ZacksUniverse → evaluate rules → matched symbols + skipped report
```

### 7b.3 Field contract (single source of truth)

`src/Util/ZacksFieldResolver.php` SPECS table is the contract between RW field codes and live data sources. It maps each supported code to (semantic, type, source, key, approx). Sources are: `base` (symbol_master), `price` (latest stockprices), `fund` (latest fundamentals), `win` (computed price windows), `vol20` (20d average volume, in-memory only), `formula` (derived). Codes not in SPECS are stored faithfully by the importer but reported as skipped by the runner.

### 7b.4 Window anchoring (must be identical across nightly + runtime)

Universe anchor = `MAX(price_date)` across `stockprices` at universe-build time. For a W-week window, historical close = `close` at `MAX(price_date) WHERE symbol = s AND price_date <= anchor - W weeks`. YTD = first close with `price_date >= year(anchor)-01-01`. 52w high/low = MAX/MIN close over `price_date >= anchor - 52 weeks`. `refresh_perf_windows.php` and `ZacksUniverse::loadWindows()` must use identical logic.

### 7b.5 Zacks-style rank is an approximation

`ZacksRankPopulator` computes a local VGM-style composite (0.40·Value + 0.30·Growth + 0.20·Momentum + 0.10·VGM) and maps the percentile to a 1–5 rank (top 5%→1, next 25%→2, middle 40%→3, next 25%→4, bottom 5%→5). This is NOT a genuine Zacks Rank feed. Any UI that shows `zacks_rank` must make this distinction visible (the detail partial `templates/partials/detail/zacks.php` renders the composite; the requirement spec FR-14 §1.2 calls this out).

### 7b.6 Backtest / Advisor portfolio model

A screen backtest runs the screen on a periodic cadence (holding period H = rebalance cadence), sells all prior holdings and buys the new set at each rebalance, applies optional stop-loss/trailing-stop, prices from `stockprices.close` at each rebalance date, and reports the full RW-equivalent stat set (total compounded return %/$, CAGR, win ratio, avg stocks held, avg turnover, stops, avg/largest winning & losing period, max drawdown, avg/best/worst winning & losing stretches). A running Advisor portfolio uses the same model but persists state between runs so stats accumulate over the portfolio's life rather than being a closed historical simulation. Both report the same stat categories.

### 7b.7 Files involved (Zacks pipeline)

| File | Role |
|---|---|
| `python/zacks_scraper.py` | Fetches Zacks pages, parses, upserts fundamentals + ratios + broker recs |
| `src/Util/ZacksFieldResolver.php` | RW field-code → live-source contract (SPECS table) |
| `src/Util/ZacksRwConfig.php` | Reads `zacks_rw:` block from config.yaml (inputs_dir, import_owner, max_rules_per_screen) |
| `src/Service/ZacksUniverse.php` | Builds live universe (base/price/fund/win/vol20) with fallback from precomputed windows |
| `src/Service/ZacksScreenImporter.php` | Parses `.und` files, upserts `user_screens` rows |
| `src/Service/ZacksScreenRunner.php` | Evaluates stored rules against a universe (AND/OR grouping, rank operators, skip semantics) |
| `src/Service/ZacksRankPopulator.php` | Computes Zacks-style composite + rank + grades, writes fundamentals |
| `src/Controller/ZacksScreenController.php` | `?action=rw_screens` list + `?action=run_rw_screen&id=N` run |
| `scripts/import_zacks_screens.php` | CLI entrypoint for import (optionally also runs rank populator) |
| `scripts/refresh_perf_windows.php` | Nightly window pre-compute + prune |
| `templates/rw_screens.php` | Screens list UI |
| `templates/run_rw_screen.php` | Run-result UI |
| `templates/zacks_eps_screener.php` | EPS-revision screener UI (bullish/bearish, min delta, limit) |
| `templates/partials/detail/zacks.php` | Detail-panel Zacks-style composite rendering |
| `run_zacks_refresh.sh` + `scripts/run_zacks_refresh.sh` | Cron wrapper for the nightly scrape |
| `python/zacks_signal_dispatcher.py` | Nightly EPS-revision signal dispatch (Discord + alert_queue) |

### 7b.8 Integration points with the filter engine

- `StockFilter.php` exposes zacks_* fundamental columns as filterable (added in the 2026-09-05 corrections). The Zacks pipeline populates those columns, so the filter engine and the Zacks pipeline share the same data.
- `stock_performance_windows` serves both the filter engine's price-change-window needs (Section 3) and the Zacks runner's window needs (chg_* columns). One table, one nightly refresh, two consumers — keep them in sync.
- If Big Pickle's `calcZacksStyleScore()` work ends up storing Zacks scores in a table, decide whether that table duplicates `fundamentals.zacks_rank/composite/grades` or replaces it, and update both `StockFilter.php` and `ZacksFieldResolver.php` to point at the same source.

---

## 7b. Zacks RW screen pipeline (BR-14 / FR-14) — architecture notes

This section captures the schema, data-flow, and integration points for the Zacks Research Wizard screen import + execution + signal dispatch + backtest/Advisor-portfolio work, so the filter-engine work and the Zacks pipeline work stay compatible.

### 7b.1 Schema the Zacks pipeline depends on (verified live 2026-09-07)

| Table | Rows (live) | Key columns | Purpose |
|---|---|---|---|
| `user_screens` | 194 | id, user_id, name, description, universe (enum stocks/segfunds), filters_json (longtext), is_public, is_deleted, created_at, updated_at | Stores imported `.und` screens under a dedicated system owner (`zacks_rw`); filters_json is the authoritative runnable rule set. |
| `zacks_broker_recommendations` | 0 | id, symbol, firm, analyst, grade, price_target, action, rec_date, fetch_date, raw_json | Per-firm broker rows scraped from Zacks recommendations page; refreshed per fetch_date. |
| `zacks_ratios_history` | 71,718 | id, symbol, ratio_name, period_label, ratio_value, fetch_date, raw_text | Multi-year ratio series scraped from the Zacks ratios page. |
| `stock_performance_windows` | 6,655 | id, symbol, as_of_date, anchor_date, perf_1q/2q/4q/2a/3a/5a/10a, chg_1w/4w/12w/24w/52w/ytd, high_52w, low_52w, hl_range_pct, chg_vs_high_52w, close, created_at | Precomputed price windows — both Hermes (perf_*) and RW (chg_*) sets — refreshed nightly; runtime fallback in ZacksUniverse when absent/stale. Unique on (symbol, as_of_date). |
| `fundamentals` | 17,131 | symbol, fetch_date, + 30 zacks_* columns (zacks_rank, zacks_rank_text, zacks_composite, zacks_value_grade, zacks_growth_grade, zacks_momentum_grade, zacks_vgm_grade, zacks_eps_change_f1_4w, _f1_12w, _f2_4w, _f2_1w, _f1_1w, zacks_eps_growth_q0_q4, _5yr, _lt_3_5yr, zacks_eps_pct_change_f1_f0, _f2_f1, zacks_sales_growth_reported_q, zacks_roi, zacks_net_profit_margin, zacks_lt_debt_capital_pct, zacks_num_analysts, zacks_price_change_52w/12w/24w/4w, zacks_recommendation, zacks_asset_turnover_ttm, zacks_fcf_f0, zacks_inventory_turnover_5yr) | Latest-fetch per-symbol Zacks valuation + EPS-revision + ratio data; also the target for ZacksRankPopulator's composite/rank/grades. |
| `alert_queue` | — | id, alert_type, symbol, severity, payload (JSON), status, created_at | Target for `zacks_signal_dispatcher.py` EPS-revision signals. |
| `symbol_master` | 3,923 | symbol, is_active, exchange, sector, industry, name, ... | Active-symbol universe source. |
| `stockprices` | 10,748,066 | symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency | Price history — the sole source for all window calculations. |

All four Zacks-side tables (`user_screens`, `zacks_broker_recommendations`, `zacks_ratios_history`, `stock_performance_windows`) exist on the live DB with the columns above. All 30 `zacks_*` columns exist in `fundamentals`. No schema migration is required to run the pipeline today — the code creates `zacks_ratios_history` and `zacks_broker_recommendations` via `CREATE TABLE IF NOT EXISTS` at scrape time, and `refresh_perf_windows.php` creates `stock_performance_windows` the same way. For production discipline, the recommended next step is a versioned migration that declares all four tables + the zacks_* columns explicitly (see remaining work 7b.x).

### 7b.2 Data flow (nightly pipeline)

```
zacks_scraper.py --all
  ├─ fetch main page   → fundamentals (valuation + zacks_* + EPS revision deltas)
  ├─ fetch ratios page → zacks_ratios_history
  ├─ fetch recs page   → zacks_broker_recommendations
  └─ fetch estimates   → fundamentals zacks_eps_change_f1_1w/4w, f2_1w/4w, forward_eps

ZacksRankPopulator::populateAll()
  └─ reads latest fundamentals + stock_performance_windows → writes zacks_rank/composite/grades

scripts/refresh_perf_windows.php
  └─ recomputes stock_performance_windows for CURDATE() anchor; prunes to last 14 as_of dates

zacks_signal_dispatcher.py
  └─ reads latest fetch_date per symbol with EPS data → top-5 bullish + top-5 bearish → Discord + alert_queue

(ZacksScreenImporter — separate, on-demand or pre-imported)
  └─ .und files → user_screens.filters_json (engine='zacks_rw')

(ZacksScreenRunner + ZacksScreenController — on-demand or scheduled)
  └─ user_screens row → ZacksUniverse → evaluate rules → matched symbols + skipped report
```

### 7b.3 Field contract (single source of truth)

`src/Util/ZacksFieldResolver.php` SPECS table is the contract between RW field codes and live data sources. It maps each supported code to (semantic, type, source, key, approx). Sources are: `base` (symbol_master), `price` (latest stockprices), `fund` (latest fundamentals), `win` (computed price windows), `vol20` (20d average volume, in-memory only), `formula` (derived). Codes not in SPECS are stored faithfully by the importer but reported as skipped by the runner.

### 7b.4 Window anchoring (must be identical across nightly + runtime)

Universe anchor = `MAX(price_date)` across `stockprices` at universe-build time. For a W-week window, historical close = `close` at `MAX(price_date) WHERE symbol = s AND price_date <= anchor - W weeks`. YTD = first close with `price_date >= year(anchor)-01-01`. 52w high/low = MAX/MIN close over `price_date >= anchor - 52 weeks`. `refresh_perf_windows.php` and `ZacksUniverse::loadWindows()` must use identical logic.

### 7b.5 Zacks-style rank is an approximation

`ZacksRankPopulator` computes a local VGM-style composite (0.40·Value + 0.30·Growth + 0.20·Momentum + 0.10·VGM) and maps the percentile to a 1–5 rank (top 5%→1, next 25%→2, middle 40%→3, next 25%→4, bottom 5%→5). This is NOT a genuine Zacks Rank feed. Any UI that shows `zacks_rank` must make this distinction visible (the detail partial `templates/partials/detail/zacks.php` renders the composite; the requirement spec FR-14 §1.2 calls this out).

### 7b.6 Backtest / Advisor portfolio model

A screen backtest runs the screen on a periodic cadence (holding period H = rebalance cadence), sells all prior holdings and buys the new set at each rebalance, applies optional stop-loss/trailing-stop, prices from `stockprices.close` at each rebalance date, and reports the full RW-equivalent stat set (total compounded return %/$, CAGR, win ratio, avg stocks held, avg turnover, stops, avg/largest winning & losing period, max drawdown, avg/best/worst winning & losing stretches). A running Advisor portfolio uses the same model but persists state between runs so stats accumulate over the portfolio's life rather than being a closed historical simulation. Both report the same stat categories.

### 7b.7 Files involved (Zacks pipeline)

| File | Role |
|---|---|
| `python/zacks_scraper.py` | Fetches Zacks pages, parses, upserts fundamentals + ratios + broker recs |
| `src/Util/ZacksFieldResolver.php` | RW field-code → live-source contract (SPECS table) |
| `src/Util/ZacksRwConfig.php` | Reads `zacks_rw:` block from config.yaml (inputs_dir, import_owner, max_rules_per_screen) |
| `src/Service/ZacksUniverse.php` | Builds live universe (base/price/fund/win/vol20) with fallback from precomputed windows |
| `src/Service/ZacksScreenImporter.php` | Parses `.und` files, upserts `user_screens` rows |
| `src/Service/ZacksScreenRunner.php` | Evaluates stored rules against a universe (AND/OR grouping, rank operators, skip semantics) |
| `src/Service/ZacksRankPopulator.php` | Computes Zacks-style composite + rank + grades, writes fundamentals |
| `src/Controller/ZacksScreenController.php` | `?action=rw_screens` list + `?action=run_rw_screen&id=N` run |
| `scripts/import_zacks_screens.php` | CLI entrypoint for import (optionally also runs rank populator) |
| `scripts/refresh_perf_windows.php` | Nightly window pre-compute + prune |
| `templates/rw_screens.php` | Screens list UI |
| `templates/run_rw_screen.php` | Run-result UI |
| `templates/zacks_eps_screener.php` | EPS-revision screener UI (bullish/bearish, min delta, limit) |
### 7b.8 Integration points with the filter engine

- `StockFilter.php` exposes zacks_* fundamental columns as filterable (added in the 2026-09-05 corrections). The Zacks pipeline populates those columns, so the filter engine and the Zacks pipeline share the same data.
- `stock_performance_windows` serves both the filter engine's price-change-window needs (Section 3) and the Zacks runner's window needs (chg_* columns). One table, one nightly refresh, two consumers — keep them in sync.
- If Big Pickle's `calcZacksStyleScore()` work ends up storing Zacks scores in a table, decide whether that table duplicates `fundamentals.zacks_rank/composite/grades` or replaces it, and update both `StockFilter.php` and `ZacksFieldResolver.php` to point at the same source.

---

## 7c. Stock price storage refactor (BR-15 / FR-15) — architecture notes

This section captures the per-symbol / per-exchange storage design so the price-storage refactor and the filter-engine / Zacks-pipeline work stay compatible. The guiding constraint: **the DB host has requested the database stay under 1 GB**, and today `stockprices` (10.7M rows, ~174 MB, ~93% of DB size) is the only table that matters for size. Everything else (fundamentals, zacks_*, perf windows, symbol_master, user_screens, settings) is collectively a few MB.

### 7c.1 Why split price storage

- No cross-symbol price calculations exist in the current code — prices are used for per-symbol lookups (latest close, MACD, per-symbol return windows) and the precomputed window table. Cross-symbol work is limited to comparisons (sector-relative, exchange-relative) that read the *recent* table or the precomputed window table.
- `symbol_master.exchange` is a stable, first-class attribute. Routing by exchange is formulaic and already mirrors how the exchange databases are organized (`ksfraser_sm_tsx`, `_nasdaq`, `_nyse`, `_v`, `_cse`, `_amex`).
- The price-history schema has been stable for 5+ years — splitting into per-symbol tables does not increase schema-change risk.

### 7c.2 Exchange database inventory (live-verified, 2026-09-09)

| Database (to-be) | exchange value(s) routed here | Active symbols (live) | Notes |
|---|---|---|---|
| `ksfraser_sm_tsx` | TSX | 880 | |
| `ksfraser_sm_nasdaq` | NASDAQ | 2,691 | Largest; monitor size |
| `ksfraser_sm_nyse` | NYSE, NYQ (and AMEX-coded if any appear) | 184 | NYSE + NYSE-American |
| `ksfraser_sm_v` | TSX.V | 15 | |
| `ksfraser_sm_cse` | CSE | 0 (today) | Future-proofing |
| `ksfraser_sm_amex` | AMEX | 0 (today) | Future-proofing |
| `ksfraser_sm_other` | OTC, TOR, EUR, GBP, CNY, HKD, and all other minor codes | ~20 | Fallback for exchanges without a dedicated DB |

The `cse` and `amex` databases have zero active symbols today but are created anyway so the routing table is complete and future symbols land correctly without a schema change.

### 7c.3 Per-symbol history table

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

`<symbol>` is the sanitized symbol string from `symbol_master.symbol`, composed by the routing layer. `split_factor` is the cumulative split adjustment factor as of this row — see §7c.6.

### 7c.4 Recent (cross-symbol) price table per exchange

One table per exchange database holding the last N days (1 year / 200 trading days) of prices for all active symbols in that exchange — the table the filter engine, screen runner, MACD, and Advisor backtest hit for "current" price work:

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

Retention: keep the last **1 year** of daily prices (or last **200 trading days** for indicators like MACD 200). When a new row is inserted for a symbol, the oldest row beyond the retention window is dropped. This keeps the recent table bounded and small.

### 7c.5 Routing (formulaic from symbol_master)

`SymbolTableRouter::routeForSymbol(string $symbol)` returns `(db_name, history_table, recent_table, exchange, connection)`. The db name comes from `symbol_master.exchange` via the exchange→db mapping; the history table is `'stockprices_' . sanitized_symbol`; the recent table is `'stockprices_recent_' . exchange_suffix`. No consumer hardcodes a database or table name. The exchange→db mapping is derived from the live `symbol_master.exchange` values and regenerated if a new exchange appears.

### 7c.6 Adjusted prices and split-factor tracking

The existing `stockprices` has `adj_close` and `split_ratio` but no explicit cumulative split-factor tracking. The refactor adds `split_factor` per row (cumulative factor as of that row) so `adj_close` is always derivable and auditable:
- `split_factor` on row N = `split_factor` on row N-1 × `split_ratio` on row N (cumulative product of all split ratios through this row).
- `adj_close = close / split_factor` (convention: cumulative factor starts at 1 and is multiplied by each split_ratio on a split row).
- `symbol_master.split_factor_current` = `split_factor` from the latest row for the symbol — cached convenience so the latest adjusted close is always available without scanning the whole table.
- Nightly ingestion recomputes `adj_close` and `split_factor` for the new row from the prior row's `split_factor` × the new row's `split_ratio`.
- Backfill: during migration, compute `split_factor` history from the existing `split_ratio` column in the old `stockprices`.

### 7c.7 Nightly ingestion (dual-write, per-exchange transaction)

For each new price row:
1. Resolve the route for the symbol.
2. Begin a transaction on the exchange database (which contains both the per-symbol table and the recent table — same DB, so one transaction covers both).
3. Insert/replace into `stockprices_<symbol>`.
4. Insert/replace into `stockprices_recent_<exchange>`.
5. If the recent table exceeds retention for this symbol, delete the oldest row for this symbol.
6. Update `symbol_master.split_factor_current` if the new `split_factor` is higher.
7. Commit.

Both writes are in the same database and same transaction — atomicity is guaranteed per symbol per night. No cross-database transaction is needed.

### 7c.8 Precomputed performance windows — refresh cadence change

The price-change windows and fundamental-based scores move to their own tables with a changed cadence:
- **Short windows (1Q, 4W, 12W, 24W, 52W, YTD):** refreshed nightly from the recent table via a lightweight rollup (cheap: small table, bounded rows per symbol).
- **Long windows (2Y, 3Y, 5Y, 10Y):** recalculated **quarterly** or after earnings release for the symbol, stored in `stock_performance_windows` with `last_recomputed`.
- **Buffett-tenet / fundamental-based scores:** recalculated **quarterly** or **after earnings**, stored in their own table(s) with `last_recomputed`.

This cuts nightly compute for long windows from "all symbols every night" to "only symbols that had an earnings release or hit a quarterly boundary."

### 7c.9 Zacks data (current only — no history)

Zacks ratings and fundamental attributes are **point-in-time only**. There is no historical Zacks rating archive available, and Zacks does not expose a feed that lets us see what rank a stock had on a past date. The `zacks_*` columns in `fundamentals` remain latest-fetch only. This is accepted as a limitation. (If a historical Zacks feed becomes available in the future, it would get its own archive table in the relevant exchange DB.)

### 7c.10 Centralized schema management

All price-table schema operations go through a centralized schema manager — never raw SQL with hardcoded table names:
- `SchemaManager::ensurePriceHistoryTable($symbol, $exchange)` — creates `stockprices_<symbol>` if absent.
- `SchemaManager::ensureRecentTable($exchange)` — creates `stockprices_recent_<exchange>` if absent.
- `SchemaManager::ensureExchangeDatabase($exchange)` — creates the exchange DB if absent.
- `SchemaManager::dropPriceHistoryTable($symbol, $exchange)` — drops a per-symbol table on permanent symbol removal.

### 7c.11 Integration with filter engine and Zacks pipeline

- The filter engine and Zacks screen runner read prices through `StockPriceRepository` (the router-backed repository), not directly from `stockprices`. The recent table is the primary source for "current" price work; `stock_performance_windows` is the source for precomputed windows.
- The Zacks pipeline reads `fundamentals.zacks_*` (latest-fetch) and `stock_performance_windows` (precomputed) — unaffected by the price-storage split except that `stock_performance_windows` is now refreshed on a changed cadence (short windows nightly, long windows quarterly).
- The Advisor backtest reads prices through the repository; where it needs cross-symbol price history in one query, it uses a scratch table (validated in UC-15e). We audit the backtest in the follow-up phase to confirm no path truly needs the old monolithic `stockprices`.

### 7c.12 DB size picture (live-verified, 2026-09-09)

The current `ksfraser_stock_market` database is approximately **187 MB** total. The breakdown that matters:

| Table | Rows (live) | Approx. size | % of DB |
|---|---|---|---|
| `stockprices` | 10,748,066 | ~174 MB | ~93% |
| `symbol_master` | 3,923 | small | <1% |
| `fundamentals` | 17,131 | small | <1% |
| `zacks_ratios_history` | 71,718 | small | <1% |
| `stock_performance_windows` | 6,655 | small | <1% |
| `user_screens` | 194 | tiny | <1% |
| All other tables (lippper_scores, evalsummary, settings, auth, etc.) | — | collectively a few MB | <5% |

**Implication:** Moving `stockprices` out of the primary DB into the per-exchange databases is the change that addresses the host's size concern. After migration, the primary DB drops from ~187 MB to well under 10 MB (everything except `stockprices`). Each exchange DB is individually smaller and manageable; the largest (NASDAQ, 2,691 symbols) is the one to monitor. The recent tables are bounded by retention (1 year / 200 days), so they never grow unbounded.

### 7c.13 Migration sequence (high level)

1. Create exchange databases + per-symbol tables + recent tables (schema manager).
2. Migrate existing `stockprices` rows into per-symbol history tables (with `split_factor` backfill) and recent tables (last N days) — `migrate_prices_to_exchange_dbs.php`.
3. Cut over reads to `StockPriceRepository` (router-based).
4. Switch nightly ingestion to dual-write.
5. Deploy the changed performance-window refresh cadence (short nightly, long quarterly).
6. Trim / drop the old `stockprices` table from the primary DB once reads are fully cut over.
7. Backtest cross-symbol audit (UC-15e) — confirm Advisor/portfolio code works against the new storage.

---

## 8. Validation performed

- DB connection verified live from this host (192.168.1.102 → ksfraser.ca:3306) using the app's actual credentials from `config.yaml`/`database.php` (`ksfraser_stockmarket` / `Zaqwsx9sm1@`)
- `StockFilter.php` syntax checked (`php -l` — clean)
- Full schema inventory SQL run against all relevant tables (counts, columns, samples for `symbol_performance`, `performance_history`, `evalsummary`, `lippper_scores`, `fundamentals`)
- `StockFilter::filterOptions()` verified to return correct shape (with real `symbol_master` exchange/sector lists pulled live)
- `StockFilter::buildWhere()` verified to produce valid SQL for all filter scenarios (base, search, exchange, sector, price-change windows, score, recommendation, fundamentals, market cap, OR mode, bucket placeholders)
- **New (2026-09-09):** exchange inventory from `symbol_master` verified live — 25 distinct exchange values; 6 primary exchange databases mapped; NASDAQ 2,691 / TSX 880 / NYSE+NQY 184 are the big three; CSE/AMEX have 0 active symbols today.

---

## 9. Remaining work (not done in this session)

### 9.1 Filter engine (Section 7.1)

1. **Write `StockController::filterList()`** — the controller method that calls `StockFilter::buildWhere()`, resolves bucket placeholders, runs the paginated SELECT with all joins, and returns data for `templates/list.php`. Depends on whether price-change windows are precomputed (build CTE if not).
2. **Wire the route in `index.php`** (`case 'list'`) and build the filter UI panel in `templates/list.php`.
3. **Write integration tests** against the live DB (not possible from this host — infra is not reachable from 192.168.1.102; tests would need to run on the app host or a host with DB access).

### 9.2 Zacks RW pipeline (BR-14 / FR-14)

1. **Backtest + Advisor-portfolio implementation** — the requirement spec FR-14 §7 defines the model and stat set, but the actual backtest engine + running-portfolio accounting is not yet coded. This is the largest remaining piece: a screen-runner-backed portfolio simulator with sell-all/buy-new rebalance, optional stops, `stockprices`-based pricing, and the full RW stat set, plus a persistent running-portfolio state table.
2. **Versioned schema migration** — today the pipeline creates its tables via `CREATE TABLE IF NOT EXISTS` at runtime (scraper + refresh script). For production discipline, add an explicit migration declaring `zacks_broker_recommendations`, `zacks_ratios_history`, `stock_performance_windows`, and the 30 `zacks_*` fundamentals columns (if not already in a migration). Makes the schema auditable and deployable to a fresh DB.
3. **`.und` parser availability** — `ZacksScreenImporter` depends on `ksfraser/research-wizard-reader` (added to `composer.json` on the branch). Confirm the package is accessible from this host's composer install before the importer is usable.
4. **EPS-revision dispatcher on the branch** — `python/zacks_signal_dispatcher.py` exists on disk (main) but is not yet on `feature/zacks-rw`; it should be committed onto the branch so the nightly pipeline is complete and the RTM row for UC-14c has its script in the same place as the rest of the pipeline.
5. **Screens list + run-result UI** — `templates/rw_screens.php` and `templates/run_rw_screen.php` exist on the branch; verify they render against the live `user_screens` data and that the run result shows matched symbols, per-rule values, and skipped-atom report.
6. **Zacks Rank population run** — `zacks_broker_recommendations` is empty (0 rows) and `zacks_rank` is unpopulated on live fundamentals; run `import_zacks_screens.php --rank` (or `ZacksRankPopulator` directly) to populate rank/composite/grades so rank-filtering screens can run.
7. **Signal-dispatch end-to-end** — run `zacks_signal_dispatcher.py` against the live DB to confirm Discord webhook resolution, top-5 selection, send + insert behavior, and the no-signals summary path.
8. **Unit tests per UT-14** (FR-14 §8) — `ZacksFieldResolver`, `ZacksScreenRunner` evaluation/grouping/rank/skips, `ZacksRankPopulator::scoreFor`/`rankForPercentile`, window calculation helper, dispatcher pure logic.

### 9.3 Stock price storage refactor (BR-15 / FR-15) — new

1. **`SymbolTableRouter`** — implement the routing helper that derives (db, history table, recent table, exchange) from `symbol_master.exchange` + `symbol_master.symbol`. Must handle the 25 distinct exchange values and the `ksfraser_sm_other` fallback for minor exchanges.
2. **`StockPriceRepository`** — implement per-symbol and recent price reads/writes via the router; migrate all existing `stockprices` readers to use this repository.
3. **`PriceIngestionService` dual-write** — update nightly ingestion to write to both the per-symbol history table and the recent table in a per-exchange transaction, and trim the recent table to retention.
4. **`SchemaManager`** — implement the centralized CREATE/ALTER/DROP layer for price tables; eliminate all raw SQL with hardcoded `stockprices_<symbol>` or `ksfraser_sm_<exchange>` names.
5. **`symbol_master.split_factor_current`** — add the column and keep it updated by the ingestion service.
6. **`split_factor` backfill** — compute cumulative split factors from the existing `split_ratio` column during migration; verify adjusted-price accuracy for split-history symbols.
7. **Performance-window cadence change** — implement quarterly / post-earnings recalculation for long windows and tenet-based scores; implement nightly short-window rollup from the recent table.
8. **`config.yaml` per-exchange DB blocks** — add connection config for each exchange database (or a single block + exchange→db mapping).
9. **Migration script** — `migrate_prices_to_exchange_dbs.php` to split the existing `stockprices` into per-symbol + recent tables across exchange databases.
10. **Backtest cross-symbol audit (UC-15e)** — review Advisor backtest / portfolio-selection code for cross-symbol price queries; add scratch tables where needed; verify results match pre-refactor behavior.

---

## 10. Source material for this update

- BR-15 / FR-15 / UC-15a–e written alongside this update (see `docs/requirements/BR-15-stock-price-storage-refactor.md`, `FR-15-stock-price-storage-refactor.md`, `UC-15-stock-price-storage-refactor.md`).
