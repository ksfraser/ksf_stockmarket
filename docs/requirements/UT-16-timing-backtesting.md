# Unit Test Outline: UT-16 — Timing Backtesting

## Requirement Coverage
- FR-16: Timing Variables in Advisor Control Plane
- BR-10: Timing-Aware Backtesting

## Preconditions
- Test database with historical price data for at least 2 years
- Backtest engine available (optimize.py, five_year_backtest.py)
- Test universe of symbols with known market cap tiers

## Test Cases

### TC-16-01: Backtest with default timing (no timing filters)
**Given** a backtest configuration with no timing variables set
**When** the backtest runs for a 1-year period
**Then** trades are executed on any day of the week
**And** the result includes win rate, Sharpe, max drawdown, total return

### TC-16-02: Backtest with entry day-of-week filter
**Given** a backtest configuration with entry_day_of_week = 3 (Thursday)
**When** the backtest runs
**Then** entries are only executed on Thursdays
**And** exits are not restricted by day-of-week (default)

### TC-16-03: Backtest with exit day-of-week filter
**Given** a backtest configuration with exit_day_of_week = 1 (Tuesday)
**When** the backtest runs
**Then** exits are only executed on Tuesdays
**And** entries are not restricted by day-of-week (default)

### TC-16-04: Backtest with both entry and exit day-of-week filters
**Given** entry_day_of_week = 3 (Thursday) and exit_day_of_week = 1 (Tuesday)
**When** the backtest runs
**Then** entries only on Thursdays, exits only on Tuesdays
**And** the result reflects the timing-constrained trade schedule

### TC-16-05: Backtest with entry week-of-month filter
**Given** entry_week_of_month = 1 (first week of month)
**When** the backtest runs
**Then** entries are only allowed during the first week of each month
**And** entries in other weeks are skipped

### TC-16-06: Backtest with market-cap-aware position sizing
**Given** a configuration with market_cap_position_limit = {micro: 2, small: 3, mid: 4, large: 5}
**When** the backtest runs and enters positions in stocks of different cap tiers
**Then** micro-cap positions are capped at 2% of portfolio
**And** large-cap positions are capped at 5% of portfolio
**And** no position exceeds its tier limit

### TC-16-07: Backtest with max_position_pct cap
**Given** max_position_pct = 3
**When** the backtest enters a position in a large-cap stock (tier limit = 5%)
**Then** the position is capped at 3% (the max_position_pct override)
**And** no position exceeds 3% of portfolio value

### TC-16-08: Backtest with sector rotation enabled
**Given** sector_rotation_enabled = TRUE and sector_momentum_lookback = 50
**When** the backtest runs
**Then** entries are only allowed in sectors with positive 50-day momentum
**And** positions in sectors with fading momentum are reduced or exited

### TC-16-09: Timing scenario comparison report
**Given** backtest results for 3 timing scenarios (default, Thu entry/Tue exit, Mon entry/Fri exit)
**When** the comparison report is generated
**Then** the report shows win rate, Sharpe, max drawdown, and total return for each scenario
**And** the scenarios are comparable side by side

### TC-16-10: Timing optimization scan - day-of-week
**Given** a backtest configuration and a 1-year historical period
**When** the optimization scan runs all 25 day-of-week combinations (5 entry x 5 exit)
**Then** all 25 scenarios complete
**And** the total scan time is < 10 minutes
**And** the best Sharpe ratio scenario is identified

### TC-16-11: Advisor control plane stores timing config
**Given** an advisor with timing_config JSON column
**When** the admin sets entry_day_of_week = 3, exit_day_of_week = 1
**Then** the timing_config is stored in the advisor's row
**And** the backtest engine reads the timing_config when running for that advisor

### TC-16-12: No timing restrictions = all trades allowed
**Given** a backtest with all timing variables set to default (no restrictions)
**When** the backtest runs
**Then** the number of trades equals the unrestricted trade count
**And** results match the default (no timing) backtest

## Postconditions
- Backtest engine correctly filters trades by day-of-week
- Backtest engine correctly filters trades by week-of-month
- Market-cap-aware position sizing caps positions per tier
- Sector rotation timing signals are applied when enabled
- Timing scenario comparison is available in the UI
- Optimization scan completes within performance target

## Related
- FR-16: Timing Variables in Advisor Control Plane
- BR-10: Timing-Aware Backtesting
- `docs/advisors/REQUIREMENTS_DESIGN.md` §Timing-Aware Trading
- `docs/architecture/architecture-document.md` §10.7
