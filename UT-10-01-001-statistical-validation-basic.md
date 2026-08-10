# UT-10-01-001: compute_statistical_validation returns sane values on clean series

**FR-10-01 · Automated Statistical Validation**  
**Priority**: Must Have

## Test Intent
Verify that `compute_statistical_validation()` returns all expected keys and
reasonable ranges when given a realistic daily return series.

## Fixtures
- 252-day return series generated from `numpy.random.normal(loc=0.0005, scale=0.015)`

## Assertions
| Field | Condition |
|-------|-----------|
| `t_stat` | float, finite |
| `p_value` | float 0–1 |
| `is_significant` | int 0 or 1 |
| `normality_p_value` | float 0–1 |
| `is_normal` | int 0 or 1 |
| `adf_stat` | float, finite |
| `adf_p_value` | float 0–1 |
| `is_stationary` | int 0 or 1 |
| `kelly_pct` | float ≥ 0 |
| `validation_json` | dict with win_rate, avg_win, avg_loss, expected_val, mean_daily, variance |

## Regression Risk
None — new test only, touches new code.
