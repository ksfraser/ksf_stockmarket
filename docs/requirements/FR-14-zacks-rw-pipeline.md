# Functional Requirement FR-14: Zacks RW Data Pipeline, Schema, Field Contract, and Calculations

## 1. Data sources

### 1.1 Downloaded (Zacks public pages)

The pipeline fetches four report pages per symbol from `https://ica.zacks.com/report.php`:

| Page type | URL param | What it carries | Stored where |
|---|---|---|---|
| Main valuation | `?t={sym}&type=main` | Valuation multiples (P/E TTM/F1, PEG, P/B, P/S, BVPS), EPS (trailing, consensus F1), shares outstanding, market cap, profitability (gross/operating/net margin, ROE, ROA, ROI), leverage/liquidity (D/E, current/quick ratio, LT debt/capital, asset turnover), dividend (yield, payout), beta, short ratio, insider/institutional %, industry label, analyst count, average recommendation label | `fundamentals` (zacks_* columns + valuation fundamentals columns) |
| Ratios history | `?t={sym}&type=ratios` | Multi-year ratio series (ROE, ROA, ROI, margins, P/B, P/E, P/S, P/CF, BVPS, current/quick, D/E, leverage, inventory turnover, sales/inventory) | `zacks_ratios_history` |
| Recommendations | `?t={sym}&type=recommendations` | Per-firm broker rows (firm, analyst, grade, price target, action, rec date) | `zacks_broker_recommendations` |
| Estimates | `?t={sym}&type=estimates` | Consensus EPS averages today, 7 days ago, 30 days ago (F1 and F2), from which 1w/4w deltas are derived | `fundamentals` (zacks_eps_change_f1_1w/4w/12w, zacks_eps_change_f2_1w/4w, forward_eps) |

**Source field → stored column contract** is defined in `src/Util/ZacksFieldResolver.php` (the SPECS table). Every RW field code the importer may encounter is either:
- mapped to a live source (one of `base` / `price` / `fund` / `win` / `vol20` / `formula`) with an explicit dataset key, or
- absent from SPECS, in which case the importer still stores the rule faithfully but the runner reports it as skipped.

**Approximation contract**: when `approx = true` in SPECS, the binding is a known approximation of the RW semantic (e.g. `eps_12m` ← `trailing_eps`; `eps_revision_q1_4w` ← `zacks_eps_change_f1_4w`; `price_cash_flow` ← `price_to_sales`), and the runner/execution output must make clear which values are approximate where that matters to a user reading results. The detail-panel partial `templates/partials/detail/zacks.php` renders the computed Zacks-style composite, not a claim of a genuine Zacks Rank.

### 1.2 Calculated

| Derived value | Where computed | Inputs | Stored / cached |
|---|---|---|---|
| Price-change windows (Hermes set) | `scripts/refresh_perf_windows.php` nightly + `ZacksUniverse::loadWindows()` runtime fallback | `stockprices.close` anchored to universe MAX price_date; offsets 13/26/52/104/156/260/520 weeks; YTD from first close of anchor year | `stock_performance_windows` (perf_1q/2q/4q/2a/3a/5a/10a) |
| Price-change windows (RW set) | same two paths as above | same price history; offsets 1/4/12/24/52 weeks; 52w high/low/range; chg_vs_high_52w; chg_ytd | `stock_performance_windows` (chg_1w/4w/12w/24w/52w/ytd, high_52w, low_52w, hl_range_pct, chg_vs_high_52w) |
| 20-trading-day average volume | `ZacksUniverse::loadVol20()` on demand | `stockprices.volume` over trailing 20 trading days from anchor | in-memory only in the universe row (vol20), not persisted |
| EPS revision deltas (1w/4w) | `zacks_scraper.py::_parse_estimates()` at scrape time | Estimates-page consensus averages (today vs 7d ago vs 30d ago) | `fundamentals` (zacks_eps_change_f1_1w, zacks_eps_change_f1_4w, zacks_eps_change_f2_1w, zacks_eps_change_f2_4w) |
| Zacks-style composite + rank + grades | `ZacksRankPopulator::scoreFor()` + `populateAll()` | latest fundamentals row (trailing_pe, price_to_book, free_cash_flow, market_cap, debt_to_equity, earnings_growth, revenue_growth, roe) + computed windows (chg_vs_high_52w, chg_4w) + latest close | `fundamentals` (zacks_rank, zacks_rank_text, zacks_composite, zacks_value_grade, zacks_growth_grade, zacks_momentum_grade, zacks_vgm_grade) |

