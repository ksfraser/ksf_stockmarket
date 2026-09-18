# Architecture Document
## 1. System Overview
KSF Stock Market Analysis is a hybrid PHP + Python application for:
- Portfolio tracking and management
- Technical and fundamental analysis
- Strategy backtesting
- Seg fund screening
- Screener-driven universe building (US + Canadian dividends, value, quality compounders, low-cost index funds)
- Symbol master synchronization with screener data
- AI advisor runs (sector, balanced fund, bond basket strategies)

## 2. Architecture Pattern

**Hybrid Architecture: PHP (Presentation) + Python (Analysis) + MariaDB (Data)**

```
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+                        Apache 2.4                                +
+  ++++++++++++++++++++++++    ++++++++++++++++++++++++++++++++   +
+  +   PHP 8.1+           +    +  mod_proxy                   +   +
+  +   Front Controller   +    +                              +   +
+  +   ++++++++++++++++   +    +  /api/* -> 127.0.0.1:5000    +   +
+  +   + Controllers  +   +    ++++++++++++++++++++++++++++++++   +
+  +   ++++++++++++++++   +               +                       +
+  +   + Services     +   +               +                       +
+  +   ++++++++++++++++   +               +                       +
+  +   + Models (PDO) +   +               +                       +
+  +   ++++++++++++++++   +               +                       +
+  +   + PythonBridge +<+++++++++++++++++++++++ HTTP +++++++++++ +
+  +   ++++++++++++++++   +               +                    + +
+  ++++++++++++++++++++++++               +                    + +
+                                         +                    + +
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                                          +                    +
                                          v                    +
                              ++++++++++++++++++++++++         +
                              +  Python 3.11+         +         +
                              +  Flask API :5000      +         +
                              +  ++++++++++++++++++  +         +
                              +  + TA Engine      +  +         +
                              +  + Backtest Engine+  +         +
                              +  + Strategies     +  +         +
                              +  + Data Import    +  +         +
                              +  + Reports        +  +         +
                              +  ++++++++++++++++++  +         +
                              ++++++++++++++++++++++++         +
                                         +                     +
                                         v                     +
                              ++++++++++++++++++++++++         +
                              +  MariaDB 10.6+        +<+++++++++
                              +  ++++++++++++++++++  +
                              +  + Portfolio data  +  +
                              +  + OHLCV prices    +  +
                              +  + Transactions    +  +
                              +  + Backtest results+  +
                              +  + User accounts   +  +
                              +  ++++++++++++++++++  +
                              ++++++++++++++++++++++++
```

## 3. Database Schema Architecture

### 3.1 Strategy: Partitioned Tables + Tiered Indicators

The legacy `stock_market` DB had ~130 tables with no partitioning and the `back_finance` DB had 21 tables -- both using MyISAM with latin1 charset. The modernized schema consolidates to ~25 focused tables on InnoDB with utf8mb4, using:

1. **Partition by YEAR**: `stockprices`, `daily_indicators`, `daily_tier2` all partitioned by `YEAR(date)` into ~10 partitions. Enables partition pruning for backtest queries and per-year backup.
2. **Tier 1 indicators via trigger**: `daily_indicators` table populated on each INSERT into `stockprices` (daily return, gap, SMA-20/50/200, volume SMA-20).
3. **Tier 2 indicators via daily event**: `daily_tier2` table populated once per day using MySQL event scheduler with window functions (Bollinger Bands, ATR-14, volume ratios, trend classification). Avoids recalculating expensive window functions on every INSERT.
4. **Unified view**: `v_stock_analysis` joins prices + both indicator tiers for backtesting and UI consumption.

### 3.2 Partitioning: By Year (Not By Symbol)

**Decision: Partition by YEAR, not by symbol.**
- ~8-10 partitions (one per year) vs 2000+ partitions (one per symbol)
- Partition pruning handles backtest date-range queries transparently
- Per-year backup via `mysqldump --where "YEAR(date)=2025"` solves the 2013 4GB dump trauma
- Adding a new partition each year is trivial: `ALTER TABLE ... ADD PARTITION`

### 3.3 Tier 2 Materialized Table (Not View)

**Decision: Materialized table `daily_tier2`, not a VIEW.**
- Window functions (Bollinger, ATR) need 14-20 rows per symbol per calculation
- Calculating on every INSERT would be O(n_symbols) per insert -- prohibitive
- Daily refresh is sufficient because indicator weightings change slowly (weeks/months)
- Populated by MySQL event scheduler at 10 PM ET daily (after market data refresh)
- Python cron can also populate this as an alternative to MySQL events
- `signal_weights` table stores per-symbol, per-signal-type weights that evolve over time via backtesting optimization

## 4. Application Design

