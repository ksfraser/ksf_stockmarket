# Architecture Document
## KSF Stock Market Analysis System

---

## 1. System Overview

KSF Stock Market Analysis is a hybrid PHP + Python application for:
- Portfolio tracking and management
- Technical and fundamental analysis
- Strategy backtesting — including timing-aware evaluation (day-of-week, day-of-month, calendar period)
- Seg fund screening
- Screener-driven universe building (US + Canadian dividends, value, quality compounders, low-cost index funds)
- Zacks Research Wizard screen import, execution, and backtesting as Advisor portfolios
- AI advisor personas with LLM-powered fundamental analysis (guidance, news, regulatory, product development)
- LLM admin console with multi-provider fallback chain configuration
- Symbol master synchronization with screener data
- AI advisor runs (sector, balanced fund, bond basket strategies)

---

## 2. Architecture Pattern

**Hybrid Architecture: PHP (Presentation) + Python (Analysis) + MariaDB (Data)**

```
┌─────────────────────────────────────────────────────────────────┐
│                        Apache 2.4                                │
│  ┌──────────────────────┐    ┌──────────────────────────────┐   │
│  │   PHP 8.1+           │    │  mod_proxy                   │   │
│  │   Front Controller   │    │                              │   │
│  │   ┌──────────────┐   │    │  /api/* → 127.0.0.1:5000    │   │
│  │   │ Controllers  │   │    └──────────┬───────────────────┘   │
│  │   ├──────────────┤   │               │                       │
│  │   │ Services     │   │               │                       │
│  │   │  - LLMService|   │               │                       │
│  │   │  - TimingService|   │               │                       │
│  │   ├──────────────┤   │               │                       │
│  │   │ Models (PDO) │   │               │                       │
│  │   ├──────────────┤   │               │                       │
│  │   │ PythonBridge │◄──┼───────────────┼──── HTTP ──────────┐ │
│  │   └──────────────┘   │               │                    │ │
│  └──────────────────────┘               │                    │ │
│                                         │                    │ │
└─────────────────────────────────────────┼────────────────────┼─┘
                                          │                    │
                                          ▼                    │
                              ┌──────────────────────┐         │
                              │  Python 3.11+         │         │
                              │  Flask API :5000      │         │
                              │  ┌────────────────┐  │         │
                              │  │ TA Engine      │  │         │
                              │  │ Backtest Engine│  │         │
                              │  │  - Timing-aware│  │         │
                              │  │ Strategies     │  │         │
                              │  │ RW Formula Eng │  │         │
                              │  │ Data Import    │  │         │
                              │  │ LLM Analyzer   │  │         │
                              │  │ Reports        │  │         │
                              │  └────────────────┘  │         │
                              └──────────┬───────────┘         │
                                         │                     │
                                         ▼                     │
                              ┌──────────────────────┐         │
                              │  MariaDB 10.6+        │◄────────┘
                              │  ┌────────────────┐  │
                              │  │ Portfolio data  │  │
                              │  │ OHLCV prices    │  │
                              │  │ Transactions    │  │
                              │  │ Backtest results│  │
                              │  │ Timing buckets  │  │
                              │  │ LLM fundamental │  │
                              │  │   data tables   │  │
                              │  │ RW screen store │  │
                              │  │ User accounts   │  │
                              │  └────────────────┘  │
                              └──────────────────────┘
```

---

## 3. Database Schema Architecture

### 3.1 Strategy: Partitioned Tables + Tiered Indicators

The legacy `stock_market` DB had ~130 tables with no partitioning and the `back_finance` DB had 21 tables — both using MyISAM with latin1 charset. The modernized schema consolidates to ~30 focused tables on InnoDB with utf8mb4, using:

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
- Calculating on every INSERT would be O(n_symbols) per insert — prohibitive
- Daily refresh is sufficient because indicator weightings change slowly (weeks/months)
- Populated by MySQL event scheduler at 10 PM ET daily (after market data refresh)
- Python cron can also populate this as an alternative to MySQL events
- `signal_weights` table stores per-symbol, per-signal-type weights that evolve over time via backtesting optimization

