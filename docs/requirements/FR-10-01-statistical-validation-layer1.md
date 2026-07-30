# FR-10-01: Statistical Validation — Automatic Baseline Layer

## Requirement
The system shall automatically compute statistical validation metrics for every
symbol during the daily scoring cycle, without requiring analyst or LLM intervention.

## Rationale (BR-3)
Consistent, comparable quantitative data across the full symbol universe is
required before any advisor or LLM adds interpretation. This layer is the
evidence floor that Layers 2 and 3 build upon.

## Tests Run
| Test | Purpose | Null Hypothesis |
|------|---------|----------------|
| One-sample t-test | Mean daily return ≠ 0 | μ = 0 |
| Jarque-Bera | Return distribution normality | Normal |
| ADF stationarity | Return mean-reversion vs trend | Unit root |

## Position Sizing
Half-Kelly fraction `f* = 0.5 × (μ / σ²)` capped at 2% of capital per position.

## Priority
Must Have

## Acceptance Criteria
- [ ] `compute_statistical_validation()` runs inside `score_symbol()` when ≥30 daily closes exist
- [ ] Results persist to `signal_validation` table (symbol × run_date unique key)
- [ ] `kelly_pct` is written into `evalvalue.kellyoptimization`
- [ ] Scoring log shows validation status per symbol

## Implementation
- `python/quant/statistics.py` :: `compute_statistical_validation()`
- `python/scoring_engine.py` :: `write_signal_validation()` + wiring in `score_symbol()`
- `sql/signal_validation.sql` :: table DDL
- `scripts/apply_migration.py` :: deployment runner

## Regression Risk
Low — runs after all scoring tables write; scoped to price history only.
