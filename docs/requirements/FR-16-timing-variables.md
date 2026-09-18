# FR-16: Timing Variables in Advisor Control Plane

## Requirement

The system shall incorporate timing variables into the backtest engine so that entry/exit timing can be optimized: day-of-week timing, day-of-month timing, market-cap-aware position-sizing limits, and sector-rotation timing signals.

## Business Context

BR-10 (Timing-Aware Backtesting) requires the backtest engine to support configurable timing variables per advisor. The goal is to determine whether buying is best on Thursday, selling on Tuesday, etc., and to optimize position sizing based on market cap and sector momentum.

## Timing Variables

### Day-of-Week Timing
| Variable | Scope | Values | Default |
|----------|-------|--------|---------|
| entry_day_of_week | Per-advisor | 0=Monday ... 4=Friday | 0 (Monday) |
| exit_day_of_week | Per-advisor | 0=Monday ... 4=Friday | 4 (Friday) |

### Day-of-Month Timing
| Variable | Scope | Values | Default |
|----------|-------|--------|---------|
| entry_week_of_month | Per-advisor | 1=first ... 5=last | 1 (first week) |
| exit_week_of_month | Per-advisor | 1=first ... 5=last | 5 (last week) |

### Market-Cap-Aware Position Sizing
| Variable | Scope | Values | Default |
|----------|-------|--------|---------|
| market_cap_position_limit | Per-advisor | JSON: {micro: 2%, small: 3%, mid: 4%, large: 5%} | {micro: 2, small: 3, mid: 4, large: 5} |
| max_position_pct | Per-advisor | 1-10% | 5% |

Market cap tiers:
- Micro cap: < $300M
- Small cap: $300M - $2B
- Mid cap: $2B - $10B
- Large cap: >= $10B

Position size = min(tier_limit, max_position_pct)

### Sector Rotation Timing
| Variable | Scope | Values | Default |
|----------|-------|--------|---------|
| sector_rotation_enabled | Per-advisor | BOOLEAN | FALSE |
| sector_momentum_lookback | Per-advisor | Days (e.g., 50) | 50 |

When sector rotation is enabled:
- Compute sector momentum (e.g., 50-day SMA of sector ETF price)
- Only allow entries in sectors with confirmed upward momentum
- Reduce/exit positions in sectors with fading momentum

## Backtest Engine Extension

The backtest engine (`src/backtest/optimize.py`, `five_year_backtest.py`) extends to:

1. Accept timing configuration per advisor/scenario
2. Filter trades by timing rules:
   - Only allow entries on or near the preferred entry day
   - Only allow exits on or near the preferred exit day
   - Only allow entries during the preferred week-of-month
3. Apply market-cap-aware position sizing per trade
4. Apply sector rotation timing signals (if enabled)
5. Report per-scenario metrics:
   - Win rate
   - Sharpe ratio
   - Max drawdown
   - Total return
   - By timing configuration (comparable across scenarios)

## Timing Optimization

The backtest engine supports scanning timing configurations:

```python
# Example: scan day-of-week combinations
for entry_dow in range(5):  # Mon-Fri
    for exit_dow in range(5):
        config = TimingConfig(entry_dow=entry_dow, exit_dow=exit_dow)
        result = backtest.run(config=config)
        results.append((entry_dow, exit_dow, result.sharpe, result.win_rate))
```

## Advisor Control Plane Exposure

Timing variables are exposed in the advisor control plane:
- Each advisor has a `timing_config` JSON column in the `advisors` table
- Admin UI allows editing timing config per advisor
- Backtest UI allows selecting timing scenarios to compare
- Results table shows win rate / Sharpe / drawdown per timing scenario

## Acceptance Criteria

- [ ] Backtest engine accepts day-of-week timing config (entry + exit)
- [ ] Backtest engine accepts day-of-month timing config (entry + exit week)
- [ ] Backtest engine applies market-cap-aware position sizing per trade
- [ ] Backtest engine supports sector rotation timing (optional, per-advisor)
- [ ] Backtest reports per-scenario metrics (win rate, Sharpe, drawdown, total return)
- [ ] Timing optimization scan completes in < 10 minutes for all day-of-week combos
- [ ] Advisor control plane stores and displays timing config per advisor
- [ ] UI allows comparing timing scenarios side by side

## Related

- BR-10: Timing-Aware Backtesting
- `docs/advisors/REQUIREMENTS_DESIGN.md` §Timing-Aware Trading
- `docs/architecture/architecture-document.md` §10.7
- `docs/requirements/UT-16-timing-backtesting.md`