### 4.1 PHP Layer
- Front controller pattern (`index.php`)
- PSR-4 autoloading under `Ksf\StockMarket\`
- Controllers, Services, Models (PDO)
- Twig templates for views
- PythonBridge HTTP client for Flask API calls

### 4.2 Python Layer
- Flask REST API on port 5000
- TA-Lib for technical analysis
- pandas for data manipulation
- SQLAlchemy for ORM (or raw SQL for performance)
- Celery or cron for async tasks
- Multiple strategy modules: Motley Fool, Buffett, Turtle, ETF, Seg Fund

### 4.3 Data Flow
```
Daily Processing Flow:
1. Market closes (4 PM ET)
2. yfinance fetches latest prices -> stockprices (trigger fires Tier 1)
3. MySQL event runs Tier 2 (window functions)
4. Python cron runs Tier 3 (TA-Lib vectorized batch)
5. Python cron runs scoring analysis (LLM + fundamental)
6. Python cron updates signal_weights (correlation analysis)
7. Results available for UI and monitoring
```

## 5. Integration Points

### 5.1 FrontAccounting Integration
- FA module uses SOAP/REST API or direct DB access
- Portfolio syncs with FA accounts
- Transactions flow between systems
- Asset revaluation triggers FA journal entries

### 5.2 External Data Sources
- yfinance: Stock prices, fundamentals
- Optional: Alpha Vantage, IEX Cloud, Polygon.io
- CSV imports for legacy data migration

### 5.3 Authentication & Authorization
- User table with roles (admin, trader, viewer)
- Session management via PHP sessions
- RBAC enforced at controller level
- API tokens for Python service authentication

## 6. Testing Strategy

### 6.1 Unit Tests
- PHP: PHPUnit for controllers, services, models
- Python: pytest for TA calculations, strategy logic
- Target: >80% coverage for business logic

### 6.2 Integration Tests
- PHP-to-Python API communication
- Database migration scripts
- FrontAccounting sync

### 6.3 Performance Tests
- Page load times under load
- Backtest execution time
- Data import throughput

## 7. Deployment

### 7.1 Environments
- Development: Local Docker or VM
- Staging: mirror of production
- Production: ksfraser.ca (or similar)

### 7.2 CI/CD
- Git-based workflow
- Automated testing before merge
- Database migrations as part of deployment
- Rollback capability

### 7.3 Monitoring
- Application logs
- Database performance
- API response times
- Cron job execution status

## 8. Security Considerations

### 8.1 Data Protection
- Password hashing (bcrypt/argon2)
- SQL injection prevention (prepared statements)
- XSS prevention (output encoding)
- HTTPS in production

### 8.2 Access Control
- RBAC at application level
- Database user permissions (least privilege)
- API authentication for Python service

### 8.3 Audit Trail
- User action logging
- Portfolio change history
- Backtest run archives

## 9. Scalability Considerations

### 9.1 Database
- Partitioning for large tables
- Index strategy for common queries
- Read replicas for reporting queries (future)

### 9.2 Application
- Stateless PHP layer (horizontal scaling)
- Python service can scale independently
- Caching layer for expensive calculations (future: Redis)

### 9.3 Data Volume
- Historical data retention policy
- Archive old data to cheaper storage
- Partition pruning for query performance

## 10. BABOK and PMBOK Alignment

### 10.1 BABOK Knowledge Areas and Process Groups

| KSF Activity | BABOK Knowledge Area | BABOK Process Group | Primary Artifacts |
|---|---|---|---|
| Portfolio tracking, transaction recording, watchlists, user mgmt | Requirements Analysis and Design Definition; Business Analysis Planning and Monitoring | Elicitation and Collaboration; Life Cycle Management | `business-requirements.md` BR-1, FR-5 |
| Stock/ETF analysis, technical indicators, candlestick patterns, signal weights | Requirements Analysis and Design Definition; Solution Evaluation | Requirements Life Cycle Management; Solution Assessment | `architecture-document.md` Sec.3, `stock-filter-engine.md` Sec.3 |
| Strategy backtesting (Motley Fool, Buffett, Turtle, ETF, seg funds) | Requirements Analysis and Design Definition; Solution Assessment and Validation | Requirements Life Cycle Management; Executing; Monitoring and Controlling | `docs/requirements/FR-4-backtesting.md`, `backtest_engine.py`, `optimize.py`, `five_year_backtest.py` |
| Seg fund screening (12+ carriers, MER <= 2.5%, guarantee >= 75%) | Requirements Analysis and Design Definition; Solution Assessment and Validation | Requirements Life Cycle Management; Executing | `docs/requirements/BR-4-seg-funds.md`, `SegFundFilter.php`, `SegFundController.php`, `docs/requirements/UT-04-seg-fund-filter.md` |
| LLM admin screen (primary/secondary/fallback URLs, models, tokens) | Requirements Analysis and Design Definition; Solution Evaluation | Elicitation and Collaboration; Requirements Life Cycle Management; Solution Assessment and Validation | `docs/requirements/FR-13-llm-admin-screen.md`, `docs/requirements/UT-11-06-llm-admin-console.md`, `AdminSettingsController.php` (PHP), `docs/advisors/REQUIREMENTS_DESIGN.md` Sec.LLM Admin Screen, `docs/architecture/architecture-document.md` Sec.10.8 |
| LLM-enhanced fundamental analysis (guidance, news, product dev, regulatory tables) | Requirements Analysis and Design Definition; Solution Evaluation | Elicitation and Collaboration; Requirements Life Cycle Management; Solution Assessment and Validation | `docs/requirements/FR-11-llm-fundamental-data.md`, `docs/requirements/UT-11-llm-fundamental-data.md`, `LLM Fundamental Analyzer` (Python), `docs/advisors/REQUIREMENTS_DESIGN.md` Sec.LLM Fundamental Data (Python + DB layer) |
| Research Wizard formula integration (pre-defined filters as reusable advisor criteria) | Requirements Analysis and Design Definition; Solution Evaluation | Elicitation and Collaboration; Requirements Life Cycle Management; Solution Assessment and Validation | `docs/requirements/FR-12-rw-formula-integration.md`, `docs/requirements/UT-12-rw-formula-advisors.md`, `RW Formula Parser` (Python), `docs/advisors/REQUIREMENTS_DESIGN.md` Sec.Research Wizard Formula Integration, `docs/architecture/architecture-document.md` Sec.10.6 |
| Timing-aware backtesting (day-of-week, day-of-month, market-cap limits, sector rotation) | Requirements Analysis and Design Definition; Solution Assessment and Validation | Requirements Life Cycle Management; Executing; Monitoring and Controlling | `docs/requirements/FR-16-timing-variables.md`, `docs/requirements/UT-16-timing-backtesting.md`, `Timing Service` (Python), `Backtest Engine` (timing-variable support) |
| Multi-gateway delivery (email/Discord/WhatsApp) | Requirements Analysis, Solution Evaluation | Executing, Monitoring and Controlling | `advisor_notifier.py`, `AdvisorNotificationController` |
| Heat maps + performance reports | Requirements Analysis, Solution Assessment and Validation | Planning, Executing | `performance.py`, `reports.php` template |
| Rebalancing workflows | Requirements Analysis, Solution Evaluation | Planning, Executing | `rebalancing.py`, `RebalancingController` |

### 10.2 BABOK Alignment Summary

- **Strategy Analysis**: BR-1 through BR-11 capture stakeholder needs across portfolio tracking, analysis, screening, backtesting, LLM-enhanced fundamental analysis, RW formula integration, timing-aware trading, and multi-gateway delivery.
- **Requirements Analysis and Design Definition**: Each requirement maps to a design artifact (architecture doc sections, filter engine sections, advisor design doc sections, test outlines). Design options documented for partitioned schema, tiered indicators, and LLM fallback chains.
- **Solution Assessment and Validation**: ATR methodology, backtest results, T+2 settlement validation, LLM accuracy testing (`UT-11-llm-fundamental-data.md`), RW formula accuracy (`UT-12-rw-formula-advisors.md`), timing optimization results (`UT-16-timing-backtesting.md`).
- **Business Analysis Planning and Monitoring**: Documentation versioning, change log in `requirements-specification.md`, traceability matrix (`traceability-matrix.md`), methodology index (`methodology/index.md`).
- **Elicitation and Collaboration**: Stakeholder interviews captured in business-requirements.md; user stories mapped to requirements; multi-gateway delivery patterns defined.
- **Requirements Life Cycle Management**: Requirements traced from BR -> FR -> US -> DB table -> PHP class -> Python script -> test. Change log tracks evolution.
- **Solution Evaluation**: Solution performance measured against requirements; backtest results validate trading strategies; LLM accuracy testing validates fundamental analysis quality.

### 10.3 PMBOK Alignment Summary

- **Scope Management**: BR-1 through BR-11 and their FR variants form the scope baseline. Traceability matrix links scope to design and tests.
- **Schedule Management**: Nightly cron, weekly backtest cadence, LLM analysis runs, RW formula screen runs, and advisor daily signal cadence modeled as scheduled deliverables.
- **Cost Management**: Backtest simulation validates capital-at-risk rules before live deployment. Position sizing controls (3%/5%/10% max) limit exposure.
- **Quality Management**: Validation scripts, syntax checks, schema migrations, LLM accuracy tests, RW formula accuracy tests, timing-variable backtests enforce build quality.
- **Resource Management**: LLM provider fallback chain (primary/secondary/fallback) ensures resource availability. Admin screen manages LLM credentials.
- **Communications Management**: Multi-gateway delivery (email/Discord/WhatsApp) for alerts and reports. Cron output to origin chat.
- **Risk Management**: Emergency buffer, leverage/margin rules, ATR trailing stops, risk gate (Sharpe/drawdown checks), LLM fallback chain, paper-trading default.
- **Procurement Management**: External data sources (yfinance, optional APIs) treated as procurement. LLM provider API keys managed via admin screen.
- **Stakeholder Management**: Public-facing AI advisor personas for reference; user roles (admin/trader/viewer) for access control.

### 10.4 Supporting Diagrams

+Architecture UML views are in `docs/methodology/uml/`:
+- `deployment.puml` -- deployment context
+- `class.puml` -- core class diagram
+- `sequence.puml` -- advisor recommendation sequence
+- `state.puml` -- alert lifecycle state machine
+- `activity.puml` -- daily run activity flow

+All diagrams map to the knowledge areas and process groups above.