### 3.4 Signal Weights: Evolving Over Time

The `signal_weights` table stores optimized weights for each indicator/signal type per symbol:
- `signal_type`: e.g., `RSI_OVERSOLD`, `MACD_CROSS`, `BB_TOUCH`, `GOLDEN_CROSS`
- `weight`: Optimized weight (decreases for unreliable signals, increases for reliable ones)
- `win_rate`: Historical win rate tracked per signal per symbol
- `updated_by`: `backtest`, `manual`, or `python_ml`
- Weights start at 1.0 (default) and are refined by backtesting

### 3.5 Timing Buckets (UPDATED — FR-16)

The `timing_buckets` table captures timing dimensions per backtest trade:

| Column | Type | Meaning |
|---|---|---|
| id | bigint PK | |
| run_id | bigint FK → backtest_runs | |
| ticker | varchar(20) | |
| signal_date | date | |
| day_of_week | enum(Mon,Tue,Wed,Thu,Fri) | Day of week of entry/exit |
| day_of_month | tinyint | Day of month (1-31) |
| period_of_month | enum(early,mid,late) | Early(1-10)/Mid(11-20)/Late(21+) |
| month_of_year | tinyint | 1-12 |
| near_month_end | tinyint | Within 3 days of month end |
| near_options_expiry | tinyint | Within 3 days of monthly opex |
| outcome | enum(WIN,LOSS,HOLD) | |
| return_pct | double | Period return |
| holding_days | int | Days held |

**Aggregation queries** compute per-bucket win rate, average return, turnover, and holding period — enabling the backtest engine to report "best day to buy: Thursday, best day to sell: Tuesday" or "best period: mid-month, worst: month-end."

**Advisor timing preferences** stored per-advisor in `advisor_accounts.profile_json`:
```json
{
  "timing": {
    "preferred_entry_day": "Thursday",
    "preferred_exit_day": "Tuesday",
    "preferred_entry_period": "mid",
    "avoid_month_end_entry": true,
    "near_opex_entry": false
  }
}
```

### 3.6 LLM Fundamental Data Tables (NEW — FR-11)

| Table | Purpose | Key Columns |
|---|---|---|
| `llm_guidance` | Forward guidance extracted from earnings releases, conference calls, SEC filings | symbol, guidance_text, source, source_date, sentiment (positive/negative/neutral), confidence, llm_model, created_at |
| `llm_news` | News events with material impact assessment | symbol, headline, source, event_date, summary, material_impact (none/low/medium/high), llm_analysis, llm_model, analyzed_at, created_at |
| `llm_regulatory` | Pending/approved regulatory actions (FDA, SEC, patents) | symbol, event_type, description, status (pending/approved/denied/withdrawn), expected_date, actual_date, material_impact, llm_analysis, llm_model, created_at, updated_at |
| `llm_product_dev` | Product launches, R&D milestones, pipeline updates | symbol, product_name, stage, description, expected_date, actual_date, material_impact, llm_analysis, llm_model, created_at, updated_at |
| `llm_analysis_sessions` | Audit trail of LLM analysis runs | session_id, trigger (scheduled/manual/advisor), symbols_analyzed, total_findings, findings_written, provider_used, model_used, started_at, completed_at, error |

**LLM Read/Write pattern**:
- On scheduled run (or advisor-triggered analysis), the LLM analyzer reads all pending/unanalyzed rows from `llm_news` and new filings from `llm_guidance` / `llm_regulatory` / `llm_product_dev`
- For each item, the LLM produces a structured assessment: material impact, suggested action (hold/sell/increase/decrease/watch), reasoning
- If the LLM discovers new guidance, news, regulatory events, or product developments not yet in the tables, it writes them
- The advisor picking engine reads from these tables when scoring candidates: a pending FDA approval with high material impact boosts a biotech stock's score; negative guidance revision lowers it
- `llm_analysis_sessions` provides traceability: which model analyzed what, when, and how many findings were written

