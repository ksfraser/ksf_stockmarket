# FR-10-04: Half-Kelly Position Sizing

## Requirement
The system shall compute a half-Kelly position-size recommendation for every
scored symbol, expressed as a percentage of capital to allocate.

## Formula
```
f* = 0.5 × (μ / σ²)
kelly_pct = min(f* × 100, max_capital_fraction × 100)
```
Where:
- μ = expected value of the daily return distribution `(win_rate × avg_win) − (loss_rate × avg_loss)`
- σ² = sample variance of daily returns
- max_capital_fraction = 2% (hard cap per position)

## Storage
Persisted to `evalvalue.kellyoptimization` via `write_scores()`.

## Priority
Must Have

## Related test outlines

- `docs/requirements/UT-10-01-001-statistical-validation-basic.md` — FR-10-01 Layer 1 tests
- `docs/requirements/UT-10-02-001-route-hypothesis-keywords.md` — FR-10-02 LLM hypothesis routing
- `docs/requirements/UT-10-03-statistical-validation-layer3.md` — FR-10-03 advisor configurable rules
- `docs/requirements/UT-10-04-half-kelly-sizing.md` — this requirement (FR-10-04)
- `docs/requirements/UT-11-llm-fundamental-data.md` — FR-11 LLM data tables
- `docs/requirements/UT-12-rw-formula-advisors.md` — FR-12 RW formula advisors

## Acceptance Criteria
- [ ] `compute_statistical_validation()` returns `kelly_pct` (percentage, 4 decimal places)
- [ ] `score_symbol()` writes `value_scores['kellyoptimization']` before `write_scores(conn, symbol, value_scores, 'evalvalue')`
- [ ] Negative edge → kelly_pct = 0.0 (no position)

## Implementation
- `python/quant/portfolio.py` :: `half_kelly_position_size()`
- `python/quant/statistics.py` :: imported and called by `compute_statistical_validation()`
- `python/scoring_engine.py` :: value_scores injection in `score_symbol()`

## Regression Risk
Low — additive field to existing evalvalue table write.
