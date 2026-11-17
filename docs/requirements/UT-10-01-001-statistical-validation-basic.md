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

## Related Test Outlines
- `docs/requirements/UT-10-01-001-statistical-validation-basic.md` — this document
- `docs/requirements/UT-10-02-001-route-hypothesis-keywords.md` — FR-10-02
- `docs/requirements/UT-10-03-statistical-validation-layer3.md` — FR-10-03
- `docs/requirements/UT-10-04-half-kelly-sizing.md` — FR-10-04
- `docs/requirements/UT-11-llm-fundamental-data.md` — FR-11 LLM data
- `docs/requirements/UT-11-06-llm-admin-console.md` — FR-11.6 LLM admin
- `docs/requirements/UT-12-rw-formula-advisors.md` — FR-12 RW formulas
- `docs/requirements/UT-16-timing-backtesting.md` — FR-16 timing-aware backtesting
