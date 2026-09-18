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
- Savings -> Brokerage cash transfers
- Asset revaluation (unrealized gains/losses)
- Journal entries for investment transactions
- Asset conversion tracking (cash -> securities)

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
| NFR-2.3 | Data integrity -- no silent data loss                 | Required        |

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

## 4. Paperclip Zero-Human Trading Firm Requirements

### FR-7: Strategy Research Agent
| ID      | Requirement                                          | Priority        |
|---------|------------------------------------------------------|-----------------|
| FR-7.1 | Generate daily internal briefs from system data (ATR optimization, evaluation scores, fundamentals) | High |
| FR-7.2 | Scan external sources (Reddit, arXiv, TradingView) for new strategy ideas | High |
| FR-7.3 | Score external ideas on novelty/feasibility/edge using LLM or heuristic | Medium |
| FR-7.4 | Persist briefs to `research_briefs` DB table and markdown/JSON institutional memory | High |
| FR-7.5 | Support three modes: internal, external, both | Medium |

### FR-8: External Provider Authentication
| ID      | Requirement                                          | Priority        |
|---------|------------------------------------------------------|-----------------|
| FR-8.1 | OAuth 2.0 authorization code flow for Reddit | High |
| FR-8.2 | API key storage for TradingView and arXiv | Medium |
| FR-8.3 | Store all tokens/credentials as [REDACTED] in `external_auth_tokens` table | High |
| FR-8.4 | Automatic token refresh when access_token expires | Medium |
| FR-8.5 | Extensible provider registry (add new providers without core changes) | Medium |

### FR-9: Risk Gate & Paper Trading Enforcement
| ID      | Requirement                                          | Priority        |
|---------|------------------------------------------------------|-----------------|
| FR-9.1 | Pre-trade risk gate checks Sharpe, drawdown, strategy gates | High |
| FR-9.2 | Return verdict: APPROVED, REVIEW, BLOCKED | High |
| FR-9.3 | Paper trading default -- live trading requires board approval | High |
| FR-9.4 | Configurable thresholds in `risk_thresholds.json` | High |
| FR-9.5 | Web UI for viewing risk thresholds (`?action=advisor&view=thresholds`) | Medium |

### FR-10: Hermes Skill & Scheduled Automation
| ID      | Requirement                                          | Priority        |
|---------|------------------------------------------------------|-----------------|
| FR-10.1 | Nightly cron at 02:00 generates internal research brief | High |
| FR-10.2 | Hermes skill wrapper for on-demand brief generation | Medium |
| FR-10.3 | Cron output delivered to origin chat | Medium |
| FR-10.4 | Hermes skill exposes scheduler management APIs (pause/resume individual jobs) | Low |
| FR-10.5 | LLM agent jobs execute multi-source scans (Reddit, Canadian forums, Facebook Groups, LinkedIn, Quora) with per-asset prompt customization | High |

## 5. AI Advisor & Fundamental Analysis Requirements (NEW)

### BR-7: AI-Advisor Personas
The system shall provide public-facing AI-advisor personas that represent distinct investment philosophies for simulation and reference. Personas include value investing (Warren Buffett-style), growth-at-reasonable-price (Peter Lynch-style), systematic index-region and sector strategies, frequency-based timing strategies (day/week/month/bi-annual), and LLM-enhanced fundamental analysts that read and update forward-guidance, news, product-development, and regulatory-approval tracking tables.

### BR-8: Zacks / Research Wizard Pre-Defined Filter Integration
The system shall parse and execute Research Wizard (RW) pre-defined filter formulas as reusable advisor screening criteria. Each newsletter-style advisor adopts one RW formula as its stock-picking rule set. A formula parser interprets common RW syntax (comparisons, logical operators, parentheses, field references) into executable conditions. Formula results are cached per screener run. Users may paste or select RW formulas through an admin UI and preview matching stocks.

### BR-9: LLM-Enhanced Fundamental Analysis
The system shall provide LLM-enabled advisors that read `llm_insider_trading`, `llm_news_events`, `llm_product_dev`, and `llm_regulatory` tables at the start of each analysis session, produce conviction scores and investment-thesis summaries, update those tables when new information is found during scanning, and operate within a configurable fallback chain (primary LLM endpoint -> secondary -> fallback).

