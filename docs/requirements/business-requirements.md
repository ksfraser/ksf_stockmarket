# Business Requirements Document (BRD)
## KSF Stock Market Analysis System
### BABOK Format v2.0

---

## 1. Project Charter

### 1.1 Project Name
KSF Stock Market Analysis System — Modernization & Enhancement

### 1.2 Project Owner
Kevin Fraser (ksfraser.ca)

### 1.3 Project Description
Modernize a legacy PHP/MySQL stock market analysis application to a hybrid PHP+Python architecture with partitioned MariaDB, comprehensive TA scoring, rule-engine advisors, and closed-loop advisor hiring with multi-channel recommendation delivery.

### 1.4 Business Drivers
1. **2013 backup trauma**: Monolithic mysqldump >4GB caused filesystem truncation — need partitioned tables for per-year backup
2. **TA calculation bottleneck**: Legacy PHP-based TA is slow — need Python/TA-Lib for vectorized batch processing
3. **Scoring system loss risk**: Years of investment thesis scoring data trapped in a legacy schema — need modern, queryable storage
4. **LLM opportunity**: Qualitative analysis (press releases, filings, earnings calls) can be partially automated
5. **Performance**: Legacy app has 1111 PHP files with no autoloading, no namespaces — PSR-4 modernization needed
6. **Advisor adoption**: Users should be able to hire built-in advisor strategies and receive actionable recommendations without editing code

### 1.5 Success Metrics
- Price data import: 2000 symbols × 15 years in < 10 minutes
- TA calculation: Full 340-indicator suite for all symbols in < 30 minutes
- Signal generation: Daily BUY/SELL signals with confidence in < 30 seconds
- Backup: Per-year partition dump in < 30 seconds each
- Scorecard population: LLM analyzes 10-K for 50 symbols/day
- Advice delivery: Recommendations reach focused user channel within 2 minutes of generation

---

## 2. Stakeholder Analysis

| Stakeholder | Role | Interest | Influence |
|---|---|---|---|
| Kevin Frainvestor | Primary user, project owner | High | High |
| Investment-monitor cron | Automated consumer | Medium | Low |
| FrontAccounting | Integration partner | Medium | Medium |
| Python analysis engine | Downstream consumer | High | Low |
| Hired advisor (bot account) | Signal generator for employer | High | Low |

---

## 3. Business Requirements

### BR-1: Portfolio Tracking
**Statement**: The system shall track investment portfolios across multiple account types with full transaction history.
**Rationale**: Kevin holds positions in RRSP, TFSA, RESP, LIRA, and non-registered accounts. Each has different tax treatment and reporting needs.
**Priority**: Must Have
**Acceptance Criteria**:
- [x] Track holdings in RRSP, TFSA, RESP, LIRA (locked-in), non-registered
- [x] Record all transactions (BUY, SELL, DIVIDEND, SPLIT, TRANSFER)
- [x] Compute cost basis, unrealized P&L, realized gains
- [x] Daily portfolio value snapshot
- [x] Advisor transactions tagged with advisor id + notes

### BR-2: Stock & ETF Analysis
**Statement**: The system shall provide comprehensive technical, fundamental, and qualitative analysis for TSX and US-listed securities.
**Rationale**: Investment decisions require multi-factor analysis combining technical signals, fundamental ratios, and qualitative assessment.
**Priority**: Must Have
**Acceptance Criteria**:
- [x] 140+ TA indicators computed per symbol per day
- [x] Comprehensive fundamental ratios with attractiveness scoring
- [ ] Qualitative scoring via LLM analysis of filings and press releases
- [x] Composite investment grade (totalscore out of 36)
- [x] Rating presets (Buffett, MF, etc.) with population automation
- [x] Side-by-side strategy chart system (motley, buffett, turtle, etc.)

### BR-3: Scoring System Preservation
**Statement**: The system shall preserve and enhance the existing investment thesis scoring system.
**Rationale**: Years of manual scoring work represent institutional knowledge that must not be lost.
**Priority**: Must Have
**Acceptance Criteria**:
- [x] All 10 scoring tables migrated with full history
- [ ] LLM-assisted population of qualitative scores
- [x] Source attribution for every score
- [x] Human override capability for all scores
- [x] Score history tracking

