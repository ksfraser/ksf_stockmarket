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

## 3. Component Responsibilities

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
| Portfolio         | portfolio, portfolio_history, transactions          |
| Market Data       | stockprices, dividends, stockinfo                   |
| Analysis          | tenets, backtest_runs, backtest_trades              |
| Users & RBAC      | users, roles, watchlists, watchlist_symbols         |
| FA Integration    | fa_transfers                                        |
| Operations        | data_import_log                                     |

## 4. Technology Stack

| Layer        | Technology         | Version  | Notes                              |
|--------------|--------------------|----------|------------------------------------|
| Web Server   | Apache             | 2.4+     | mod_proxy, mod_rewrite             |
| Backend      | PHP                | 8.1+     | PSR-4 autoloading, typed           |
| Backend      | Python             | 3.11+    | Flask, pandas, numpy               |
| Database     | MariaDB            | 10.6+    | InnoDB, utf8mb4                   |
| ORM/DBAL     | PDO (native)       | —        | No ORM — raw PDO for performance   |
| Templating   | Twig               | 3.x      | Auto-escaping, sandboxing          |
| Logging      | Monolog            | 3.x      | PSR-3 compatible                   |
| Config       | phpdotenv          | 5.x      | .env files                         |
| Testing      | PHPUnit            | 10.x     | Unit + integration tests           |
| Analysis     | yfinance           | —        | Yahoo Finance data                 |
| Analysis     | ta-lib / pandas-ta | —        | Technical indicators               |
| CSS Framework| Custom/Tailwind    | —        | To be decided in Phase 4           |

## 5. Deployment Architecture

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

## 6. API Contract (PHP ↔ Python)

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

## 7. Security Model

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

## 8. Migration Strategy

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
