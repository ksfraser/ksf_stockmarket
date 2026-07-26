# Architecture Decision Record: Generic Advisor Rule Engine & Pipeline Integration

**Status:** Accepted  
**Date:** 2026-07-20  
**Decision Makers:** Kevin Fraser  
**Related Docs:** `docs/ARCHITECTURE.md`, `docs/requirements/requirements-specification.md`, `docs/requirements/traceability-matrix.md`

---

## Context

The existing advisor backtest system (`advisor_backtest.py`, `strategies.py`) uses hardcoded strategy classes. A `strategy_rules` table exists but is empty and unused by any production code. The system lacks:
- Runtime rule editing (ATR stop %, oscillators, candlestick toggles)
- Combo/conensus strategy testing
- Parameter sweep / sensitivity analysis
- User-designed advisors
- Forward-walk validation
- Integration with existing GA/NN agents

Meanwhile, `strategy_pipeline.py` already encodes most of these capabilities but is isolated from the advisor webapp and rule engine.

## Decision

1. **Add a generic rule composer (`python/src/rules/composer.py`)** that reads existing `strategy_rules` rows and blends them into composite strategies stored back in `strategy_rules`. This lets users compose new advisors from shared ones via CLI/API without editing code.

2. **Add a pipeline integration layer (`python/src/rules/pipeline_integration.py`)** that reuses `strategy_pipeline.py` logic (oscillators, combos, parameter sweeps, consensus voting) inside the advisor/rule stack. It provides:
   - Oscillator/candlestick toggles (`normalize_indicator_set`)
   - Timeframe-aware candlestick scoring (`timeframed_candle_score` for 1D/1W/1M)
   - Combo voting (`consensus_buy_signals`)
   - Parameter sweep and combo sweep runners with DB persistence
   - `backtest_user_advisor` and `forward_walk` entrypoints

3. **Fix the position-hang bug** in both `executor.py` and `advisor_backtest.py` by forcing a sell-all pass when `signals` is empty, matching the existing correct behavior in `rules_backtest.py`.

4. **Keep `strategy_rules` as the single source of truth** for rule definitions. `risk_rules` JSON stores numeric knobs; `entry_rules`/`exit_rules`/`bias_criteria` store declarative selection logic.

5. **Do not replace `advisor_backtest.py` yet.** We extend capabilities through `rules_backtest.py` and `pipeline_integration.py` so legacy behavior stays intact while new features mature.

## Consequences

### Positive
- Users can design custom advisors by blending existing advisors via `python/src/rules/composer.py`.
- Oscillator, candlestick, ATR/stop, and sizing parameters are changeable through DB JSON without code deploys.
- Combo testing and parameter sweeps are runnable standalone (`strategy_pipeline.py`) and from the advisor stack (`pipeline_integration.py`).
- `forward_walk()` enables rolling validation for any custom advisor.
- Position-hang bug is eliminated in both the legacy executor and the rule runner.

### Neutral
- `strategy_pipeline.py` remains a standalone script; it writes to a `RESULTS_TABLE` that is separate from `backtest_runs`. Over time we may align schemas.

### Negative / Risk
- More parallel persistence paths (legacy backtest, rules backtest, pipeline sweep) increases schema-drift risk.
- Pyright type-check noise from cursor rows (`dict` vs `tuple`) in `pipeline_integration.py`; runtime behavior is unchanged because pymysql returns dict-like rows.

## Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Replace `strategy_rules` with a new `advisor_compositions` table | `strategy_rules` already exists, is seeded, and has the columns we need. Adding another table creates sync burden. |
| Build a PHP UI first, then backend | We need a verified Python backend before wiring UI. The rule engine/backend is the harder problem. |
| Keep `strategy_pipeline.py` completely isolated | Loses the reusable oscillator/ATR/combo logic we already paid to write. Wire it in. |
| Drop GA/NN integration as “too complex” | User explicitly asked for it. We can connect them later without re-architecting. |

## Action Items

- [x] Fix position-hang bug in `executor.py` and `advisor_backtest.py` (A14)
- [x] Create `python/src/rules/composer.py` (A1)
- [x] Create `python/src/rules/pipeline_integration.py` (A2)
- [ ] Wire `pipeline_integration` into web/runtime TO-DO via cron or service
- [ ] Expose composer/sweep via CLI and API endpoints
- [ ] Connect `nn_agent.py` / `ga_optimizer.py` to rule engine outputs (A6)
- [ ] Update RTM + requirements docs with new FRs (A9-A11)
