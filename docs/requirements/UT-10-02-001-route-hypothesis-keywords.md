# UT-10-02-001: route_hypothesis auto-detects test type from keyword

**FR-10-02 · LLM Hypothesis Routing**  
**Priority**: Must Have

## Test Intent
Verify that `route_hypothesis()` selects the correct statistical test based on
hypothesis keyword matching.

## Fixtures
- 120-day return series (`numpy.random.normal(0.0003, 0.012)`)
- 120-day benchmark series (slightly correlated)

## Assertions
| Hypothesis input | Expected test_type |
|------------------|-------------------|
| "Is this trend stationary?" | `adf_stationarity` |
| "Are returns normally distributed?" | `jarque_bera` |
| "Does this beat the benchmark?" | `ols_regression` |
| "Does this have a significant mean return?" | `t_test` |
| "What is the Kelly position size?" | `kelly_position` |
| "Is this asset volatile?" | `rolling_hit_rate` (default) |

## Regression Risk
None — new test only, touches new code.

## Related Test Outlines
- `docs/requirements/UT-10-01-001-statistical-validation-basic.md` — this document
- `docs/requirements/UT-10-02-001-route-hypothesis-keywords.md` — FR-10-02
- `docs/requirements/UT-10-03-statistical-validation-layer3.md` — FR-10-03
- `docs/requirements/UT-10-04-half-kelly-sizing.md` — FR-10-04
- `docs/requirements/UT-11-llm-fundamental-data.md` — FR-11 LLM data
- `docs/requirements/UT-11-06-llm-admin-console.md` — FR-11.6 LLM admin
- `docs/requirements/UT-12-rw-formula-advisors.md` — FR-12 RW formulas
- `docs/requirements/UT-16-timing-backtesting.md` — FR-16 timing-aware backtesting