### 3.7 Zacks Research Wizard Tables (FR-14 / BR-8)

| Table | Purpose |
|---|---|
| `user_screens` | Imported `.und` screen definitions with `filters_json` (engine='zacks_rw') |
| `zacks_broker_recommendations` | Per-firm broker rows (firm, analyst, grade, price_target, action, rec_date) |
| `zacks_ratios_history` | Multi-year ratio series per symbol |
| `stock_performance_windows` | Precomputed price windows (Hermes + RW sets) |
| `fundamentals` | Zacks_* columns + valuation fundamentals + composite/rank/grades |

See `docs/requirements/FR-14-zacks-rw-pipeline.md` for full schema and calculation contracts.

### 3.8 Advisor Tables (BR-7)

| Table | Purpose |
|---|---|
| `advisor_accounts` | Advisor persona accounts (slug, display_name, strategy, profile_json) |
| `portfolio_visibilities` | Public/private visibility per user/portfolio |
| `advisor_runs` | Per-advisor run metadata (trade_date, status, result_json) |
| `advisor_trades` | Individual advisor trades (symbol, action, shares, price, commission, news_impact_json) |

See `docs/advisors/REQUIREMENTS_DESIGN.md` for full design.

## 3. Legacy Schema Comparison

| Property | `stock_market` (old) | `back_finance` (new) | `ksf_stockmarket` (modern) |
|---|---|---|---|
| Origin | Original web app | Finance/trading module | Modernized PHP app |
| Tables | ~130 (FA + legacy SQL) | 21 tables | ~30 focused tables |
| Engine | MyISAM / InnoDB mix | MyISAM mostly | InnoDB |
| Charset | latin1 | latin1 | utf8mb4 |
| Partitioned | No | No | **Yes** (prices, indicators) |
| Tier 1 (trigger) | No | No | **Yes** |
| Tier 2 (materialized) | No | No | **Yes** |
| Signal weights | No | No | **Yes** |
| Timing buckets | No | No | **Yes** (extended) |
| LLM fundamental data | No | No | **Yes** (new) |
| RW screen storage | No | No | **Yes** (new) |
| RBAC | No | No | **Yes** |

See `database-comparison.md` for detailed column-level comparison.

## 4. Component Responsibilities

### PHP Layer (Web Application)
| Component | Responsibility |
|---|---|
| Controllers | Handle HTTP requests, input validation, routing |
| Services | Business logic, orchestration |
| Models | Data access via PDO, domain objects |
| Views | Twig templates, HTML rendering |
| PythonBridge | HTTP client to Flask API |
| FA Module | FrontAccounting journal entry creation |
| LLMService | Multi-provider LLM completion with fallback chain (NEW — FR-11.6) |
| AdminSettingsController | LLM provider chain config UI (NEW — FR-11.6) |
| TimingService | Timing dimension capture and aggregation for backtests (NEW — FR-16) |
| RwFormulaService | RwFormulaParser + ZacksFieldResolver evaluation for advisor picking (NEW — FR-12) |

### Python Layer (Analysis Engine)
| Component | Responsibility |
|---|---|
| Flask API | REST endpoints for PHP bridge |
| Backtest Engine | Portfolio simulation, trade execution, metrics — timing-aware (UPDATED — FR-16) |
| TA Library | Candlestick patterns, indicators, Turtle system |
| Strategies | Motley Fool, Buffett, Combined screening |
| Fetchers | yFinance/Google/SEDAR/SEC → normalized DTOs |
| Repositories | DTO ↔ SQLite/MariaDB storage, column mapping |
| Detection | Volume/NATR/RSI/gap triggers read from local DB |
| Reports | HTML/PDF report generation |
| Advisor Notifier | Email/Discord/WhatsApp recommendation delivery |
| Risk Engine | Optional rules enforcement in backtest + live |
| RW Formula Engine | RwFormulaParser + ZacksFieldResolver for advisor picking (NEW — FR-12) |
| LLM Fundamental Analyzer | Reads/writes llm_* tables for guidance, news, regulatory, product dev (NEW — FR-11) |
| Zacks Scraper + Rank Populator | Scrapes Zacks pages, computes composite/rank/grades (FR-14) |
| RW Screen Runner | Executes imported .und screens against live universe (FR-14) |

