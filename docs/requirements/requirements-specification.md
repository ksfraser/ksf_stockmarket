# Requirements Specification
## KSF Stock Market Analysis System

---

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
- Day-of-week and day-of-month timing evaluation to determine optimal entry/exit timing
- Sector and market-cap-aware position limits (large investors cannot move into small caps without price impact)

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

### BR-7: AI Advisor Personas
The system shall present public reference portfolios run by advisor personas that mimic known investing styles (Buffett, Lynch, etc.) and systematic strategies (index regions/sectors, day/week/month/bi-annual trading) so regular users can view them without logging in. Advisors may use hand-coded picking criteria, Zacks Research Wizard `.und` screen imports, or Research Wizard formula-based criteria. (Per `docs/advisors/REQUIREMENTS_DESIGN.md`.)

### BR-8: Zacks Research Wizard Integration
The system shall import Research Wizard (`.und`) screen files, execute them against the live market universe, dispatch EPS-revision signals to Discord and `alert_queue`, and support backtesting any screen as a rebalancing Advisor portfolio with running totals. (Per `docs/requirements/FR-14-zacks-rw-pipeline.md`.)

### BR-9: LLM-Powered Fundamental Analysis
The system shall use an LLM to analyze forward guidance, news releases, product development, and regulatory approvals for each holding, and store the findings in structured tables (`llm_guidance`, `llm_news`, `llm_regulatory`, `llm_product_dev`, `llm_analysis_sessions`) so AI advisors can read and update them — enabling an LLM-driven advisor to make hold/sell/weight decisions based on fundamental developments, not just price action. The LLM may discover and write new findings not previously in the tables.

### BR-10: LLM Admin Console with Fallback Chain
The system shall provide an admin screen to configure the LLM provider chain: primary, secondary, and fallback providers each with provider name, model, API key, and base URL; and a fallback mode (failover, round_robin, primary_only). The `LLMService` shall attempt completion on primary; on failure or rate-limit (HTTP 429), fall through to secondary then fallback per the configured mode. (Per `docs/advisors/REQUIREMENTS_DESIGN.md`.)

### BR-11: Timing-Aware Backtesting
The system shall capture timing dimensions (day-of-week, day-of-month, period-of-month, month-of-year, near-month-end, near-options-expiry) for every backtest trade and report per-bucket win rate, return, turnover, and holding period so optimal entry/exit timing can be determined empirically and persisted per advisor. Advisors shall have configurable timing preferences stored in `advisor_accounts.profile_json` that running portfolios respect on each rebalance. (Per `docs/advisors/REQUIREMENTS_DESIGN.md`.)

---

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
| FR-3.6 | Zacks Research Wizard screen import and execution    | High     |
| FR-3.7 | Research Wizard formula engine: parse `.und` formula syntax (field refs with time-lag offsets, MovingMean/N periods, AND/OR grouping, coalesce operators) and evaluate against live universe | High |

### FR-4: Backtesting
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-4.1 | Run backtests with configurable date ranges          | High     |
| FR-4.2 | Support multiple rebalancing frequencies             | High     |
| FR-4.3 | Track per-trade P&L, commissions, position sizing    | High     |
| FR-4.4 | Compute Sharpe ratio, max drawdown, win rate        | High     |
| FR-4.5 | Queue-based execution to prevent overload            | Medium   |
| FR-4.6 | Store results per strategy as separate portfolio     | High     |
| FR-4.7 | Timing-aware backtesting: evaluate day-of-week (Mon–Fri) and day-of-month (early/mid/late) impact on entry and exit returns; report best/worst timing buckets per strategy | High |
| FR-4.8 | Market-cap and sector constraints in backtests: large-position caps on small-cap names, sector concentration limits, so simulated portfolios respect real-world execution constraints | High |

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

### FR-7: Strategy Research Agent
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-7.1 | Generate daily internal briefs from system data (ATR optimization, evaluation scores, fundamentals) | High |
| FR-7.2 | Scan external sources (Reddit, arXiv, TradingView) for new strategy ideas | High |
| FR-7.3 | Score external ideas on novelty/feasibility/edge using LLM or heuristic | Medium |
| FR-7.4 | Persist briefs to `research_briefs` DB table and markdown/JSON institutional memory | High |
| FR-7.5 | Support three modes: internal, external, both | Medium |

### FR-8: External Provider Authentication
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-8.1 | OAuth 2.0 authorization code flow for Reddit | High |
| FR-8.2 | API key storage for TradingView and arXiv | Medium |
| FR-8.3 | Store all tokens/credentials as [REDACTED] in `external_auth_tokens` table | High |
| FR-8.4 | Automatic token refresh when access_token expires | Medium |
| FR-8.5 | Extensible provider registry (add new providers without core changes) | Medium |

### FR-9: Risk Gate & Paper Trading Enforcement
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-9.1 | Pre-trade risk gate checks Sharpe, drawdown, strategy gates | High |
| FR-9.2 | Return verdict: APPROVED, REVIEW, BLOCKED | High |
| FR-9.3 | Paper trading default — live trading requires board approval | High |
| FR-9.4 | Configurable thresholds in `risk_thresholds.json` | High |
| FR-9.5 | Web UI for viewing risk thresholds (`?action=advisor&view=thresholds`) | Medium |

