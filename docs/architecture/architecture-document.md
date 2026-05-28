# Architecture Document

## 1. System Overview

KSF Stock Market Analysis is a hybrid PHP + Python application for:
- Portfolio tracking and management
- Technical and fundamental analysis
- Strategy backtesting
- Seg fund screening
- FrontAccounting integration

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
                              │  │ Strategies     │  │         │
                              │  │ Data Import    │  │         │
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
                              │  │ User accounts   │  │
                              │  └────────────────┘  │
                              └──────────────────────┘
```

## 3. Database Schema Architecture

### 3.1 Strategy: Partitioned Tables + Tiered Indicators

The legacy `stock_market` DB had ~130 tables with no partitioning and the `back_finance` DB had 21 tables — both using MyISAM with latin1 charset. The modernized schema consolidates to ~25 focused tables on InnoDB with utf8mb4, using:

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

This means the system learns which indicators work best for each stock over time, rather than using fixed thresholds.

### 3.5 Backup Strategy

Each partition is backed up independently:
```bash
# Full backup: one file per year
for year in $(seq 2008 2026); do
  mysqldump --single-transaction --where "YEAR(price_date)=${year}" \
    ksf_stockmarket stockprices > stockprices_${year}.sql
done

# Incremental: today's partition only
mysqldump --single-transaction --where "YEAR(price_date)=YEAR(CURDATE())" \
  ksf_stockmarket stockprices > stockprices_current.sql

# Tier tables (small, full dump)
mysqldump ksf_stockmarket daily_indicators daily_tier2 signal_weights > indicators.sql
```

## 3. Legacy Schema Comparison

| Property | `stock_market` (old) | `back_finance` (new) | `ksf_stockmarket` (modern) |
|---|---|---|---|
| Origin | Original web app | Finance/trading module | Modernized PHP app |
| Tables | ~130 (FA + legacy SQL) | 21 tables | ~25 focused tables |
| Engine | MyISAM / InnoDB mix | MyISAM mostly | InnoDB |
| Charset | latin1 | latin1 | utf8mb4 |
| Partitioned | No | No | **Yes** (prices, indicators) |
| Tier 1 (trigger) | No | No | **Yes** |
| Tier 2 (materialized) | No | No | **Yes** |
| Signal weights | No | No | **Yes** |
| RBAC | No | No | **Yes** |

See `database-comparison.md` for detailed column-level comparison.

## 4. Component Responsibilities

### PHP Layer (Web Application)
| Component    | Responsibility                                      |
|--------------|-----------------------------------------------------|
| Controllers  | Handle HTTP requests, input validation, routing     |
| Services     | Business logic, orchestration                       |
| Models       | Data access via PDO, domain objects                |
| Views        | Twig templates, HTML rendering                      |
| PythonBridge | HTTP client to Flask API                            |
| FA Module    | FrontAccounting journal entry creation              |

### Python Layer (Analysis Engine)
| Component       | Responsibility                                      |
|-----------------|-----------------------------------------------------|
| Flask API       | REST endpoints for PHP bridge                       |
| Backtest Engine | Portfolio simulation, trade execution, metrics      |
| TA Library      | Candlestick patterns, indicators, Turtle system     |
| Strategies      | Motley Fool, Buffett, Combined screening            |
| Data Import     | CSV ingestion, yfinance integration                 |
| Reports         | HTML/PDF report generation                          |

### Database Layer
| Table Group       | Tables                                               |
|-------------------|------------------------------------------------------|
| Portfolio         | portfolio, portfolio_history, user_trades           |
| Market Data       | stockprices (partitioned), dividends, stockinfo     |
| Tier 1 Indicators | daily_indicators (partitioned, trigger-populated)   |
| Tier 2 Indicators | daily_tier2 (partitioned, daily event-populated)   |
| Signal Weights    | signal_weights (per-symbol, evolving)               |
| Backtesting       | backtest_runs, backtest_trades                      |
| Users & RBAC      | users, roles, watchlists, watchlist_symbols         |
| Alerts            | alerts, alerts_raised                               |
| FA Integration    | fa_transfers                                        |
| Operations        | data_import_log                                     |

## 5. Technology Stack

| Layer        | Technology         | Version  | Notes                              |
|--------------|--------------------|----------|------------------------------------|
| Web Server   | Apache             | 2.4+     | mod_proxy, mod_rewrite             |
| Backend      | PHP                | 8.1+     | PSR-4 autoloading, typed           |
| Backend      | Python             | 3.11+    | Flask, pandas, numpy               |
| Database     | MariaDB            | 10.6+    | InnoDB, utf8mb4, partitioning      |
| ORM/DBAL     | PDO (native)       | —        | No ORM — raw PDO for performance   |
| Templating   | Twig               | 3.x      | Auto-escaping, sandboxing          |
| Logging      | Monolog            | 3.x      | PSR-3 compatible                   |
| Config       | phpdotenv          | 5.x      | .env files                         |
| Testing      | PHPUnit            | 10.x     | Unit + integration tests           |
| Analysis     | yfinance           | —        | Yahoo Finance data                 |
| Analysis     | ta-lib / pandas-ta | —        | Technical indicators               |
| CSS Framework| Custom/Tailwind    | —        | To be decided in Phase 4           |

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

## 7. API Contract (PHP ↔ Python)

### Endpoints

| Method | Path                       | Request Body              | Response           |
|--------|----------------------------|---------------------------|--------------------|
| POST   | /api/backtest/run          | strategy, params, dates   | { run_id, status } |
| GET    | /api/backtest/status/{id}  | —                         | { status, metrics }|
| GET    | /api/backtest/results/{id} | —                         | { trades, metrics }|
| POST   | /api/ta/analyze            | symbol, indicators        | { signals, values }|
| POST   | /api/screen/run            | screen_type, universe     | { results: [...] } |
| GET    | /api/data/prices/{symbol}  | ?from=&to=                | { prices: [...] }  |
| POST   | /api/data/import           | symbols[], source         | { import_log }     |
| GET    | /api/health                | —                         | { status: "ok" }   |

## 8. Security Model

### Authentication
- PHP session-based authentication for web UI
- Password hashing via `password_hash()` (bcrypt)
- API key for PHP ↔ Python bridge (localhost only)

### Authorization (RBAC)
| Role    | Permissions                                              |
|---------|----------------------------------------------------------|
| admin   | Full access: manage users, run backtests, modify data    |
| trader  | View data, run backtests, manage own watchlists          |
| viewer  | View-only: dashboards, reports, watchlists               |

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