### Database Layer
| Table Group | Tables |
|---|---|
| Portfolio | portfolio, portfolio_history, user_trades |
| Market Data | stockprices (partitioned), dividends, stockinfo |
| Tier 1 Indicators | daily_indicators (partitioned, trigger-populated) |
| Tier 2 Indicators | daily_tier2 (partitioned, daily event-populated) |
| Signal Weights | signal_weights (per-symbol, evolving) |
| Backtesting | backtest_runs, backtest_trades, backtest_periods (timing-extended), timing_buckets (timing-extended) |
| Users & RBAC | users, roles, watchlists, watchlist_symbols |
| Advisors | user_advisors, advisor_recommendations, strategy_rules, risk_rules, optional_rules, kb_articles, advisor_accounts, portfolio_visibilities, advisor_runs, advisor_trades |
| LLM Fundamental Data | llm_guidance, llm_news, llm_regulatory, llm_product_dev, llm_analysis_sessions (NEW) |
| Alerts | alerts, alerts_raised |
| Screener | tradingview_screener_results (preset_name+market+symbol unique), symbol_master |
| Zacks RW | user_screens, zacks_broker_recommendations, zacks_ratios_history, stock_performance_windows, fundamentals (zacks_* columns) |
| FA Integration | fa_transfers |
| Operations | data_import_log |

---

## 5. Technology Stack

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Web Server | Apache | 2.4+ | mod_proxy, mod_rewrite |
| Backend | PHP | 8.1+ | PSR-4 autoloading, typed |
| Backend | Python | 3.11+ | Flask, pandas, numpy |
| Database | MariaDB | 10.6+ | InnoDB, utf8mb4, partitioning |
| ORM/DBAL | PDO (native) | — | No ORM — raw PDO for performance |
| Templating | Twig | 3.x | Auto-escaping, sandboxing |
| Logging | Monolog | 3.x | PSR-3 compatible |
| Config | phpdotenv | 5.x | .env files |
| Testing | PHPUnit | 10.x | Unit + integration tests |
| Analysis | yfinance | — | Yahoo Finance data |
| Analysis | ta-lib / pandas-ta | — | Technical indicators |
| LLM | OpenRouter/OpenAI/Ollama | — | Multi-provider fallback chain (NEW) |
| RW Parser | ksfraser/research-wizard-reader | — | Formula parser, field resolver, .und parser (NEW) |
| CSS Framework | Custom/Tailwind | — | To be decided in Phase 4 |

---

## 6. Deployment Architecture

### Container Structure (via ksf_Infrastructure Ansible)

```
Pod: ksf-stockmarket
├── Container: ksf-stockmarket-web
│   ├── Apache 2.4 + PHP 8.1
│   ├── Document root: /var/www/html/public
│   └── Port: {{ http_port }} (default 8080)
├── Container: ksf-stockmarket-api
│   ├── Python 3.11 + Flask
│   ├── Port: 5000 (internal)
│   └── Gunicorn WSGI server
├── Container: ksf-stockmarket-db
│   ├── MariaDB 10.6
│   ├── Port: {{ db_port }} (default 3306)
│   └── Volume: /var/lib/mysql
└── Shared Volumes:
    ├── {{ app_dir }}:/var/www/html
    ├── {{ data_dir }}:/var/lib/mysql
    └── {{ csv_data_dir }}:/var/www/html/data/csv
```

### Ansible Recipe Requirements (from ksf_Infrastructure)
The existing recipe needs these additions:
1. Configurable ports: `{{ http_port }}`, `{{ db_port }}`
2. Named containers with prefix: `{{ app_name }}-web`, `{{ app_name }}-db`, `{{ app_name }}-api`
3. Bind mounts from host paths
4. Environment variables via `.env` file
5. Python API container (new)

---