**Window anchoring semantics (must hold for both nightly and runtime path)**:
- Universe anchor = `MAX(price_date)` across `stockprices` at the time the universe is built.
- For a W-week window, historical close = `close` at `MAX(price_date) WHERE price_date <= anchor - W weeks`, per symbol.
- YTD: first close with `price_date >= anchor_year-01-01`.
- 52w high/low: `MAX(close)` / `MIN(close)` over `price_date >= anchor - 52 weeks`.
- Both `refresh_perf_windows.php` and `ZacksUniverse::loadWindows()` use exactly this logic, so the precomputed table and the runtime fallback are interchangeable.

**Rank populator is an approximation, not a Zacks Rank feed**:
- Composite = 0.40·Value + 0.30·Growth + 0.20·Momentum + 0.10·VGM, each a 0–100 sub-score.
- Value (40 max): trailing PE (<15/<20/<30 bands), P/B (<1/<2/<3 bands), FCF yield (>6%/>3%/>1%), D/E (<0.3/<0.8/<1.5 bands).
- Growth (30 max): earnings_growth (>20%/>10%/>0 bands), revenue_growth (>15%/>5%/>0 bands).
- Momentum (20 max): chg_vs_high_52w (>=95/>=85/>=70/>=50 bands) + chg_4w (>10/>5/>0/>-5 bands).
- Rank = percentile band over the scored universe: top 5% → 1, next 25% → 2, middle 40% → 3, next 25% → 4, bottom 5% → 5. Text labels: Strong Buy / Buy / Hold / Sell / Strong Sell.
- This must be described to users as a local composite that mimics Zacks Rank distribution, not the genuine Zacks Rank. Acceptance: the detail panel and any screen output that surfaces `zacks_rank` make that distinction visible (see template partial and UC-14a).

## 2. Schema (required tables and columns)

### 2.1 `user_screens` (screen definitions)

Stores imported RW screens. Must exist with at least:

| Column | Type | Meaning |
|---|---|---|
| id | int PK | screen row id |
| user_id | int FK → users.id | owner (system importer user for RW screens) |
| name | varchar(120) | screen name (filename-derived, trimmed) |
| description | varchar(500) | human-readable output description (rule count, custom-formula count, source) |
| universe | enum('stocks','segfunds') | 'stocks' for RW screens |
| filters_json | longtext | authoritative serialized rule atoms (engine='zacks_rw', version, source_file, report, parsed_at, rules[]) |
| is_public | tinyint | visibility flag |
| is_deleted | tinyint | soft-delete |
| created_at / updated_at | timestamp | audit |

Acceptance: `user_screens` must contain a row for every imported `.und` screen, keyed for upsert on (user_id, universe='stocks', name). The `filters_json` payload must be sufficient to re-run the screen without the original file.

### 2.2 `zacks_broker_recommendations` (per-firm broker rows)

| Column | Type | Meaning |
|---|---|---|
| id | bigint PK | |
| symbol | varchar(20) | our symbol |
| firm | varchar(100) | broker firm name |
| analyst | varchar(100) | analyst (if present) |
| grade | varchar(10) | firm's grade label |
| price_target | double | target price (if parsed) |
| action | varchar(50) | Buy/Hold/Sell-style action |
| rec_date | date | recommendation date (if parsed) |
| fetch_date | date | scrape date |
| raw_json | text | raw cell array for audit/reparse |

Acceptance: the table exists and is populated by `zacks_scraper.py` whenever a recommendations page yields broker rows; a symbol's rows are refreshed (delete+reinsert) per fetch_date so the table reflects the latest scrape, not an append-only history.

### 2.3 `zacks_ratios_history` (ratio time series)

| Column | Type | Meaning |
|---|---|---|
| id | bigint PK | |
| symbol | varchar(20) | |
| ratio_name | varchar(80) | e.g. "Return on Equity" |
| period_label | varchar(20) | current / year-1 / year-2 / year-3 |
| ratio_value | double | parsed ratio value |
| fetch_date | date | scrape date |
| raw_text | text | raw matched text for audit |

Acceptance: the table exists and is populated by `zacks_scraper.py` from the ratios page; rows for the same (symbol, fetch_date) replace prior rows for that scrape.

### 2.4 `stock_performance_windows` (precomputed price windows)