### BR-4: Backtesting
**Statement**: The system shall support multi-strategy backtesting with configurable parameters.
**Rationale**: Strategy validation before committing capital.
**Priority**: Must Have
**Acceptance Criteria**:
- [x] Multiple screening strategies (Motley, Buffett, Turtle, Combined)
- [x] Multiple rebalancing frequencies
- [x] Signal-optimized weights based on correlation
- [x] Custom advisor composer + GA/NN agents (rule blending, default weights)
- [x] Multi-strategy combo consensus backtests
- [x] Parameter sweeps across risk/sizing variables
- [x] Forward-walk rolling backtest validation
- [x] ATR/oscillator/candlestick toggle controls in rules

### BR-5: Custom Advisor Builder
**Statement**: Users shall be able to design, share, and backtest custom advisors by combining weights/rules from existing advisors.
**Rationale**: Experimentation without code editing.
**Priority**: Must Have
**Acceptance Criteria**:
- [x] UI/CLI to select advisors and assign blend weights
- [x] Persist composite rule definitions in `strategy_rules`
- [x] Share custom advisors with other users via "shared with me"
- [x] Auto-sell stale positions when strategy signals empty
- [x] NN/GA/RL agents can optimize rule weights through backtest

### BR-6: Data Reliability
**Statement**: The system shall support reliable backup and recovery of partitioned time-series.
**Rationale**: 2013 incident where monolithic mysqldump >4GB caused filesystem truncation.
**Priority**: Must Have
**Acceptance Criteria**:
- [x] Price data partitioned by year — each partition backed up independently
- [x] Per-year backup completes in < 30 seconds
- [x] Point-in-time recovery for any date
- [x] Scoring tables backed up as portable, human-readable format

### BR-7: Advisor Hiring & Recommendations *(new)*
**Statement**: Users shall hire advisor accounts and receive recommendations through their chosen channels, scoped only to the employer. The system shall also enforce optional knowledge-base-derived risk rules before entries.
**Rationale**: Kevin wants actionable guidance without manual polling. Advisors act on rules; outputs are events that should be delivered to the hiring user via the user's configured channels. KB principles (asymmetric risk/reward, diversification, lifecycle allocation) are encoded as tunable optional rules so they apply only when enabled.
**Priority**: Must Have
**Acceptance Criteria**:
- [x] Browse advisors by strategy, hire/pause/fire per user
- [x] User notification preferences: email / Discord / WhatsApp
- [x] Recommendation format: action, symbol, price, max, stop, notes, confidence, reason
- [x] Notes attached to transactions when advisor takes rule action
- [x] API for recommendations + notification preferences
- [x] WhatsApp gateway HTTP framework with E.164 normalization
- [ ] Private Discord reach (bot DM + channel webhook, user-scoped)
- [x] Optional rules: min reward:risk, emergency buffer target + grace days, leverage cap, margin utilization + buffer + grace hours, asset class blacklist

---

## 4. Data Model (summary)

| Table | Purpose | Notes |
|---|---|---|
| users | Auth + RBAC | role: admin / user / viewer / advisor |
| user_settings | Flat prefs | Uses setting_key/value pair |
| portfolio | Current holdings | Per-user, per-account-type |
| portfolio_history | Daily snapshots | cost_basis, unrealized P&L |
| portfolio_trades | Transactions | BUY/SELL/DIV/Split/Transfer |
| advisor_accounts | AI advisor config | strategy, investor type icons, forced rebalance |
| user_advisors | User→advisor hire | user_id, advisor_id, is_active |
| transactions | Event log | source, user_id, advisor_id, notes |
| advisor_recommendations | Recommendation queue | user_id, advisor_id, action, price, stops, sent flags |
| backtest_runs | Strategy runs | Per advisor + date range |
| strategy_rules | Rule + risk/sizing | Per advisor, per symbol whitelist; includes optional_rules JSON |
| broker_stop_orders | Live stops | Via broker API when wired |
| alert_queue | Trigger-level alerts | keyed on detection |
| kb_articles | Knowledge base | slug, markdown content, linked from strategy guidance |

---

## 5. Out of Scope / Deferred
- Real brokerage API execution (manual trade entry until broker integration)
- WhatsApp gateway routing (gateway manual until Twilio/gateway wired)
- Load-tested API scale (single-user profile; competes against broker overhead)