### FR-10: Hermes Skill & Scheduled Automation
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-10.1 | Nightly cron at 02:00 generates internal research brief | High |
| FR-10.2 | Hermes skill wrapper for on-demand brief generation | Medium |
| FR-10.3 | Cron output delivered to origin chat | Medium |

### FR-11: LLM Fundamental Data Tables
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-11.1 | `llm_guidance` table: store forward guidance extracted from earnings releases, conference calls, SEC filings per symbol, with source, date, guidance_text, sentiment (positive/negative/neutral), and confidence | High |
| FR-11.2 | `llm_news` table: store news events per symbol (headline, source, date, summary, ticker, sector) with a flag indicating whether the LLM has analyzed the event for material impact | High |
| FR-11.3 | `llm_regulatory` table: track pending regulatory approvals, FDA decisions, SEC filings, patent grants per symbol with status (pending/approved/denied), expected date, and material impact assessment | High |
| FR-11.4 | `llm_product_dev` table: track product launches, pipeline updates, R&D milestones per symbol with stage, expected date, and impact assessment | High |
| FR-11.5 | LLM advisor reads these tables when making hold/sell/weight decisions; if the LLM discovers new guidance, news, regulatory events, or product developments not yet in the tables, it writes them | High |
| FR-11.6 | Admin screen to configure LLM provider, model, API key, base URL, and fallback chain (primary/secondary/fallback) — extends `AdminSettingsController` and `LLMService` | High |

### FR-12: Advisor Picking Strategies with Research Wizard Formulas
| ID     | Requirement                                          | Priority |
|--------|------------------------------------------------------|----------|
| FR-12.1 | Each advisor defines its picking criteria as a set of filter rules — either hand-coded (like the existing `IStrategy::score()` pattern) or imported from Research Wizard `.und` files parsed by the `ksfraser/research-wizard-reader` package | High |
| FR-12.2 | Advisors may use Research Wizard pre-defined filters expressed as formulas: field references with time-lag offsets (e.g. `i95 > i95[Recent-4Q]`), MovingMean/N period calls, scoped references (e.g. `i13[,qqq]>0`), AND/OR connective grouping, and coalesce fallback chains (e.g. `(1/(i192=1)) | (3/(i192=2))`) | High |
| FR-12.3 | The `RwFormulaParser` (from `ksfraser/research-wizard-reader`) binds field codes to live data sources via `ZacksFieldResolver::spec()` and evaluates the parsed formula AST against each candidate symbol's data; formulas that reference unavailable fields are skipped with a report, not silently ignored | High |
| FR-12.4 | Advisor picking criteria are stored as runnable rule sets: hand-coded strategies use `IStrategy::score(array $indicators)`, RW-imported screens use `filters_json` with `engine='zacks_rw'`, and future LLM-generated criteria use a `formula_json` representation that the formula engine can also evaluate | High |
| FR-12.5 | Each advisor's picking frequency (daily/weekly/monthly/bi-annual) is configurable and the backtest engine evaluates picking performance per frequency so the optimal cadence can be determined empirically | High |

---

## 3. Non-Functional Requirements

### NFR-1: Performance
| ID      | Requirement                                          | Target          |
|---------|------------------------------------------------------|-----------------|
| NFR-1.1 | Page load time                                       | < 2 seconds     |
| NFR-1.2 | Backtest execution (per strategy)                    | < 5 minutes     |
| NFR-1.3 | Daily monitor signal generation                      | < 30 seconds    |
| NFR-1.4 | Data import (2000 symbols)                           | < 10 minutes    |
| NFR-1.5 | Research Wizard formula evaluation (per screen × universe) | < 60 seconds for 3000-symbol universe |

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
| NFR-5.5 | FrontAccounting 2.4+                                 | Medium           |

---

## 4. Documentation Cross-References

| Topic | Primary Document |
|-------|-----------------|
| AI Advisor Personas + LLM + Timing + RW Formulas | `docs/advisors/REQUIREMENTS_DESIGN.md` |
| Zacks RW Pipeline | `docs/requirements/FR-14-zacks-rw-pipeline.md` |
| LLM Fundamental Data Tables | `docs/advisors/REQUIREMENTS_DESIGN.md` §Database Design |
| LLM Admin Console | `docs/advisors/REQUIREMENTS_DESIGN.md` §LLM Admin Screen |
| Timing-Aware Backtesting | `docs/advisors/REQUIREMENTS_DESIGN.md` §Timing-Aware Trading |
| RW Formula Integration | `docs/advisors/REQUIREMENTS_DESIGN.md` §Research Wizard Formula Integration |
| Stock Filter Engine | `docs/architecture/stock-filter-engine.md` |
| Architecture | `docs/architecture/architecture-document.md` |
| BABOK/PMBOK Methodology | `docs/methodology/index.md` |
