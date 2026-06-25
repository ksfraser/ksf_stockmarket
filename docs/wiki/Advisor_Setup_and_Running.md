[[Category: ksf_stockmarket]]
# Advisor Setup and Running

This page documents how to create, configure, and run the AI advisor accounts from the `ksf_stockmarket` repo.

## Prerequisites
- MariaDB reachable at `ksfraser.ca:3306`
- Database: `ksfraser_stock_market`
- App bootstrap available: `local.php` / `Local_Init()`
- Python deps installed in the repo venv

## 1. Create advisor accounts

Create accounts by inserting rows in `users` + `user_settings`:

```sql
INSERT INTO users (username, email, password_hash, display_name, role, is_active)
VALUES ('warren-buffet', 'warren-buffet@example.com', '<bcrypt>', 'Warren Buffett', 'advisor', 1);
SET @uid := LAST_INSERT_ID();
INSERT INTO user_settings (user_id, setting_key, setting_value) VALUES (@uid, 'advisor_strategy', 'buffett_quality');
```

### Built-in advisor strategies
- `buffett_quality`
- `dividend_growth`
- `momentum`
- `sector`
- `bond_basket`
- `balanced_fund`

Sector advisors also require `advisor_sector`; balanced fund advisors use fixed 60/40 allocation; bond basket advisors track `[TBIL.TO, ZGB.TO, HMP.TO, ZAG.TO]`.

The legacy `advisor_accounts` table is **no longer used**; advisors are normal users with `role='advisor'` and strategy metadata in `user_settings`.

**Legacy bootstrap (still available):**
```bash
php scripts/bootstrap_advisors.php
```
Optional flags:
```bash
php scripts/bootstrap_advisors.php --slug=warren-buffet --reset
```

## 2. Run an advisor for one date

Use the Python runner with `--date` and `--slug`:
```bash
cd /home/ksf_stockmarket/ksf_stockmarket
source .venv/bin/activate
PYTHONPATH=python/src:$PYTHONPATH python -m advisors.runner --date=2025-05-16 --slug=warren-buffet --dry-run
```

Flags:
- `--date=YYYY-MM-DD` required for reproducible runs
- `--slug=` limits to one advisor
- omit `--dry-run` to persist trades

## 3. Run all advisors for a date
```bash
PYTHONPATH=python/src:$PYTHONPATH python -m advisors.runner --date=YYYY-MM-DD
```

## 4. Live pages
- `Stockmarket_App`: app KB hub with links to this page and other wiki articles

No API keys/tokens are included in this documentation.
