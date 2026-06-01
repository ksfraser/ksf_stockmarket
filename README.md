# ksf_stockmarket

Stock market analysis and portfolio tracking tool — hybrid PHP web dashboard + Python analysis engine.

## Architecture

- **PHP 8.1+** — Web dashboard (portfolio, detail, transactions, strategies, auth)
- **Python 3.11+** — Analysis engine, backtesting, technical analysis, DB adapter layer
- **MySQL (MariaDB)** — Price data, portfolio, transactions (hosted at ksfraser.ca)
- **Apache + PHP-FPM** — Serves web dashboard at `/stockmarket/` and `/dashboard/`

## Live URLs

- **Dashboard:** `http://192.168.1.102/stockmarket/` (or `/dashboard/`)
- **Login:** `http://192.168.1.102/stockmarket/?action=login` (default: admin / admin123)
- **My Dashboard:** `?action=my_dashboard` (buy/sell recs, earnings, dividends)
- **Portfolio:** `?action=portfolio` (holdings with annualized P&L, stops, strategy)
- **Transactions:** `?action=transactions` (filterable history)
- **Strategies:** `?action=strategy_stock` (backtested selection strategies)
- **Risk Mgmt:** `?action=strategy_money` (Kelly criterion, stops, sleeves)
- **Settings:** `?action=settings` (color scheme, password)

## Directory Structure

```
ksf_stockmarket/                   ← Git repo root (Python + docs)
  docs/                            ← Architecture & requirements
    ARCHITECTURE.md                ← Complete system spec (v5.0)
    ARCHITECTURE_v4.md             ← v4 adaptive architecture
    requirements/                  ← Business requirements & traceability
    STOCK_SELECTION_STRATEGIES.md  ← Strategy backtest results
    STRATEGY_REFERENCE.md          ← Trading tactics reference
  python/                          ← Python analysis engine
    daily_pipeline.py              ← Price fetcher (optimized)
    db/                            ← DB adapter layer (abstract + MySQL + SQLite)
    requirements.txt               ← Python dependencies
  tests/                           ← pytest suite
    unit/test_db_adapter.py        ← 18 passing DB adapter tests
    conftest.py                    ← Fixtures
  pyproject.toml                   ← Python project config
  config.yaml                      ← DB connection config

/var/www/stockmarket-app/          ← PHP workspace (authoritative source)
  index.php                        ← Front controller (routes all requests)
  src/Controller/
    DashboardController.php        ← App dashboard (overview)
    StockController.php            ← Symbol list, detail, portfolio
    TransactionController.php      ← Transaction history with filters
    StrategyController.php         ← Backtested strategy results
    UserController.php             ← My Dashboard + Settings
    AuthController.php             ← Login/logout/session + remember-me
    SymbolAdminController.php      ← Symbol activation/deactivation
    FundamentalsController.php     ← Fundamental data fetcher
  src/Model/Database.php           ← PDO singleton
  src/View/helpers.php             ← Template helper functions
  templates/                       ← PHP templates
    layout.php                     ← Main layout with nav
    overview.php                   ← App dashboard
    my_dashboard.php               ← Personal dashboard
    portfolio.php                  ← Enhanced holdings table
    detail.php                     ← Symbol detail with charts
    transactions.php               ← Transaction history
    strategy_stock.php             ← Stock selection strategies
    strategy_money.php             ← Money/risk management
    settings.php                   ← User preferences
    login.php                      ← Login form
  config/database.php              ← DB credentials

/var/www/html/stockmarket/         ← Apache web root (rsync from workspace)
/var/www/html/dashboard-owl/       ← /dashboard/ alias
```

## Key Backtest Results

| Strategy | Win Rate | Profit Factor | Max Drawdown |
|---|---|---|---|
| Candlestick Patterns | 12% | 0.82 | -24.3% |
| Oscillators (RSI/MACD/Stoch) | 44% | 1.31 | -14.7% |
| Neural Network Directional | 53.1% | 1.42 | -11.2% |
| Ensemble Blend | 51.4% | 1.58 | -9.1% |
| Kelly + Win Rate Inversion | Varies | 1.72 | -6.8% |

## Database (MySQL at ksfraser.ca)

- **Database:** `ksfraser_stock_market`
- **Key tables:** stockprices (135K rows), indicators_json (126K rows), symbol_master (404), portfolio (23)
- **Python DB adapter:** Abstract `DBConnection` with MySQL + SQLite implementations, 18 tests passing

## Setup

### PHP (Web Dashboard)
```bash
cd /var/www/stockmarket-app
composer install
# Edit config/database.php with credentials
# Apache serves from /var/www/html/stockmarket/ (rsync from workspace)
```

### Python
```bash
cd /home/ksf_stockmarket/ksf_stockmarket
pip install -r python/requirements.txt
pip install -e .
pytest tests/  # 18 DB adapter tests pass
```

### Sync to Web Root
```bash
rsync -av --include="*.php" --include="*/" --exclude="*" \
  /var/www/stockmarket-app/ /var/www/html/stockmarket/
```

## Development

### Running Tests
```bash
# Python
pytest tests/unit/test_db_adapter.py -v

# PHP (when PHPUnit is configured)
./vendor/bin/phpunit
```

### Code Style
- PHP: PSR-4, `declare(strict_types=1)`, SOLID, DI
- Python: Type hints, abstract classes, config-driven factories

## Authentication
- Session-based PHP auth with `user_sessions` table for remember-me (30-day cookies)
- Default admin: `admin` / admin123` (change on first login)
- Per-user settings: color scheme, font size, compact tables, decimal places, date format

## License

Proprietary — Kevin Fraser / K.S. Fraser Inc.
