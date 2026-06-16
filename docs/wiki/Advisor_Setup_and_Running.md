[[Category: ksf_stockmarket]]
# Advisor Setup and Running

This page documents how to create, configure, and run the AI advisor accounts from the `ksf_stockmarket` repo.

## Prerequisites
- MariaDB reachable at `ksfraser.ca:3306`
- Database: `ksfraser_stock_market`
- App bootstrap available: `local.php` / `Local_Init()`
- Python deps installed in the repo venv

## 1. Create advisor accounts

Run the PHP bootstrap script:
```
php scripts/bootstrap_advisors.php
```

Optional flags:
```
php scripts/bootstrap_advisors.php --slug=warren-buffet --reset
```

Each advisor account:
- gets a normal user record
- gets an `advisor_accounts` row
- gets `portfolio_visibilities` set to public
- starts with 100,000 CAD deposited on 2025-01-02

## 2. Run an advisor for one date

Use the Python runner with `--date` and `--slug`:
```
cd /home/ksf_stockmarket/ksf_stockmarket
source .venv/bin/activate
PYTHONPATH=python/src:$PYTHONPATH python -m advisors.advisor_runner --date=2025-05-16 --slug=warren-buffet --dry-run
```

Flags:
- `--date=YYYY-MM-DD` required for reproducible runs
- `--slug=` limits to one advisor
- omit `--dry-run` to persist trades

## 3. Run all advisors for a date
```
python -m advisors.advisor_runner --date=2025-05-16
```

## 4. Weekly variants
Weekly advisor slugs run only on their weekday:
```
Weekly_Monday, Weekly_Tuesday, Weekly_Wednesday, Weekly_Thursday, Weekly_Friday
```

Eligibility is enforced by `advisor_eligible()`.

## 5. Queue / screener integration
If `select_universe()` returns symbols that do not yet have price/TA data for the requested date, the runner enqueues:
- `event_type=screener_symbols_ingested`
- payload: `slug`, `symbol`, `trade_date`

The existing queue worker consumes `event_queue` and runs the screener ingestion workflow before the advisor continues to the next date.

## 6. Live pages
- `Stockmarket_App`: app KB hub with links to this page and other wiki articles

No API keys/tokens are included in this documentation.
