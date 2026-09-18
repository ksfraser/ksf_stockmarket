# Unit Test Outline: UT-10-03 — Statistical Validation Layer 3

## Requirement Coverage
- FR-10: Hermes Skill & Scheduled Automation
- BR-6: Paperclip Zero-Human Trading Firm (statistical validation sub-requirement)

## Preconditions
- Python test environment with access to validation modules
- Synthetic price data set with known statistical properties
- Reference implementation of Layer 1 and Layer 2 validations

## Test Cases

### TC-10-03-01: Layer 3 validation - multi-signal confluence check
**Given** a set of 5 signals fired on the same symbol on the same day
**When** Layer 3 validation runs the confluence check
**Then** the system computes a confluence score based on the number of independent signals agreeing
**And** signals with high confluence (>= 3 independent signals) are flagged as higher conviction
**And** isolated single signals are flagged as lower conviction

### TC-10-03-02: Layer 3 validation - regime detection integration
**Given** a market regime classifier that identifies bull/bear/sideways regimes
**When** Layer 3 validation evaluates a signal in a bear regime
**Then** the signal's conviction score is adjusted downward if the signal historically performs poorly in bear regimes
**And** the regime-adjusted conviction is stored alongside the raw conviction

### TC-10-03-03: Layer 3 validation - drawdown control integration
**Given** a current portfolio drawdown of 12% (above the 10% threshold)
**When** Layer 3 validation evaluates a new BUY signal
**Then** the signal is subject to enhanced scrutiny (higher confidence threshold required)
**And** if the signal's historical win rate in similar drawdown conditions is below 40%, the signal is suppressed

### TC-10-03-04: Layer 3 validation - position sizing adjustment
**Given** a signal with high confluence (4 independent signals agreeing) and strong historical win rate (65%)
**When** Layer 3 validation computes position size
**Then** the position size is increased relative to a single-signal position
**And** the increase factors in current portfolio exposure (no single position exceeds max position size)

### TC-10-03-05: Layer 3 validation - time-of-day sensitivity
**Given** a signal fired near market close (last 30 minutes)
**When** Layer 3 validation evaluates the signal
**Then** the signal is flagged as "intraday confirmation" if it aligns with morning signals for the same symbol
**And** signals fired near close that contradict morning signals are flagged for review

### TC-10-03-06: Layer 3 validation - statistical significance threshold
**Given** a signal with a sample size of 15 historical occurrences
**When** Layer 3 validation computes statistical significance
**Then** the system requires a higher win rate threshold for small sample sizes (e.g., 70% win rate for n<20)
**And** signals with insufficient sample size are flagged as "insufficient data" rather than given a definitive conviction

### TC-10-03-07: Layer 3 validation - output format
**Given** a validated signal from Layer 2
**When** Layer 3 completes validation
**Then** the output includes: confluence_score, regime_adjusted_conviction, position_size_recommendation, statistical_significance_flag, data_sufficiency_flag
**And** the output is in a structured format compatible with the Hermes skill delivery pipeline

## Postconditions
- Layer 3 validation output includes confluence, regime adjustment, position sizing, and statistical significance
- Small sample sizes are appropriately flagged
- Drawdown conditions affect signal conviction
- Output is structured for downstream consumption

## Related
- FR-10: Hermes Skill & Scheduled Automation
- `UT-10-01-001-statistical-validation-basic.md` (Layer 1)
- `UT-10-02-001-route-hypothesis-keywords.md` (Layer 2)