| Column | Type | Meaning |
|---|---|---|
| id | bigint unsigned PK | |
| symbol | varchar(20) | |
| as_of_date | date | "today" for which windows were computed |
| anchor_date | date | universe MAX price_date used as the window anchor |
| perf_1q/2q/4q/2a/3a/5a/10a | double | Hermes windows: (close - past_close)/past_close*100 for 3/6/12/24/36/60/120-month offsets |
| chg_1w/4w/12w/24w/52w | double | RW windows: same formula for 1/4/12/24/52-week offsets |
| chg_ytd | double | YTD % change vs first close of anchor year |
| high_52w / low_52w | double | 52-week high/low close |
| hl_range_pct | double | position in 52w range = (close - low)/(high - low)*100 |
| chg_vs_high_52w | double | close/high_52w*100 |
| close | double | latest close (anchored) |
| created_at | timestamp | audit |

Unique index on (symbol, as_of_date). Index on as_of_date. Pruned to the last 14 as_of_dates by the refresh script.

Acceptance: the table exists, is refreshed nightly after prices load, and the stored anchor_date matches the universe anchor at run time (so `ZacksUniverse::loadPrecomputedWindows()` can use it); when it doesn't match or the table is absent, `ZacksUniverse::loadWindows()` computes the same values at runtime from `stockprices`.

### 2.5 `fundamentals` (zacks_* columns)

The existing `fundamentals` table (keyed by symbol + fetch_date) must contain, at minimum, all columns listed in Section 1.1's "Main valuation" row plus the EPS-revision columns, plus the rank/composite/grade columns listed in 1.2. Verified present on the live DB (30 zacks_* columns). The scraper upserts these per symbol per fetch_date.

Acceptance: every field a stored screen rule can reference via ZacksFieldResolver must have a live column or a documented calculation path. Fields absent from SPECS are allowed only when the runner explicitly reports them as skipped.

### 2.6 `alert_queue` (signal dispatch target)

Must support inserts with the payload shape produced by `zacks_signal_dispatcher.py`:
- id (varchar, e.g. `zacks-{symbol}-{YYYYMMDDHHMMSS}`)
- alert_type (e.g. `zacks_eps_revision`)
- symbol
- severity (e.g. `high`)
- payload (JSON: symbol, change_value, direction, forward_eps, message)
- status (e.g. `pending`)
- created_at (datetime)

Acceptance: the dispatcher inserts one row per dispatched signal and the row round-trips the full signal context.

## 3. Calculations (operational definitions)

All calculations below are the canonical definitions; the code in `refresh_perf_windows.php`, `ZacksUniverse`, `ZacksRankPopulator`, and `zacks_scraper.py` must match them.

### 3.1 Price change % for window W (weeks or months)

For symbol s, anchor A = universe MAX price_date:
- past_close(s, A, W) = close at MAX(price_date) WHERE symbol = s AND price_date <= A - W
- chg(s, W) = (close_at(A) - past_close(s, A, W)) / past_close(s, A, W) * 100, or NULL if past_close missing/zero

For month-based Hermes windows, W is expressed in weeks (13/26/52/104/156/260/520). For YTD, past_close = first close with price_date >= year(A)-01-01.

### 3.2 52-week range position

- high_52w(s) = MAX(close) WHERE symbol = s AND price_date >= A - 52 weeks
- low_52w(s) = MIN(close) WHERE symbol = s AND price_date >= A - 52 weeks
- hl_range_pct = (close_at(A) - low_52w) / (high_52w - low_52w) * 100, NULL if high == low
- chg_vs_high_52w = close_at(A) / high_52w * 100

### 3.3 20-day average volume

- vol20(s) = average of volume over the trailing 20 trading-day price_date rows for symbol s up to and including A. Computed in memory by ZacksUniverse only when a screen rule references field code 22 (avg_volume_20d).

### 3.4 EPS revision delta

- zacks_eps_change_f1_4w = f1_consensus_today - f1_consensus_30d_ago (from estimates page)
- zacks_eps_change_f1_1w = f1_consensus_today - f1_consensus_7d_ago
- same pattern for F2 → zacks_eps_change_f2_4w / f2_1w
- NULL when either consensus value is missing

### 3.5 Zacks-style composite and rank

Defined in Section 1.2. Acceptance: the composite is a 0–100 number; rank is an integer 1–5 with labels; grades are A/B/C/D/F per 90/80/70/60 thresholds; the rank distribution across the active scored universe must be computable from `fundamentals.zacks_rank`.

## 4. Screen import contract

### 4.1 Input

- Directory of `.und` files (configured via `config.yaml zacks_rw.inputs_dir`, overrideable via env `RW_INPUTS_DIR` and CLI `--dir`).
- Each file is parsed by `UndParser` (from `ksfraser/research-wizard-reader`) into screen name, report path, and rule atoms.

