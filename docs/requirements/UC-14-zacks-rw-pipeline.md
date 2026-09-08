# Use Case UC-14a: Import and run Research Wizard stock screens

**Actor**: Advisor / Kevin (system importer runs as the dedicated `zacks_rw` system user; human actor lists and runs screens).

**Preconditions**:
- `config.yaml zacks_rw.inputs_dir` points at a directory containing `.und` screen files.
- The Zacks scrape has run at least once so `fundamentals` has zacks_* data and `stock_performance_windows` is fresh, OR the runtime window fallback is available.
- For screens that filter on Zacks Rank, `ZacksRankPopulator` has populated `fundamentals.zacks_rank` / composite / grades.

**Main success scenario**:
1. Actor runs the importer (CLI `php scripts/import_zacks_screens.php` or the nightly job). The importer reads every `.und` file in the configured directory, parses each into rules, and upserts a `user_screens` row per screen under the `zacks_rw` owner with `universe = 'stocks'`, a faithful `filters_json`, and a description like "Imported from Research Wizard (.und): N rules, M custom formula."
2. Actor navigates to `?action=rw_screens`. The screens list shows each imported screen with name, owner, description, public flag, and last-updated time, most-recent first.
3. Actor selects a screen and runs it (`?action=run_rw_screen&id=N`). The system builds the live universe, evaluates the stored rules with Zacks/RW semantics, and returns:
   - the screen's source file and description,
   - universe size and rule count,
   - the matched symbols with the per-rule metric values that drove the match,
   - a skipped-atom report if any rule could not be executed.
4. Actor reads the output description: the screen's stored description plus the per-run summary (how many symbols matched, which rules were skipped and why). If the screen filters on Zacks Rank, the rendered rank values are shown as the local Zacks-style composite with the approximation made clear in the detail panel.

**Alternative scenarios**:
- A `.und` file cannot be parsed into at least one rule → it is counted as failed and not stored; the importer reports the failure count.
- A screen references a field code with no live data source → the runner reports that atom as skipped with reason "field code N has no data source in this app" and continues; `fully_executed` is false.
- A screen references a custom formula → skipped with reason "custom formula: not executed".
- The Zacks site is unreachable for a symbol during a scrape → that symbol is skipped for that cycle; screens depending on that symbol's data simply have no match for it (missing data excludes the symbol per RW semantics).
- The inputs directory is missing or unconfigured → import fails with a clear message.

**Postconditions**:
- Imported screens persist in `user_screens` and can be re-run at any time; re-importing updates them in place.
- A run produces a stable, sorted match list and an honest skip report; the screen's `filters_json` is sufficient to re-run without the original file.

---

# Use Case UC-14b: Backtest a screen as a rebalancing portfolio and run it as a live Advisor portfolio

**Actor**: Advisor / Kevin.

**Preconditions**:
- At least one stock screen exists in `user_screens` (imported or otherwise stored with `filters_json` runnable by `ZacksScreenRunner`).
- `stockprices` has history covering the backtest date range, and `stock_performance_windows` (or runtime fallback) can produce the windows any screen rule references.

**Main success scenario (backtest)**:
1. Actor opens the backtest interface for a chosen screen and selects a holding period H (e.g. 1 week, 4 weeks) and a historical date range.
2. The system simulates: on each rebalance date (every H across the range), run the screen on the universe as of that date; the result set becomes the new holdings; all prior holdings are sold and the new set bought (sell-all / buy-new).
3. Optional: actor sets a stop-loss and/or trailing-stop; the simulation applies per-symbol exits when the stop is hit.
4. Prices for portfolio valuation at each rebalance come from `stockprices.close` at (or nearest to) the rebalance date.
5. The system reports the full RW-equivalent stat set: total compounded return (% and $), CAGR, win ratio (winning periods / total periods), average number of stocks held, average periodic turnover, stop-loss threshold, average number of stocks stopped, average return per period, average and largest winning/losing period, max drawdown, average and best/worst winning stretch, average and worst losing stretch.

**Main success scenario (running Advisor portfolio)**:
1. Actor creates a named Advisor portfolio from the screen, choosing a real rebalance cadence (daily/weekly/monthly).
2. On each rebalance (run manually or on schedule), the system runs the screen on the current universe, sells all current holdings, buys the new set, and updates the portfolio's running totals.
3. The portfolio persists its state between runs so cumulative return, drawdown, win/loss periods, turnover, stops, and stretches accumulate over the portfolio's life.
4. Actor views the portfolio's current stats — the same stat categories as the backtest, but as running totals since inception rather than a closed historical simulation.

**Alternative scenarios**:
- A rebalance date has insufficient price history for some symbols → those symbols are excluded from that rebalance's holdings (missing data excludes, consistent with screen semantics).
- A screen returns an empty universe on a rebalance date → the portfolio holds cash for that period (no positions), and the stat computation continues (a zero-position period is a valid period for win/loss/stretch accounting).
- Stop-loss triggers on some holdings → those are exited at the stop price and counted in the stop stats; remaining holdings continue.

**Postconditions**:
- A backtest is a closed historical simulation with a final stat report.
- A running Advisor portfolio is an open-ended account whose stats accumulate across rebalances; the same screen can produce both a backtest (historical) and a running portfolio (live), and both report the same categories of stats.

---

# Use Case UC-14c: Nightly Zacks pipeline (scrape → rank → signals → dispatch)

**Actor**: cron (nightly job `5a2a8f15cbf6` / `run_zacks_refresh.sh`).

**Preconditions**:
- Credentials available to the wrapper (sources `.env` / config).
- `fundamentals` and `stock_performance_windows` schemas exist.
- `system_settings` has a `discord_alert_webhook` value for signal dispatch.

**Main success scenario**:
1. `zacks_scraper.py --all` fetches the four Zacks pages per active symbol and upserts `fundamentals` (zacks_* + valuation columns), `zacks_broker_recommendations`, and `zacks_ratios_history`.
2. `ZacksRankPopulator::populateAll()` computes the Zacks-style composite and rank for every active symbol with data and updates `fundamentals.zacks_rank` / `zacks_composite` / grades.
3. `scripts/refresh_perf_windows.php` refreshes `stock_performance_windows` for the current as_of_date (Hermes + RW windows, anchored to the universe MAX price_date), pruning to the last 14 as_of dates.
4. `zacks_signal_dispatcher.py` reads the latest `fetch_date` per symbol with EPS data, takes the top 5 bullish and top 5 bearish by 4-week F1 EPS change, posts each to Discord, inserts an `alert_queue` row per dispatched signal, and posts a no-signals summary if applicable; it also reports scrape stats.
5. (Future: screen runs / backtests scheduled as part of the nightly cycle.)

**Alternative scenarios**:
- Zacks site unreachable → scrape fails per symbol or in bulk; the job reports failures and continues; screens/rank for affected symbols have missing data (skipped atoms / no rank update).
- No Discord webhook configured → dispatcher reports the error and does not attempt to send.
- `stock_performance_windows` absent → `ZacksUniverse` computes windows at runtime (same semantics); the nightly refresh normally ensures the table exists and is fresh.

**Postconditions**:
- `fundamentals` has the latest zacks_* data per symbol for the day's scrape.
- `stock_performance_windows` is fresh for today's anchor.
- Rank/composite/grades are populated for active symbols with data.
- Any EPS-revision signals are dispatched and queued; a no-signals night still posts a summary.
