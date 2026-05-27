# ksf_stockmarket

Stock market analysis and portfolio tracking tool.

## Architecture

- **PHP 8.1+** — Web UI, controllers, views, FA integration
- **Python 3.11+** — Analysis engine, backtesting, technical analysis
- **MariaDB** — Price data, portfolio, transactions
- **Apache** — Serves PHP, proxies `/api/*` to Python Flask service

## Directory Structure

```
src/Controller/    — Request handlers
src/Model/          — Domain models, DB access
src/Service/        — Business logic layer
src/TA/             — Technical analysis (candlesticks, Turtle, indicators)
src/Module/         — FrontAccounting integration
src/View/           — Templates
python/             — Python analysis engine
    backtest_engine/  — Backtesting framework
    data_import/      — CSV/yfinance data pipeline
    reports/          — Report generation
    api/              — Flask API for PHP bridge
database/           — Schema and migrations
data/csv/           — Historical price data (migrated from currentdata/)
docs/               — Project documentation (BABOK format)
tests/              — PHPUnit tests
public/             — Web root (index.php front controller)
scripts/            — CLI scripts, cron jobs
config/             — Application configuration
```

## Setup

### PHP Dependencies
```bash
composer install
```

### Python Dependencies
```bash
cd python && pip install -r requirements.txt
```

### Database
```bash
# Run schema
mysql -u root -p < database/schema.sql

# Run migrations
php scripts/migrate.php
```

### Configuration
```bash
cp config/.env.example config/.env
# Edit config/.env with your DB credentials, API keys
```

### Apache
Point document root to `public/`. The included `.htaccess` routes all requests
to `index.php` (front controller pattern). API requests to `/api/*` are
proxied to the Flask service on `127.0.0.1:5000`.

### Python API Service
```bash
cd python/api
python app.py
# Or via systemd: systemctl start ksf-stockmarket-api
```

## Development

### Running Tests
```bash
./vendor/bin/phpunit
```

### Code Style
```bash
./vendor/bin/php-cs-fixer fix --dry-run --diff
```

### Static Analysis
```bash
./vendor/bin/phpstan analyse src/ --level=8
```

## FrontAccounting Integration

The FA module (`src/Module/FrontAccounting.php`) creates journal entries for:
- Savings → Brokerage transfers
- Asset revaluation (unrealized gains/losses)

Stock price data lives in MariaDB, **not** in FA tables. The only FA interaction
is journal entries for transfers and revaluations.

## License

Proprietary — Kevin Fraser / K.S. Fraser Inc.