### 4.2 Storage

- Owner: a dedicated system user named by `config.yaml zacks_rw.import_owner` (default `zacks_rw`), created on demand if absent.
- One `user_screens` row per screen, universe = `stocks`, upserted on (owner, name). `filters_json` is the authoritative runnable representation; `description` summarizes rule count and any custom-formula count.

### 4.3 Idempotency

- Re-running the importer with the same directory must update existing screens in place and add new ones; it must not duplicate screens for the same owner+name.
- A screen's `updated_at` reflects the last import time.

### 4.4 Failure behavior

- A file that cannot be parsed into at least one rule is counted as failed and skipped (not stored).
- Parser warnings are counted and reported but do not abort the import.
- Missing inputs directory → fatal error with a clear message (config missing or path absent).

## 5. Screen execution contract

### 5.1 Input

- A `user_screens` row whose `filters_json.engine == 'zacks_rw'`.
- The `filters_json.rules` array (one object per rule atom: code, operator, value, connective, timeframe, raw_operator, formula, etc.).

### 5.2 Universe

- Built by `ZacksUniverse` from: active symbols (`symbol_master.is_active = 1`), latest close+volume per symbol, latest fundamentals row per symbol, computed windows (precomputed if fresh, else runtime), and optionally 20d volume if any rule references field 22.
- Universe size is reported with every run result.

### 5.3 Evaluation semantics

- Comparison operators apply per symbol; a symbol missing the referenced metric fails that rule (RW behavior).
- Direct rank operators (top/bottom N, top/bottom %) select from the active universe by the referenced metric.
- Group-rank variants rank within sector (approximation) when supported; aggregate-scoring group-rank operators are reported as unsupported.
- AND/OR connective grouping: rules linked by OR form an alternative group; groups are ANDed.
- Unsupported atoms (custom formulas, unresolved field codes, aggregate references, group-rank variants not supported) are reported in `skipped` and treated as neutral so the rest of the screen still executes honestly.
- `fully_executed` is true when `skipped` is empty.

### 5.4 Output

- `symbols`: matched symbols, each with symbol, name, exchange, close, price_date, and the metric value per rule index that drove the match.
- `skipped`: per-atom skip report (index, rule, reason).
- `universe_size`, `rule_count`.
- Symbols sorted by symbol for stable output.

## 6. Signal dispatch contract (`zacks_signal_dispatcher.py`)

Runs after a scrape cycle. Behavior:
- Reads the Discord webhook URL from `system_settings.setting_key = 'discord_alert_webhook'`.
- Counts scrape stats: symbols updated today, symbols with EPS data today, total symbols with EPS data all-time.
- Gets the latest `fetch_date` per symbol that has `zacks_eps_change_f1_4w` populated; for each, reads `zacks_eps_change_f1_4w`, `forward_eps`, and name.
- Top 5 bullish (change > 0, descending) and top 5 bearish (change < 0, ascending).
- Sends one Discord message per signal with the standard wording (bullish: "+X.XX, analysts raising estimates, institutional accumulation leading indicator"; bearish: "X.XX, analysts cutting estimates, institutional distribution leading indicator").
- On successful send, inserts a `alert_queue` row (type `zacks_eps_revision`, severity `high`, payload with symbol/change_value/direction/forward_eps/message).
- If no signals, sends a "no significant revisions tonight" summary.
- Reports whether any signal was dispatched.

Acceptance: the dispatcher is idempotent per run (sends + inserts for the top-5 per direction based on the latest fetch_date per symbol), does not re-send historical signals, and logs scrape stats.

## 7. Backtest / Advisor portfolio contract

### 7.1 Backtest model (matches RW semantics)

- A screen is run on a periodic schedule: holding period H (e.g. 1 week, 4 weeks) defines both the hold duration and the rebalance cadence (every H).
- Each rebalance: run the screen on the universe as of that date; the resulting symbol set is the new holdings; ALL prior holdings are sold, then the new set is bought (sell-all / buy-new).
- Optional stop-loss: a per-symbol stop price (e.g. -X% from entry) that exits a holding early; optional trailing stop: a stop that follows the high since entry by Y%.
- Prices used for portfolio valuation at each rebalance date come from `stockprices.close` at the rebalance date (or the nearest available trading date).

### 7.2 Reported stats (RW-equivalent, full set)