## 7. API Contract (PHP ↔ Python)

### Endpoints

| Method | Path | Request Body | Response |
|---|---|---|---|
| POST | /api/backtest/run | strategy, params, dates, timing_buckets=true | { run_id, status } |
| GET | /api/backtest/status/{id} | — | { status, metrics } |
| GET | /api/backtest/results/{id} | — | { trades, metrics, timing_buckets } |
| POST | /api/ta/analyze | symbol, indicators | { signals, values } |
| POST | /api/screen/run | screen_type, universe | { results: [...] } |
| GET | /api/data/prices/{symbol} | ?from=&to= | { prices: [...] } |
| POST | /api/data/import | symbols[], source | { import_log } |
| GET | /api/health | — | { status: "ok" } |
| GET | api_screener | ?preset= | HTML fragment |
| GET | /api/advisor/recommendations | ?user_id=N | { recommendations: [...] } |
| GET/POST | /api/advisor/preferences | ?user_id=N | { prefs } |
| POST | /api/advisor/notifications/whatsapp/send | to, message | { message_id } |
| POST | /api/advisor/notifications/whatsapp/status | provider payload | { status } |
| POST | /api/llm/analyze | symbol, analysis_type, data | { result, provider_used } |
| GET | /api/timing/performance | ?strategy=&period= | { buckets: [...], optimal: {...} } |
| POST | /api/rw/formula/evaluate | formula, symbol_data | { result, skipped: [...] } |

---

## 8. Security Model

### Authentication
- PHP session-based authentication for web UI
- Password hashing via `password_hash()` (bcrypt)
- API key for PHP ↔ Python bridge (localhost only)
- LLM API keys stored as password-type in system_settings, never exposed to UI

### Authorization (RBAC)
| Role | Permissions |
|---|---|
| admin | Full access: manage users, run backtests, modify data, configure LLM providers, view advisor timing preferences |
| trader | View data, run backtests, manage own watchlists, run screens |
| viewer | View-only: dashboards, reports, watchlists, public advisor portfolios |

---

## 9. Migration Strategy

### Parallel Operation
The legacy PHP application runs alongside the new code during migration:
- Legacy code: untouched in original directories (`application/`, `class/`, `model/`, etc.)
- New code: under `src/` with PSR-4 autoloading
- Shared database: old tables preserved, new tables added
- Feature flags in config control which code path is active

### Migration Sequence
1. Phase 1: Foundation (this phase) — parallel structure
2. Phase 2: Core models — port `class/` and `model/` incrementally
3. Phase 3: Analysis engine — Python takes over backtesting/TA
4. Phase 4: UI — port controllers to front controller pattern
5. Phase 5: FA integration — new module
6. Phase 6: Reporting + data migration
7. Phase 7: LLM fundamental data + RW formula advisors + timing-aware backtesting (NEW)

---

## 10. Optional Python Worker Fallback

### 10.1 Problem
When the stockmarket app runs in a container, the PHP process cannot `proc_open()` a local Python interpreter. To preserve the existing bare-metal behaviour while supporting containerized deployments, controllers now use a curl-fallback to a FastAPI worker.

### 10.2 Worker Endpoint
`POST /worker/refresh_prices` accepts:
- `symbol` — single ticker to fetch/update
- `full_history` — boolean; bypass day calc
- `days` — optional day window

The worker shells out to `fetch_prices.py` and returns HTTP status.

### 10.3 Configuration
| Variable | Purpose | Default |
|---|---|---|
| `PYTHON_WORKER_URL` | URL of FastAPI worker | unset (bare metal uses `proc_open`) |
| `WORKER_PORT` | Worker container port | `8000` |
| `STOCKMARKET_PYTHON_DIR` | Host path mounted into the worker container | `/home/ksf_stockmarket/ksf_stockmarket/python` |

### 10.4 Container Deployment (optional)
`ksf_Infrastructure` defines an optional service `stockmarket-python-worker` on profile `stockmarket`. Enable via Ansible with `enable_stockmarket_python_worker=true` or via Podman Compose with `--profile stockmarket`.

