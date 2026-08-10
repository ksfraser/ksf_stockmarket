# FR-10-03: Statistical Validation — Advisor Configurable Rules

## Requirement
The system shall allow advisors and users to define per-strategy statistical
test requirements through a configurable rules table. Rules specify (a) which
test to run, (b) the minimum significance threshold, and (c) whether the rule
is required (hard block) or advisory (warning only).

## Rationale (BR-3, BR-7)
Layer 1 runs the same fixed battery for every symbol. Some strategies need
stricter filters (satellite_spec: requires non-normal returns for fat-tail
exploitation) and some need looser ones (income_dividend: steady yield matters
more than alpha significance). Advisor rules encode this domain knowledge.

## Rule Table Schema
`advisor_stat_rules(strategy_type, test_type, min_p_value, required, description, is_active)`

## Seed Rules (applied at install)

| strategy_type | test_type | min_p_value | required | Description |
|---------------|-----------|-------------|----------|-------------|
| core_buffett | t_test | 0.05 | yes | Require significant mean return |
| core_buffett | adf_stationarity | 0.05 | no | Log stationarity warning |
| tactical_swing | t_test | 0.05 | yes | Require significant trend signal |
| tactical_swing | adf_stationarity | 0.05 | no | ADF confirms mean-rev vs trend |
| tactical_swing | jarque_bera | 0.05 | no | Normality for stop calibration |
| income_dividend | t_test | 0.10 | yes | Looser — income is steady |
| satellite_spec | jarque_bera | 0.05 | yes | Fat tails required |
| satellite_spec | kelly_position | 0.00 | yes | Half-Kelly always required |

## Priority
Should Have

## Acceptance Criteria
- [ ] `apply_advisor_stat_rules(conn, symbol, strategy_types, val_result)` returns 3 lists: passed, failed, warned
- [ ] Rules are applied after Layer 1 but do not block scoring — they flag for advisor review
- [ ] `required=True` failures surface as hard block in advisor recommendation output
- [ ] Rule table uses `ON DUPLICATE KEY UPDATE` for idempotent seeding

## Implementation
- `python/scoring_engine.py` :: `apply_advisor_stat_rules()`
- `sql/advisors.sql` :: `advisor_stat_rules` table + seed rows
- `scripts/apply_migration.py` :: deployment

## Regression Risk
Low — additive only; does not modify existing scoring tables or logic.
