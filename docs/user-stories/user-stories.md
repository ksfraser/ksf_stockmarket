# User Stories

## Portfolio Management

### US-1: View Portfolio Dashboard
**As a** trader
**I want to** see my current holdings with real-time values
**So that** I can monitor my portfolio performance at a glance

**Acceptance Criteria:**
- [ ] Shows all positions with symbol, shares, cost basis, current value, P&L
- [ ] Displays total portfolio value and day change
- [ ] Updates prices from latest available data
- [ ] Loads in < 2 seconds

### US-2: Add Transaction
**As a** trader
**I want to** record a buy/sell/dividend transaction
**So that** my portfolio reflects my actual holdings

**Acceptance Criteria:**
- [ ] Form with symbol, type (BUY/SELL/DIVIDEND), shares, price, date
- [ ] Validates symbol exists in stockinfo
- [ ] Updates portfolio table automatically
- [ ] Records transaction in transaction table

### US-3: Track Portfolio History
**As a** trader
**I want to** see my portfolio value over time
**So that** I can evaluate long-term performance

**Acceptance Criteria:**
- [ ] Daily snapshot of total portfolio value
- [ ] Chart showing value over selectable time range
- [ ] Export to CSV

## Analysis

### US-4: View Technical Analysis
**As a** trader
**I want to** see TA indicators for a given symbol
**So that** I can make informed trading decisions

**Acceptance Criteria:**
- [ ] Displays SMA(20/50/200), RSI(14), MACD, Bollinger Bands
- [ ] Shows candlestick chart with pattern annotations
- [ ] Generates BUY/SELL/HOLD signal with confidence percentage
- [ ] Computed by Python engine via API

### US-5: Run Stock Screen
**As a** trader
**I want to** screen stocks using Motley Fool or Buffett criteria
**So that** I can find investment candidates

**Acceptance Criteria:**
- [ ] Select screen type (Rule Maker, Bear Market, Buffett, Combined)
- [ ] Select universe (TSX, TSX 60, S&P 500, all)
- [ ] Returns ranked list with scores
- [ ] Results sortable by any column

### US-6: ETF Screener
**As a** trader
**I want to** screen ETFs by Sharpe ratio, MER, returns, and correlation
**So that I can find the best ETFs for my portfolio

**Acceptance Criteria:**
- [ ] Filter by MER, return range, Sharpe ratio
- [ ] Show correlation with existing holdings
- [ ] Rank by composite score
- [ ] Display holdings overlap analysis

## Backtesting

### US-7: Configure Backtest
**As a** trader
**I want to** configure and run a backtest
**So that** I can evaluate a strategy before committing capital

**Acceptance Criteria:**
- [ ] Select strategy (MF, Buffett, Turtle, Combined)
- [ ] Set date range, initial capital, trade fee
- [ ] Set rebalancing frequency
- [ ] Set max position size (3%, 5%, 10%)
- [ ] Submit to queue, get run ID

### US-8: View Backtest Results
**As a** trader
**I want to** see detailed backtest results
**So that** I can evaluate strategy performance

**Acceptance Criteria:**
- [ ] Summary: total return, Sharpe, max drawdown, win rate, num trades
- [ ] Trade log: date, symbol, type, price, quantity, P&L
- [ ] Equity curve chart
- [ ] Comparison with benchmark (TSX Composite)

## Seg Funds

### US-9: Screen Seg Funds
**As an** investor with LIRA/LRSP
**I want to** screen seg funds by MER, guarantee level, and returns
**So that** I can choose the best funds for my locked-in accounts

**Acceptance Criteria:**
- [ ] Filter by carrier, MER (< 2.5%), guarantee (≥ 75%)
- [ ] Filter by series (NLCB2/LL no-load)
- [ ] Show 1Y/3Y/5Y/10Y returns
- [ ] Rank by risk-adjusted return

## FA Integration

### US-10: Record Transfer
**As a** user with FA integration
**I want to** record a savings → brokerage transfer
**So that** FA tracks the asset conversion

**Acceptance Criteria:**
- [ ] Form: from account, to account, amount, date
- [ ] Creates FA journal entry
- [ ] Records in fa_transfers table
- [ ] Links to brokerage transaction

### US-11: Revalue Assets
**As a** user with FA integration
**I want to** revalue my investment assets to current market prices
**So that** FA reflects unrealized gains/losses

**Acceptance Criteria:**
- [ ] Pulls latest prices from MariaDB
- [ ] Computes unrealized gain/loss per position
- [ ] Creates FA revaluation journal entry
- [ ] Shows before/after comparison

## Administration

### US-12: Manage Users
**As an** admin
**I want to** create and manage user accounts
**So that** I can control access to the system

**Acceptance Criteria:**
- [ ] Create user with username, email, role
- [ ] Set/reset password
- [ ] Activate/deactivate account
- [ ] Assign role (admin/trader/viewer)

### US-13: Manage Watchlists
**As a** trader
**I want to** create and manage watchlists
**So that** I can organize symbols I'm tracking

**Acceptance Criteria:**
- [ ] Create watchlist with name
- [ ] Add/remove symbols
- [ ] View watchlist with current prices
- [ ] Only owner can modify (admin can modify any)
