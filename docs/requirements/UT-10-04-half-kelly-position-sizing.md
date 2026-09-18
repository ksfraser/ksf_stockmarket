# Unit Test Outline: UT-10-04 — Half-Kelly Position Sizing

## Requirement Coverage
- FR-10: Hermes Skill & Scheduled Automation
- BR-6: Paperclip Zero-Human Trading Firm (position sizing sub-requirement)

## Preconditions
- Python test environment with position sizing module
- Test portfolio with known cash balance and current positions
- Mock signal with known win rate and payoff ratio

## Test Cases

### TC-10-04-01: Half-Kelly fraction calculation
**Given** a signal with win rate w = 0.60 and payoff ratio r = 1.5
**When** the Half-Kelly fraction is computed
**Then** f_kelly = (w * r - (1-w)) / r = (0.60 * 1.5 - 0.40) / 1.5 = 0.333...
**And** f_half_kelly = f_kelly / 2 = 0.1667 (16.67% of portfolio)

### TC-10-04-02: Half-Kelly with capped maximum
**Given** f_half_kelly = 0.1667 (16.67%)
**And** the maximum position size is capped at 10% of portfolio
**When** the position size is computed
**Then** the actual position size is min(f_half_kelly, max_position) = 10%
**And** the cap is applied after the Half-Kelly calculation

### TC-10-04-03: Half-Kelly with negative edge (no position)
**Given** a signal with win rate w = 0.40 and payoff ratio r = 1.0
**When** the Half-Kelly fraction is computed
**Then** f_kelly = (0.40 * 1.0 - 0.60) / 1.0 = -0.20 (negative)
**And** f_half_kelly = 0 (no position taken, negative edge)
**And** the signal is rejected for entry

### TC-10-04-04: Half-Kelly with zero win rate
**Given** a signal with win rate w = 0.0 and payoff ratio r = 2.0
**When** the Half-Kelly fraction is computed
**Then** f_kelly = (0.0 * 2.0 - 1.0) / 2.0 = -0.50 (negative)
**And** f_half_kelly = 0 (no position taken)

### TC-10-04-05: Half-Kelly position size in dollars
**Given** a portfolio with $100,000 cash balance
**And** f_half_kelly = 0.10 (10%)
**When** the position size in dollars is computed
**Then** position_size = $100,000 * 0.10 = $10,000
**And** if the stock price is $50, the number of shares = floor($10,000 / $50) = 200 shares

### TC-10-04-06: Half-Kelly with existing position (add to position)
**Given** a portfolio with an existing 5% position in a symbol
**And** a new signal for the same symbol with f_half_kelly = 0.10
**When** the position size is computed
**Then** the total target position = 10% of portfolio
**And** the additional buy amount = (10% - 5%) * portfolio_value
**And** if the existing position already exceeds the target, no additional buy is made

### TC-10-04-07: Half-Kelly decay with outdated signals
**Given** a signal that is 5 days old with no price movement confirmation
**When** the position size is computed
**Then** the f_half_kelly fraction is decayed by a factor (e.g., 0.9 per day without confirmation)
**And** after 5 days, the effective fraction = 0.10 * (0.9^5) = 0.059 (5.9%)

### TC-10-04-08: Half-Kelly output includes all components
**Given** a validated signal
**When** the Half-Kelly position sizing computes the order
**Then** the output includes: f_kelly, f_half_kelly, position_size_dollars, shares_to_buy, decay_factor_applied, cap_applied (boolean)
**And** the output is in a structured format for the execution pipeline

## Postconditions
- Half-Kelly fraction is correctly computed from win rate and payoff ratio
- Capped at maximum position size
- Negative edge signals result in zero position
- Existing positions are accounted for in add-to-position scenarios
- Outdated signals are decayed
- Output is structured for downstream execution

## Related
- FR-10: Hermes Skill & Scheduled Automation
- Kelly Criterion: f = (p*b - q) / b where p=win rate, b=payoff ratio, q=1-p
- `UT-10-01-001-statistical-validation-basic.md`
- `UT-10-02-001-route-hypothesis-keywords.md`
- `UT-10-03-statistical-validation-layer3.md`
