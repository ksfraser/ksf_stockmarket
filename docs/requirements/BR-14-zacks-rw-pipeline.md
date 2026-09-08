# Business Requirement BR-14: Zacks Research Wizard Screen Pipeline

**Statement**: The system shall import Research Wizard stock screens from `.und` files, evaluate them against the live market universe, surface the results and per-screen output descriptions, dispatch EPS-revision signals to Discord and `alert_queue`, and support backtesting any screen as a rebalancing Advisor portfolio with running totals.

**Rationale**: Research Wizard screens encode analyst rule sets (valuation, momentum, estimate revisions, rank filters) that the app can reuse directly. Importing them eliminates hand re-entry, running them produces a current watchlist, and backtesting them the way RW does (periodic rebalance, sell-all/buy-new, optional stops) turns a screen into a trackable Advisor portfolio with real running performance — not just a one-off backtest.

**Priority**: Should Have

**Acceptance Criteria**:
- [ ] Screen import reads `.und` files from a configured directory and stores each screen as a row in `user_screens` (universe = `stocks`) under a dedicated system owner, with `filters_json` faithful to every parsed rule atom and a human-readable `description`; re-running is idempotent (upsert on owner+name).
- [ ] Screen execution loads the live universe (active symbols, latest close, latest fundamentals, computed price windows, optional 20d volume), evaluates stored rules with Zacks/RW semantics (per-symbol comparison, top/bottom N and % rank operators, AND/OR connective grouping, missing-data exclusion, unsupported-atom skip report), and returns matched symbols with the metric values that drove the match plus a `skipped` report.
- [ ] Screens that filter on Zacks Rank have data to run against: `fundamentals.zacks_rank` / `zacks_composite` / `zacks_value_grade` / `zacks_growth_grade` / `zacks_momentum_grade` / `zacks_vgm_grade` are populated for active symbols before those screens run.
- [ ] The EPS-revision screener surfaces bullish/bearish symbols by 4-week F1 EPS change with the columns a user expects to see (symbol, recommendation, analyst count, forward EPS, F1/F2 1w and 4w deltas, trailing/forward PE, ROE, beta, industry) and a plain-language explanation of how to read the signal.
- [ ] EPS-revision signals dispatch to the configured Discord channel and insert into `alert_queue` with full payload (`symbol`, `change_value`, `direction`, `forward_eps`, `message`); a "no signals" night still posts a summary.
- [ ] Any screen can be backtested with RW-style parameters (holding period, rebalance frequency derived from it, sell-all/rebuy-new rebalance, optional stop-loss and trailing-stop), and the backtest reports the full RW-equivalent stats: total compounded return (% and $), CAGR, win ratio, winning periods / total periods, average number of stocks held, average periodic turnover, number stopped, average return per period, average and largest winning/losing period, max drawdown, average and best/worst winning and losing stretches.
- [ ] A screen can be instantiated as a running Advisor portfolio whose stats accumulate from live runs (daily/weekly/monthly rebalance) rather than being a pure historical backtest — i.e., the same stat set is maintained as a running total over the portfolio's life.
- [ ] All data that screens reference is either downloaded (Zacks pages) or calculated (price windows, VGM-style composite and rank, 20d volume) — nothing referenced by a screen rule is left unpopulated by design.
- [ ] The nightly refresh job runs the pipeline in order (scrape → rank populate → screen results / EPS screener → signal dispatch) and is executable from a shell wrapper that sources credentials, so the cron scheduler can run it.

**Out of scope for this requirement**:
- Genuine Zacks Rank feed integration (the rank populator is a local VGM-style approximation; see FR-14 acceptance).
- Portfolio execution / live orders (paper testing and running totals only).
- FrontAccounting journal entry creation for backtest/Advisor portfolio trades (defer to FR-6 when needed).
