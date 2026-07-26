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

### BR-7: Advisor Hiring & Recommendations
The system shall allow users to hire one or more advisor accounts to generate
actionable recommendations and deliver them via the user's chosen channels:
- Email
- Discord DM or private channel
- WhatsApp (via gateway)

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
| FR-3.6 | Screener preset changes update results without full-page reload (AJAX) | Medium |

### FR-4: Backtesting
|| ID     | Requirement                                          | Priority |
||--------|------------------------------------------------------|----------|
|| FR-4.1 | Run backtests with configurable date ranges          | High     |
|| FR-4.2 | Support multiple rebalancing frequencies             | High     |
|| FR-4.3 | Track per-trade P&L, commissions, position sizing    | High     |
|| FR-4.4 | Compute Sharpe ratio, max drawdown, win rate        | High     |
|| FR-4.5 | Queue-based execution to prevent overload            | Medium   |
|| FR-4.6 | Store results per strategy as separate portfolio     | High     |
|| FR-4.7 | Compose custom advisors by blending existing rules   | High     |
|| FR-4.8 | Run multi-strategy combo consensus backtests         | High     |
|| FR-4.9 | Run parameter sweeps across risk/sizing variables    | High     |
|| FR-4.10| Forward-walk rolling backtest validation             | Medium   |
|| FR-4.11| Oscillator/candlestick/ATR toggle controls in rules | High     |
|| FR-4.12| Timeframe-aware candlestick signals (D/W/M)          | Medium   |

### FR-5: Rule Engine & Custom Advisors
|| ID     | Requirement                                          | Priority |
||--------|------------------------------------------------------|----------|
|| FR-5.1 | Persist rule definitions in `strategy_rules` table   | High     |
|| FR-5.2 | Load rule-driven signals for any advisor             | High     |
|| FR-5.3 | Runtime rule editor for stop %, ATR mult, sizing     | High     |
|| FR-5.4 | Share custom advisors with other users               | High     |
|| FR-5.5 | Auto-sell stale positions on empty signal sets       | High     |
|| FR-5.6 | NN/GA/RL agents optimize rule weights via backtest   | Medium   |

### FR-6: Advisor Hiring & Recommendations
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-6.1 | Browse available advisors with strategy summary      | High     |
| FR-6.2 | Hire/pause/fire advisors per user                    | High     |
| FR-6.3 | Cron generates advisor signals for active hires only | High     |
| FR-6.4 | Queue recommendations per user per advisor           | High     |
| FR-6.5 | Deliver recommendations via email, Discord, WhatsApp | High     |
| FR-6.6 | Recommendations carry notes: action, price, stops, confidence, reason | High |
| FR-6.7 | User notification preferences UI                     | Medium   |
| FR-6.8 | API endpoints: recommendations, preferences | Medium |
| FR-6.9 | WhatsApp gateway: HTTP POST with E.164 normalization | Medium |
| FR-6.10 | Private Discord recommendation delivery (bot DM / channel webhook) | Medium |

### FR-7: User Management & RBAC
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-7.1 | User authentication (username/password)              | High     |
| FR-7.2 | Role-Based Access Control (admin/trader/viewer)      | High     |
| FR-7.3 | Watchlists per user                                  | Medium   |
| FR-7.4 | Session management                                   | High     |

### FR-8: FrontAccounting Integration
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-8.1 | Record cash → brokerage transfers                   | Medium   |
| FR-8.2 | Track asset revaluation in FA                        | Medium   |
| FR-8.3 | Stock data in MariaDB (not FA tables)                | High     |
| FR-8.4 | UI respects FA RBAC and permissions                  | Medium   |

### FR-9: Shared Advisor Access
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-9.1 | Advisor portfolios may be public or shared           | High     |
| FR-9.2 | Users may browse shared advisor portfolios           | High     |
| FR-9.3 | Shared portfolio path must auto-select the advisor   | High     |
| FR-9.4 | Shared transactions tab must preserve advisor selection | High   |

### FR-10: Broker Stop Orders
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-10.1 | Place manual stop orders (trailing, stop-loss, stop-limit) | High |
| FR-10.2 | Support ALL-share or portion-percentage sell       | High     |
| FR-10.3 | View active stops with distance to trigger          | High     |
| FR-10.4 | View historical triggered / cancelled / expired stops | Medium |

### FR-11: Alerts / Monitoring
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-11.1 | Display alert queue counts (pending / completed / failed) | High |
| FR-11.2 | Show last 2 trading days of recent alerts           | High     |
| FR-11.3 | Date-stamp each alert                                | High     |
| FR-11.4 | Indicate repeat alerts (same symbol+type hit prior day) | Medium |


- **FR-103**: The system shall enforce optional knowledge-base-derived risk rules before entries.
- **FR-104**: Admin UI shall allow editing optional_rules JSON per strategy bucket.
- **FR-105**: Optional rules include: min reward:risk ratio, emergency buffer target + grace days, leverage cap, margin utilization + buffer + grace hours, asset class blacklist.

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

### NFR-4.1: Distributed, Idempotent, DI-based Data Layer
| ID      | Requirement                                          | Target          |
|---------|------------------------------------------------------|-----------------|
| NFR-4.1.1 | Calculators fetch via Repository, never raw yfinance inline | Required |
| NFR-4.1.2 | Fetchers (yFinance, Google, SEDAR, SEC) return DTOs only, write via Repository | Required |
| NFR-4.1.3 | DTO domain fields are single source of truth; repos map to schema | Required |
| NFR-4.1.4 | SQLite `price_intraday` / `alert_queue` for sub-day/ephemeral work | Required |
| NFR-4.1.5 | MariaDB `stockprices` for daily+ history | Required |
| NFR-4.1.6 | `Repository.is_stale()` contract: calculator returns `STALE_DATA` if age > threshold | Required |
| NFR-4.1.7 | Every script is rerunnable with same outcome (idempotent) | Required |

### NFR-5: Compatibility
| ID      | Requirement                                          | Priority        |
|---------|------------------------------------------------------|-----------------|
| NFR-5.1 | PHP 8.1+                                             | High            |
| NFR-5.2 | MariaDB 10.6+ / MySQL 8.0+                          | High            |
| NFR-5.3 | Python 3.11+                                         | High            |
| NFR-5.4 | Apache 2.4+ with mod_proxy                           | High            |
| NFR-5.5 | FrontAccounting 2.4+                                 | Medium          |