### BR-10: Timing-Aware Backtesting
The system shall incorporate timing variables into the backtest engine so that entry/exit timing can be optimized: day-of-week timing (e.g., buy on Thursday, sell on Tuesday), day-of-month timing (e.g., first week vs. last week of the month), market-cap-aware position-sizing limits, and sector-rotation timing signals. Timing variables are configurable per advisor and optimizable through backtesting.

### BR-11: LLM Admin & Configuration
The system shall provide an admin screen for configuring LLM provider URLs (primary, secondary, fallback), model names, and API tokens; per-advisor LLM profile assignment; connection-health status display for each endpoint; automatic fallback routing when the primary is unavailable; and secure storage of LLM credentials (never logged in plaintext).

### FR-11: LLM Fundamental Data Tables
| ID     | Requirement                                                                                                                          | Priority |
|--------|--------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-11.1 | System shall maintain `llm_insider_trading` table: forward guidance, executive transactions, insider sentiment per symbol            | High     |
| FR-11.2 | System shall maintain `llm_news_events` table: structured news releases, earnings surprises, product launches, regulatory actions, spin-offs | High     |
| FR-11.3 | System shall maintain `llm_product_dev` table: product development lifecycle stages (concept -> prototype -> production rollout -> market launch -> modification -> EOL) per product line per symbol | High     |
| FR-11.4 | System shall maintain `llm_regulatory` table: regulatory approvals, pending reviews, industry changes, compliance actions per symbol  | High     |
| FR-11.5 | Each LLM table shall include: `id, symbol, event_date, as_of, source, headline, details, confidence, conviction_score, is_verified, created_at, updated_at` | High     |
| FR-11.6 | LLM-enabled advisors shall read these four tables at session start and update them when new information is discovered during scanning  | High     |

### FR-12: Research Wizard Formula Integration
| ID     | Requirement                                                                                                                          | Priority |
|--------|--------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-12.1 | System shall support RW pre-defined filter formula syntax as reusable filter configurations                                           | High     |
| FR-12.2 | Advisors shall load any RW pre-defined filter as their stock-picking criteria                                                        | High     |
| FR-12.3 | A formula parser shall interpret common RW syntax (GT, LT, GTE, LTE, EQ, NEQ, AND, OR, parentheses, field references, literal values) into executable filter conditions | High     |
| FR-12.4 | Advisors shall cache parsed formula results per screener run for performance                                                          | Medium   |
| FR-12.5 | Formula editor UI shall allow users to paste or select RW formulas and preview matching stocks                                       | Medium   |

### FR-13: LLM Advisor Admin Screen
| ID     | Requirement                                                                                                                          | Priority |
|--------|--------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-13.1 | Admin screen for configuring LLM provider URLs (primary, secondary, fallback), model names, and API tokens                          | High     |
| FR-13.2 | Per-advisor LLM profile assignment (which LLM config an advisor uses)                                                                | Medium   |
| FR-13.3 | Connection health status display for each configured LLM endpoint                                                                     | Medium   |
| FR-13.4 | Automatic fallback chain: primary -> secondary -> fallback when endpoint unavailable                                                   | High     |
| FR-13.5 | All LLM credentials stored securely -- password-hashed where applicable, never logged in plaintext                                    | High     |

### FR-16: Timing Variables in Advisor Control Plane
| ID     | Requirement                                                                                                                          | Priority |
|--------|--------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-16.1 | Advisor control plane shall expose day-of-week timing preference per advisor (preferred entry day, preferred exit day)              | High     |
| FR-16.2 | Advisor control plane shall expose day-of-month timing preference per advisor (week-of-month bias for entry and exit)               | Medium   |
| FR-16.3 | Backtest engine shall accept timing-variable configurations and report win rate / Sharpe / drawdown by timing scenario              | High     |
| FR-16.4 | Backtest engine shall support market-cap-aware position sizing limits (larger caps = larger positions, capped at advisor max)      | Medium   |
| FR-16.5 | Backtest engine shall support sector-rotation timing signals (buy sector when momentum confirmed, reduce when momentum fades)       | Medium   |

## 6. Change Log
