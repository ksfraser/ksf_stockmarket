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
None — new code path, no existing callers affected.
