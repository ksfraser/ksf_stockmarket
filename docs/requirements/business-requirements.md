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
Modernize a legacy PHP/MySQL stock market analysis application to a hybrid PHP+Python architecture with partitioned MariaDB, comprehensive TA scoring, and LLM-assisted fundamental analysis.

### 1.4 Business Drivers
1. **2013 backup trauma**: Monolithic mysqldump >4GB caused filesystem truncation — need partitioned tables for per-year backup
2. **TA calculation bottleneck**: Legacy PHP-based TA is slow — need Python/TA-Lib for vectorized batch processing
3. **Scoring system loss risk**: Years of investment thesis scoring data trapped in a legacy schema — need modern, queryable storage
4. **LLM opportunity**: Qualitative analysis (press releases, filings, earnings calls) can be partially automated
5. **Performance**: Legacy app has 1111 PHP files with no autoloading, no namespaces — PSR-4 modernization needed

### 1.5 Success Metrics
- Price data import: 2000 symbols × 15 years in < 10 minutes
- TA calculation: Full 340-indicator suite for all symbols in < 30 minutes
- Signal generation: Daily BUY/SELL signals with confidence in < 30 seconds
- Backup: Per-year partition dump in < 30 seconds each
- Scorecard population: LLM analyzes 10-K for 50 symbols/day

---

## 2. Stakeholder Analysis

| Stakeholder | Role | Interest | Influence |
|---|---|---|---|
| Kevin Frainvestor | Primary user, project owner | High | High |
| investment-monitor cron | Automated consumer | Medium | Low |
| FrontAccounting | Integration partner | Medium | Medium |
| Python analysis engine | Downstream consumer | High | Low |

---

## 3. Business Requirements

### BR-1: Portfolio Tracking
**Statement**: The system shall track investment portfolios across multiple account types with full transaction history.
**Rationale**: Kevin holds positions in RRSP, TFSA, and non-registered accounts. Each has different tax treatment and reporting needs.
**Priority**: Must Have
**Acceptance Criteria**:
- [ ] Track holdings in RRSP, TFSA, MARGIN, RESP, CASH account types
- [ ] Record all transactions (BUY, SELL, DIVIDEND, SPLIT, TRANSFER)
- [ ] Compute cost basis, unrealized P&L, realized gains
- [ ] Daily portfolio value snapshot

### BR-2: Stock & ETF Analysis
**Statement**: The system shall provide comprehensive technical, fundamental, and qualitative analysis for TSX and US-listed securities.
**Rationale**: Investment decisions require multi-factor analysis combining technical signals, fundamental ratios, and qualitative assessment.
**Priority**: Must Have
**Acceptance Criteria**:
- [ ] 340+ TA indicators computed per symbol per day
- [ ] Comprehensive fundamental ratios with attractiveness scoring
- [ ] Qualitative scoring via LLM analysis of filings and press releases
- [ ] Composite investment grade (totalscore out of 36)

### BR-3: Scoring System Preservation
**Statement**: The system shall preserve and enhance the existing investment thesis scoring system.
**Rationale**: Years of manual scoring work (Motley Fool, Buffett tenets, InvestorPlace criteria) represent institutional knowledge that must not be lost.
**Priority**: Must Have
**Acceptance Criteria**:
- [ ] All 10 scoring tables migrated with full history
- [ ] LLM-assisted population of qualitative scores
- [ ] Source attribution for every score (which document was analyzed)
- [ ] Human override capability for all LLM-generated scores
- [ ] Score history tracking

### BR-4: Backtesting
**Statement**: The system shall support multi-strategy backtesting with configurable parameters.
**Rationale**: Strategy validation before committing capital. $9.95/trade fee, max 1% position size, $100K starting capital.
**Priority**: Must Have
**Acceptance Criteria**:
- [ ] Multiple screening strategies (Motley Fool, Buffett, Turtle, Combined)
- [ ] Multiple rebalancing frequencies (weekly, monthly, quarterly)
- [ ] Signal-optimized weights based on correlation analysis
- [ ] Results stored per strategy as separate virtual portfolio

### BR-5: Data Reliability
**Statement**: The system shall support reliable backup and recovery of all data.
**Rationale**: 2013 incident where monolithic mysqldump >4GB caused filesystem truncation. Must never happen again.
**Priority**: Must Have
**Acceptance Criteria**:
- [ ] Price data partitioned by year — each partition backed up independently
- [ ] Per-year backup completes in < 30 seconds
- [ ] Point-in-time recovery for any date
- [ ] Scoring tables backed up as portable, human-readable format