- Total compounded return (% and $)
- Compounded annual growth rate (CAGR)
- Win ratio = winning periods / total periods
- Average number of stocks held (per period)
- Average periodic turnover
- Stop-loss stats: stop-loss threshold used, average number of stocks stopped, average return per period
- Average winning period, largest winning period
- Average losing period, largest losing period
- Max drawdown
- Average winning stretch, best stretch (in periods)
- Average losing stretch, worst stretch (in periods)

### 7.3 Advisor portfolio (running totals)

- A screen can be instantiated as a named Advisor portfolio that is meant to be rebalanced for real (daily/weekly/monthly cadence chosen by the advisor), not just historically backtested.
- The same stat set as 7.2 is maintained as running totals over the portfolio's life: starting from the portfolio's inception, each rebalance updates cumulative return, drawdown, win/loss periods, turnover, stops, stretches, etc.
- Running portfolios persist their state between runs so successive rebalances accumulate rather than restart.

Acceptance: a backtest and a running Advisor portfolio produced from the same screen and same parameters report the same kinds of stats; the difference is that the backtest is a closed historical simulation over a chosen date range, while the Advisor portfolio is an open-ended running account updated by each rebalance.

### 7.4 Scope boundary

- This requirement covers the backtest/stat computation and the running-portfolio accounting. It does not require live order execution or FA journal entries in this pass (those are FR-6 territory if/when needed).

## 8. Unit test notes (UT-14)

Follow the repo's existing BABOK unit-test pattern (see `UT-10-01-001…` and `tests/Unit/ZacksFieldResolverTest.php` / `StockFilterTest.php`).

- UT-14-001: `ZacksFieldResolver::spec()` returns the correct source/key/approx for a representative set of field codes (e.g. 5 price, 19 beta, 44/54 EPS revision, 192 zacks_rank, 505 exchange, and one code not in SPECS returns null).
- UT-14-002: `ZacksScreenRunner` evaluation of a simple single-rule screen against a small hand-built universe returns the expected matched symbols and values.
- UT-14-003: AND/OR connective grouping produces the expected pass/fail outcome on a 3-rule screen with a known universe.
- UT-14-004: rank operator (top N) on a known universe returns the correct top-N symbols by the referenced metric, and symbols missing the metric fail the rule.
- UT-14-005: unsupported atom (custom formula / unresolved code) is reported in `skipped` and does not abort the screen; `fully_executed` is false when any atom is skipped.
- UT-14-006: `ZacksRankPopulator::scoreFor()` returns the expected composite/grade values on a hand-built fundamentals+windows input; `rankForPercentile()` maps boundary percentiles to the correct rank.
- UT-14-007: window calculation helper (extracted from refresh_perf_windows / ZacksUniverse) returns the expected % change for a known price series with a known anchor.
- UT-14-008: `zacks_signal_dispatcher.py` logic (extracted pure functions for "top N bullish/bearish by latest fetch_date") returns the expected symbols from a hand-built fundamentals snapshot.

Acceptance: each UT above passes against the corresponding code path; tests that need a DB run against a test fixtures dataset, not the live DB.

## 9. User acceptance test notes (UAT-14)

- UAT-14a: Import a small set of `.und` files; verify each appears in the screens list with a sensible description, rule count, and source file; re-import the same files and verify counts show updates not duplicates.
- UAT-14b: Run one imported screen; verify matched symbols, the metric values shown, and the skipped-atom report (if any); verify a screen that filters on Zacks Rank runs against populated rank data.
- UAT-14c: Run the EPS revision screener in both directions with a nonzero minimum; verify the columns and the plain-language explanation render correctly; verify a night with signals posts to Discord and inserts alert_queue rows, and a night without signals posts the summary.
- UAT-14d: Backtest one screen with a 1-week hold and again with a 4-week hold, with and without a stop-loss; verify the full stat set appears and is sensible (return %, $ CAGR, win ratio, turnover, stops, stretches, drawdown).
- UAT-14e: Create a running Advisor portfolio from a screen; run two rebalance cycles; verify running totals accumulate across the two runs (return, drawdown, periods, turnover, stops).

## 10. Non-functional requirements applicable

- NFR-1.3 (daily monitor signal generation < 30s) applies to the EPS-revision signal dispatch portion; the full nightly scrape is exempt (it is bound by the number of active symbols and Zacks rate limits).
- NFR-2.2 (graceful degradation when a data source is unavailable) applies: if the Zacks site is unreachable for a symbol or the whole run, the pipeline reports failures per symbol and continues, and screens that depend on missing fields skip those atoms rather than crashing.
- NFR-4.4 (BABOK-format documentation) is satisfied by this document plus BR-14, UC-14a, UC-14b, and the RTM rows.
