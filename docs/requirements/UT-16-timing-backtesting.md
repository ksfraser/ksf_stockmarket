# Unit Test Outline — Timing-Aware Backtesting (UT-16)

Test timing dimension capture and aggregation in the backtest engine.

## UT-16-001: Backtest captures day_of_week per trade

**Given** a backtest simulation with 10 trades on known dates

**When** the backtest engine records each trade

**Then** each trade's timing_buckets row has the correct day_of_week (Mon=1..Fri=5) derived from the trade date

## UT-16-002: Backtest captures period_of_month per trade

**Given** a backtest with trades on day 5 (early), day 15 (mid), day 25 (late)

**When** the backtest engine records each trade

**Then** the timing_buckets rows have period_of_month = early, mid, late respectively

## UT-16-003: Backtest captures near_month_end flag

**Given** trades on day 28, 29, 30, 31 of a 31-day month

**When** the backtest engine records each trade

**Then** near_month_end = 1 for days 28-31 (within 3 days of month end); near_month_end = 0 for other days

## UT-16-004: Backtest captures near_options_expiry flag

**Given** trades on the 3rd Friday of the month (options expiry) and 2 days before

**When** the backtest engine records each trade

**Then** near_options_expiry = 1 for trades within 3 days of monthly options expiry; 0 otherwise

## UT-16-005: Timing bucket aggregation by day_of_week

**Given** a backtest with 100 trades spread across all 5 weekdays

**When** the timing aggregation query runs

**Then** the result shows win rate, average return, and trade count per day_of_week

## UT-16-006: Timing bucket aggregation by period_of_month

**Given** a backtest with trades in early, mid, and late periods

**When** the timing aggregation query runs

**Then** the result shows win rate, average return, and trade count per period_of_month

## UT-16-007: Best/worst timing bucket reported per strategy

**Given** a completed backtest with timing data

**When** the backtest results are compiled

**Then** the run metadata includes best_timing_bucket and worst_timing_bucket (by win rate)

## UT-16-008: Advisor timing preferences stored in profile_json

**Given** an advisor account with timing preferences

**When** the advisor account is saved

**Then** profile_json contains timing.preferred_entry_day, timing.preferred_exit_day, timing.preferred_entry_period, timing.avoid_month_end_entry

## UT-16-009: Running portfolio respects timing preferences

**Given** a running advisor portfolio with preferred_entry_day='Thursday'

**When** a rebalance is scheduled on a Tuesday

**Then** the rebalance is skipped (or deferred to nearest Thursday); no trades are executed on Tuesday

## UT-16-010: Market-cap position limits in backtest

**Given** a backtest with max_position_pct_of_micro_cap=5 and a small-cap stock (market_cap < $300M)

**When** the backtest engine allocates positions

**Then** the small-cap position is capped at 5% of portfolio value, not the default allocation

## UT-16-011: Sector concentration limits in backtest

**Given** a backtest with max_sector_pct=20 and a sector that would receive 25% allocation

**When** the backtest engine allocates positions

**Then** the sector allocation is capped at 20%; excess is redistributed or held as cash

---

*Prerequisite test infrastructure:* `tests/Unit/TimingBacktestTest.php` — new file. Requires a backtest engine test harness that can run simulations against historical price data and inspect timing_buckets rows. Use a small hand-built price series (10-20 days) for deterministic tests.
