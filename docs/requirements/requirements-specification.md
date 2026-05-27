# Requirements Specification

## 1. Business Requirements

### BR-1: Portfolio Tracking
The system shall track investment portfolios across multiple account types:
- RRSP (Registered Retirement Savings Plan)
- TFSA (Tax-Free Savings Plan)
- LIRA/LRSP (Locked-In Retirement Accounts)
- Non-registered investment accounts
- FrontAccounting-integrated brokerage accounts

### BR-2: Stock & ETF Analysis
The system shall provide technical and fundamental analysis for:
- TSX-listed securities
- TSX-listed ETFs
- NYSE/NASDAQ securities
- Precious metals and commodities

### BR-3: Backtesting
The system shall support strategy backtesting with:
- Multiple screening strategies (Motley Fool, Buffett, Turtle)
- Multiple rebalancing frequencies (weekly, monthly, quarterly, semi-annual)
- Position sizing controls (3%, 5%, 10% max)
- $100K starting capital, $9.95 trade fee

### BR-4: Seg Fund Analysis
The system shall screen and recommend segregated funds from 12+ carriers
for LIRA/LRSP accounts with:
- MER under 2.5%
- Consistent 5-7% historical returns
- 75%+ guarantee level
- No-load (NLCB2/LL) series

### BR-5: FrontAccounting Integration
The system shall integrate with FrontAccounting to track:
- Savings → Brokerage cash transfers
- Asset revaluation (unrealized gains/losses)
- Journal entries for investment transactions
- Asset conversion tracking (cash → securities)

### BR-6: Reporting
The system shall generate:
- Daily trade signals with technical analysis
- Portfolio performance reports
- Backtest results comparison
- Seg fund screening reports

## 2. Functional Requirements

### FR-1: Data Import
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-1.1 | Import historical OHLCV data from CSV files          | High     |
| FR-1.2 | Fetch current prices via yfinance API                | High     |
| FR-1.3 | Import scraped financial statement data              | Medium   |
| FR-1.4 | Support symbol validation and dead symbol detection  | Medium   |
| FR-1.5 | Log all import operations with record counts         | Low      |

### FR-2: Technical Analysis
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-2.1 | Compute SMA, EMA, RSI, MACD, Bollinger Bands        | High     |
| FR-2.2 | Candlestick pattern recognition (15+ patterns)       | Medium   |
| FR-2.3 | Turtle trading system (entry/exit/position sizing)   | Medium   |
| FR-2.4 | Generate BUY/SELL/HOLD signals with confidence       | High     |

### FR-3: Screening
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-3.1 | Motley Fool Rule Maker screen                        | High     |
| FR-3.2 | Motley Fool Bear Market screen                       | Medium   |
| FR-3.3 | Buffett value investing screen                       | High     |
| FR-3.4 | ETF screener (Sharpe, return, MER, correlation)     | High     |
| FR-3.5 | Seg fund screener (MER, guarantee, returns)         | High     |

### FR-4: Backtesting
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-4.1 | Run backtests with configurable date ranges          | High     |
| FR-4.2 | Support multiple rebalancing frequencies             | High     |
| FR-4.3 | Track per-trade P&L, commissions, position sizing    | High     |
| FR-4.4 | Compute Sharpe ratio, max drawdown, win rate        | High     |
| FR-4.5 | Queue-based execution to prevent overload            | Medium   |
| FR-4.6 | Store results per strategy as separate portfolio     | High     |

### FR-5: User Management & RBAC
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-5.1 | User authentication (username/password)              | High     |
| FR-5.2 | Role-Based Access Control (admin/trader/viewer)      | High     |
| FR-5.3 | Watchlists per user                                  | Medium   |
| FR-5.4 | Session management                                   | High     |

### FR-6: FA Integration
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-6.1 | Create FA journal entries for transfers              | Medium   |
| FR-6.2 | Track asset revaluation in FA                        | Medium   |
| FR-6.3 | Stock data in MariaDB (not FA tables)                | High     |
| FR-6.4 | UI respects FA RBAC and permissions                  | Medium   |

## 3. Non-Functional Requirements

### NFR-1: Performance
| ID      | Requirement                                          | Target          |
|---------|------------------------------------------------------|-----------------|
| NFR-1.1 | Page load time                                       | < 2 seconds     |
| NFR-1.2 | Backtest execution (per strategy)                    | < 5 minutes     |
| NFR-1.3 | Daily monitor signal generation                      | < 30 seconds    |
| NFR-1.4 | Data import (2000 symbols)                           | < 10 minutes    |

### NFR-2: Reliability
| ID      | Requirement                                          | Target          |
|---------|------------------------------------------------------|-----------------|
| NFR-2.1 | System uptime                                        | 99.5%           |
| NFR-2.2 | Graceful degradation when Python API unavailable     | Required        |
| NFR-2.3 | Data integrity — no silent data loss                 | Required        |

### NFR-3: Security
| ID      | Requirement                                          | Priority        |
|---------|------------------------------------------------------|-----------------|
| NFR-3.1 | Password hashing (bcrypt/argon2)                     | High            |
| NFR-3.2 | SQL injection prevention (prepared statements)       | High            |
| NFR-3.3 | XSS prevention (output encoding)                     | High            |
| NFR-3.4 | RBAC enforcement at controller level                 | High            |
| NFR-3.5 | HTTPS required in production                         | High            |

### NFR-4: Maintainability
| ID      | Requirement                                          | Priority        |
|---------|------------------------------------------------------|-----------------|
| NFR-4.1 | PSR-4 autoloading, namespaced code                   | High            |
| NFR-4.2 | PHPUnit test coverage > 80% for business logic       | Medium          |
| NFR-4.3 | Static analysis (PHPStan level 8)                    | Medium          |
| NFR-4.4 | BABOK-format documentation                           | High            |
| NFR-4.5 | Migration-based schema management                    | Medium          |

### NFR-5: Compatibility
| ID      | Requirement                                          | Priority        |
|---------|------------------------------------------------------|-----------------|
| NFR-5.1 | PHP 8.1+                                             | High            |
| NFR-5.2 | MariaDB 10.6+ / MySQL 8.0+                          | High            |
| NFR-5.3 | Python 3.11+                                         | High            |
| NFR-5.4 | Apache 2.4+ with mod_proxy                           | High            |
| NFR-5.5 | FrontAccounting 2.4+                                 | Medium          |
