[[Category: ksf_stockmarket]]
# Advisor Setup and Running

This page documents how to create, configure, run, and receive notifications from
advisor accounts in the `ksf_stockmarket` repo.

## Prerequisites
- MariaDB reachable at `ksfraser.ca:3306`
- Database: `ksfraser_stock_market`
- App bootstrap available: `local.php` / `Local_Init()`
- Python deps installed in the repo venv
- Env vars for notifications: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `DISCORD_BOT_TOKEN`, `DISCORD_ALERT_WEBHOOK`

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
- `vectorvest_safe`, `vectorvest_valuation`
- `vectorvest_valuation`

Sector advisors also require `advisor_sector`; balanced fund advisors use fixed 60/40 allocation; bond basket advisors track `[TBIL.TO, ZGB.TO, HMP.TO, ZAG.TO]`.

The legacy `advisor_accounts` table is **no longer used**; advisors are normal users with `role='advisor'` and strategy metadata in `user_settings`.

**Legacy bootstrap (still available):**
```bash
php scripts/bootstrap_advisors.php
```

## 2. Hire an advisor (PHP UI)

Navigate to `?action=hire_advisors` to browse active advisors.

Hiring actions:
```sql
INSERT INTO user_advisors (user_id, advisor_id, is_active) VALUES (:user_id, :advisor_id, 1)
ON DUPLICATE KEY UPDATE is_active = 1;
```

Pause:
```sql
UPDATE user_advisors SET is_active = 0 WHERE user_id = :user_id AND advisor_id = :advisor_id;
```

Fire:
```sql
DELETE FROM user_advisors WHERE user_id = :user_id AND advisor_id = :advisor_id;
```

## 3. Run an advisor for one date

Use the Python runner with `--date` and `--slug`:
```bash
cd /home/ksf_stockmarket/ksf_stockmarket
source .venv/bin/activate
PYTHONPATH=python/src:$PYTHONPATH python -m advisors.runner --date=YYYY-MM-DD --slug=warren-buffet --dry-run
```

Flags:
- `--date=YYYY-MM-DD` required
- `--slug=` limits to one advisor
- omit `--dry-run` to persist trades

## 4. Run all advisors for a date

```bash
PYTHONPATH=python/src:$PYTHONPATH python -m advisors.runner --date=YYYY-MM-DD
```

## 5. Run recommendation cron (per-user hiring + notifications)

```bash
PYTHONPATH=".:python:python/src" python3.10 python/scripts/run_advisor_recommendations.py --date=YYYY-MM-DD
```

This script:
- loads active advisors
- generates signals per advisor
- filters to users in `user_advisors.is_active=1`
- writes `advisor_recommendations`
- dispatches notifications via user preferences in `user_settings`

## 6. Configure notifications

Per-user notification preferences are stored in `user_settings`:

| Setting key | Value example | Required | Purpose |
|---|---|---|---|
| `advisor_notify_email` | `1` | Allowed only if SMTP configured | Send recommendation emails |
| `advisor_notify_discord_dm` | `1` | — | Send Discord DM to user |
| `advisor_discord_user_id` | `123456789012345678` | when DM enabled | Recipient Discord user ID |
| `advisor_notify_discord_channel` | `1` | — | Send to Discord channel |
| `advisor_discord_channel_id` | `123456789012345678` | when channel enabled | Target channel ID |
| `advisor_notify_whatsapp` | `1` | Requires gateway wiring | Send WhatsApp message |
| `advisor_whatsapp_number` | `+15551234567` | when WhatsApp enabled | Destination number |

UI: `?action=advisor_preferences`

## 7. View recommendations

UI: `?action=my_recommendations`

API:
```bash
curl -H "X-User-Id: 1" http://127.0.0.1:5000/api/advisor/recommendations
curl http://127.0.0.1:5000/api/advisor/preferences?user_id=1
```

## 8. Transaction notes

When `python/src/advisors/runner.py` persists a trade, it writes:
- `user_id` from the advisor account
- `advisor_id`
- `notes` formatted with action, price, max, stop, confidence, rank, reason, schedule

This creates an auditable log of every advisor-initiated action.

## 9. Troubleshooting
- **No recommendations received**: Confirm `run_advisor_recommendations.py` completed, the advisor is active in `advisor_accounts`, and the user has an active row in `user_advisors`.
- **Email fails**: verify `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS` env vars.
- **Discord DM fails**: verify `DISCORD_BOT_TOKEN` and the user ID is numeric and the bot can user.createmessage.
- **WhatsApp not implemented**: placeholder `_send_whatsapp()` logs only; gateway wiring required.
