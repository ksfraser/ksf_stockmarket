# ksf_stockmarket Repository Analysis & Modernization Plan
Analysis date: 2026-05-25

## Current State Assessment

### Repository Stats
- **1111 PHP files** — no autoloading, no namespaces, pre-PSR
- **1997 CSV files** — historical price data for ~2000 symbols
- **MySQL schema** — portfolio, stock prices, financial statements, transactions
- **Backtesting engine** — PHP classes for buy-and-hold, candlestick strategies
- **TA code** — candlestick pattern recognition, Turtle trading system
- **Financial reports** — scraped from old Google Finance API
- **Dependencies** — PEAR, Log4php, no Composer

### Directory Structure (current)
```
application/       — MVC app layer
backtest/          — Strategy backtesting engine (PHP)
class/             — Old-style PHP classes (.php.cpp extension)
controller/        — Request handlers
currentdata/       — CSV price data + symbol lists (~2000 symbols)
css/               — Stylesheets
external/          — Third-party libs
fin_reports/       — Scraped financial statements
images/
jobs/              — Cron jobs
logs/
model/             — DB access layer
modules/           — Feature modules
reports/           — Generated reports
scripts/           — SQL scripts, candlestick processing
setup/             — DB schema (stocks.sql)
wiki/              — Documentation (XFDF)
invest.conf        — App config
app.ini            — Simple key-value config
```

### Key Files
- `backtest/backtest.class.php` (1165 lines) — Main backtest engine
- `backtest/buyhold.class.php` — Buy-and-hold strategy
- `setup/stocks.sql` — Full DB schema
- `class/*.php.cpp` — Domain classes (portfolio, transactions, alerts)
- `model/include_all.php` — Manual class loading
- `jobs/` — Cron-based data loading

### Database Schema (from stocks.sql)
- `portfolio` — symbol, shares, cost
- `stockprices` — OHLCV data per symbol/date
- `dividends` — Dividend records
- `stockinfo` — Company metadata
- `transactions` — Buy/sell transactions
- `portfolio_history` — Portfolio value over time
- `financial_statements` — Scraped financial data

## Proposed Modernization

### Architecture: Hybrid PHP + Python

**Recommendation: PHP for UI/FA integration, Python for analysis engine.**

Rationale:
1. Python's data science ecosystem (pandas, numpy, yfinance, scipy) is vastly superior
2. PHP is well-suited for web UI, FA module integration, RBAC
3. Rewriting 15 years of analysis logic in PHP would be regressive
4. The existing backtesting/Turtle logic can be ported incrementally

### Directory Structure (proposed)

```
ksf_stockmarket/
├── composer.json              — Composer autoloading
├── phpunit.xml                — Test configuration
├── README.md
├── docs/                      — Project documentation (BABOK style)
│   ├── requirements/
│   ├── architecture/
│   ├── user-stories/
│   └── test-plans/
│
├── config/
│   ├── db.php                 — Database configuration
│   ├── app.php                — App settings
│   └── services.php           — Service definitions
│
├── src/                       — PHP code (PSR-4 autoloaded)
│   ├── Controller/            — Request handlers
│   ├── Model/                 — Domain models, DB access
│   │   ├── Portfolio.php
│   │   ├── Stock.php
│   │   ├── Transaction.php
│   │   └── BacktestResult.php
│   ├── Service/               — Business logic
│   │   ├── PortfolioService.php
│   │   ├── BacktestService.php
│   │   ├── DataImportService.php
│   │   └── PythonBridge.php   — Calls Python scripts
│   ├── View/                  — Templates
│   ├── TA/                    — Technical analysis
│   │   ├── Candlestick.php
│   │   ├── TurtleSystem.php
│   │   └── Indicators.php
│   └── Module/                — FA integration
│       └── FrontAccounting.php
│
├── python/                    — Python analysis engine
│   ├── requirements.txt
│   ├── backtest_engine/       — From hermes investment-agent
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── strategies/
│   │   │   ├── motley_fool.py
│   │   │   ├── buffett.py
│   │   │   └── turtle.py
│   │   └── screens/
│   ├── data_import/           — CSV price data loader
│   ├── reports/               — Report generation
│   └── api/                   — Flask API for PHP bridge
│       └── app.py
│
├── database/
│   ├── schema.sql             — Modernized schema
│   ├── migrations/            — DB migration scripts
│   └── seeds/                 — Reference data
│
├── data/                      — Price data
│   ├── csv/                   — Migrated from currentdata/
│   └── cache/                 — yfinance cache
│
├── tests/                     — PHPUnit tests
│   ├── Unit/
│   └── Integration/
│
├── public/                    — Web root
│   ├── index.php              — Front controller
│   ├── assets/                — CSS, JS, images
│   └── api/                   — API endpoint
│
└── scripts/                   — CLI scripts, cron jobs
    ├── import_prices.py
    ├── run_backtest.py
    └── cron/
```

### Database Schema Changes

Keep existing tables, add new ones:

```sql
-- Existing tables (keep as-is for data migration)
-- portfolio, stockprices, dividends, stockinfo, transactions, portfolio_history

-- New tables for modernized features
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(255),
    password_hash VARCHAR(255),
    role ENUM('admin', 'trader', 'viewer') DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE watchlists (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(64) NOT NULL,
    UNIQUE(user_id, name)
);

CREATE TABLE watchlist_symbols (
    watchlist_id INTEGER NOT NULL REFERENCES watchlists(id),
    symbol VARCHAR(16) NOT NULL,
    added_date DATE NOT NULL,
    PRIMARY KEY (watchlist_id, symbol)
);

CREATE TABLE backtest_runs (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    strategy VARCHAR(64) NOT NULL,
    parameters TEXT,  -- JSON
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(15,2),
    final_value DECIMAL(15,2),
    total_return DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    status ENUM('pending', 'running', 'complete', 'error'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fa_transfers (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    fa_journal_id INTEGER,
    from_account VARCHAR(32),
    to_account VARCHAR(32),
    amount DECIMAL(15,2),
    trade_date DATE,
    description TEXT,
    reconciled BOOLEAN DEFAULT FALSE
);
```

### Migration Plan (Phased)

#### Phase 1: Foundation (Week 1-2)
1. Set up Composer with PSR-4 autoloading
2. Create `src/` directory structure
3. Migrate DB schema (keep old tables, add new)
4. Set up PHPUnit
5. Create Project Docs directory (BABOK format)
6. Keep existing code working alongside new structure

#### Phase 2: Core Models (Week 3-4)
1. Port `class/*.php.cpp` to `src/Model/` with namespaces
1. Port `model/` DB layer to use PDO/ORM
2. Create `src/Service/` business logic layer
3. Write unit tests for core models
4. Migrate CSV data to yfinance-backed data pipeline

#### Phase 3: Analysis Engine (Week 5-6)
1. Install Python alongside PHP (same container or sidecar)
2. Port existing Python backtesting from `hermes/investment-agent`
3. Create Python API (Flask) for PHP to call
4. Bridge: `PythonBridge.php` calls Flask API
5. Port TA code: candlestick patterns, Turtle system

#### Phase 4: UI Modernization (Week 7-8)
1. Port `controller/` to new `src/Controller/`
2. Update views (Twig or plain PHP templates)
3. Add RBAC (user roles: admin, trader, viewer)
4. Portfolio tracking UI
5. Backtest results viewer

#### Phase 5: FA Integration (Week 9-10)
1. Study FrontAccounting module API
2. Implement `src/Module/FrontAccounting.php`
3. Track: savings → brokerage transfers, asset revaluation
4. Stock data in MariaDB (not FA tables)
5. Only FA tie-in: journal entries for transfers, revaluations
6. Ensure existing FA pod recipe works with new app

#### Phase 6: Data & Reporting (Week 11-12)
1. Migrate 1997 CSV files to unified data pipeline
2. Validate old data against yfinance
3. Build report generation (PDF/HTML)
4. Cron jobs for data refresh
5. Historical backtesting on full dataset

### Apache + Python Integration

Apache can run Python via several methods:

**Option A: mod_proxy to Flask (RECOMMENDED)**
```apache
# Apache config
ProxyPass /api http://127.0.0.1:5000
ProxyPassReverse /api http://127.0.0.1:5000
```
PHP calls `http://localhost/api/backtest` etc. Clean separation.

**Option B: mod_wsgi**
Run Python WSGI app directly in Apache process. Tighter coupling.

**Option C: CLI via exec()**
PHP calls `python3 script.py --args` and parses JSON output. Simple but slow.

**Recommendation: Option A.** PHP handles web UI, session, RBAC. Python handles all math/data. They communicate via HTTP API on localhost. If the Python API is down, the PHP UI still works for viewing existing data.

### FA Pod Recipe Updates

The existing `ksfraser/ksf_Infrastructure` Ansible recipe needs:
1. **Configurable ports** — Pass `{{ http_port }}`, `{{ db_port }}` as vars
2. **Named containers** — `{{ app_name }}-web`, `{{ app_name }}-db`
3. **Bind mounts** — `{{ data_dir }}:/var/lib/mysql`, `{{ app_dir }}:/var/www/html`
4. **Multi-service** — Add Python API container (`{{ app_name }}-api`)
5. **Environment variables** — DB credentials, API keys via `.env` file

### Key Decisions Needed

1. **PHP version target?** PHP 8.2+ recommended (Heroku/Fedora 36 has 8.1+)
2. **PHP framework?** Plain PHP with PSR-4, or Laravel/Symfony?
   → Recommendation: Plain PHP + PSR-4. Simpler, matches existing skill set.
3. **Python API framework?** Flask (lightweight) vs FastAPI (modern)?
   → Recommendation: Flask. Simpler, well-documented, easy to containerize.
4. **FA module language?** PHP (native FA modules are PHP)
   → Yes, FA module must be PHP.
5. **Data migration strategy?** Keep old tables or fresh start?
   → Keep old tables, create new ones alongside. Migrate incrementally.
6. **Containerize?** Docker/podman for the pod?
   → Yes, extend existing Ansible recipe to deploy full stack.

### Immediate Next Steps

1. [ ] Create `composer.json` with PSR-4 autoloading
2. [ ] Set up `src/` directory with namespaces
3. [ ] Create `docs/` directory (BABOK format)
4. [ ] Modernize `setup/stocks.sql` with new tables
5. [ ] Install Python + Flask alongside Apache
6. [ ] Create `PythonBridge.php` service
7. [ ] Move `hermes/investment-agent` Python code into `python/`
8. [ ] Update FA Ansible recipe for ports/volumes