---

## 11. Methodology Alignment (BABOK / PMBOK)

### 11.1 Knowledge Area Mapping

| System Capability | BABOK Knowledge Area | PMBOK Process Group | Primary Artifacts |
|---|---|---|---|
| Portfolio tracking + taxonomies | Business Analysis Planning and Monitoring, Requirements Analysis | Planning, Executing | `requirements-specification.md`, `traceability-matrix.md`, `architecture-document.md` |
| Advisor hiring + recommendations | Requirements Analysis, Solution Evaluation | Planning, Executing, Monitoring | `business-requirements.md`, `solution-design.md`, advisor migrations/backends |
| T+2 settlement + cash flow | Requirements Analysis, Solution Assessment and Validation | Executing, Monitoring and Controlling | `strategy_pipeline.py`, `runner.py`, `rules_backtest.py` |
| Optional risk rules (leverage/buffer/blacklist) | Requirements Analysis, Solution Evaluation | Planning, Executing | `strategy_rules` schema seeds, `AdminSettingsController` |
| ATR trailing stops + backtest | Requirements Analysis, Solution Assessment and Validation | Planning, Executing | `risk.py`, `rules_backtest.py`, `atr_methodology.php` |
| Multi-gateway delivery (email/Discord/WhatsApp) | Requirements Analysis, Solution Evaluation | Executing, Monitoring and Controlling | `advisor_notifier.py`, `AdvisorNotificationController` |
| Heat maps + performance reports | Requirements Analysis, Solution Assessment and Validation | Planning, Executing | `performance.py`, `reports.php` template |
| Rebalancing workflows | Requirements Analysis, Solution Evaluation | Planning, Executing | `rebalancing.py`, `RebalancingController` |
| LLM admin console + fallback chain | Requirements Analysis, Solution Evaluation | Planning, Executing | `AdminSettingsController`, `LLMService`, FR-11.6 |
| LLM fundamental data tables | Requirements Analysis, Solution Evaluation | Planning, Executing | `llm_*` tables, FR-11 |
| Timing-aware backtesting | Requirements Analysis, Solution Assessment and Validation | Planning, Executing | `TimingService`, FR-16 |
| Research Wizard formula advisors | Requirements Analysis, Solution Evaluation | Planning, Executing | `RwFormulaParser`, `ZacksFieldResolver`, FR-12 |

### 11.2 BABOK Alignment Summary

- **Strategy Analysis**: requirements/BRD, stakeholder elicitation captured in `business-requirements.md` BR-1..BR-9.
- **Requirements Analysis**: formalized in `requirements-specification.md` with FR/NFR IDs aligned to BR traceability, including FR-11 (LLM data), FR-12 (RW formulas), FR-16 (timing), FR-14 (Zacks RW).
- **Solution Assessment and Validation**: ATR methodology, backtest results, timing analysis, and T+2 settlement validation feed acceptance criteria.
- **Business Analysis Planning and Monitoring**: documentation versioning, change log, traceability matrix maintained in `docs/`.

### 11.3 PMBOK Alignment Summary

- **Scope Management**: PortfolioPerformance parity target list = formal scope baseline; traceability matrix links requirements to design and tests.
- **Schedule Management**: nightly cron, weekly backtest cadence, and advisor daily signal cadence modeled as scheduled deliverables.
- **Cost Management**: backtest simulation validates capital-at-risk rules before live deployment.
- **Quality Management**: validation scripts, syntax checks, schema migrations, and RW formula parser unit tests enforce build quality.
- **Risk Management**: emergency buffer, leverage/margin rules, ATR stops, and LLM fallback chain are formal risk response strategies.

### 11.4 Supporting Diagrams

Architecture UML views are in `docs/methodology/uml/`:
- `deployment.puml` — deployment context
- `class.puml` — core class diagram
- `sequence.puml` — advisor recommendation sequence
- `state.puml` — alert lifecycle state machine
- `activity.puml` — daily run activity flow

All diagrams map to the knowledge areas and process groups above.
