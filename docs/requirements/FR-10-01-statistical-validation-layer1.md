# FR-10-01: Statistical Validation — Automatic Baseline Layer

**Parent requirements**: FR-10-01 (this document), FR-11 (LLM fundamental data), FR-12 (RW formula advisors), FR-16 (timing-aware backtesting).

**Related test outlines**:
- `docs/requirements/UT-10-01-001-statistical-validation-basic.md` — this requirement
- `docs/requirements/UT-10-02-001-route-hypothesis-keywords.md` — FR-10-02
- `docs/requirements/UT-11-06-llm-admin-console.md` — FR-11.6 LLM admin console
- `docs/requirements/UT-11-llm-fundamental-data.md` — FR-11 LLM data tables
- `docs/requirements/UT-12-rw-formula-advisors.md` — FR-12 RW formula advisors
- `docs/requirements/UT-14-zacks-rw-pipeline.md` — FR-14 Zacks RW
- `docs/requirements/UT-16-timing-backtesting.md` — FR-16 timing-aware backtesting

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
