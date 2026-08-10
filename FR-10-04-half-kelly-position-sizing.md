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
Should Have

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
