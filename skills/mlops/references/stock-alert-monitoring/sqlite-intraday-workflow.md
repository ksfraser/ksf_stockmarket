# SQLite Intraday Workflow

## Purpose
Ephemeral alert queue for weekday market-hour detection triggers. Avoids MariaDB round-trips during the trading day; syncs to canonical DB at EOD.

## Key Files

| File | Role |
|------|------|
| `detection_triggers.py` | Runs 4 checks: volume, NATR, oscillator extremes, gap. Writes to SQLite when `--sqlite` is passed. |
| `scripts/sync-sqlite-alerts-to-mariadb.py` | EOD sync: copies `alert_queue` rows to remote MariaDB, then clears SQLite. |
| `config/paths.py` | Defines `DETECTION_ALERT_DB = /home/ksf_stockmarket/ksf_stockmarket/data/analysis_results.db` |

## SQLite DB Path
Resolved from `config/paths.py` at runtime. Do **not** assume any `.sqlite` or `.db` file in the project directory is the active store. Always confirm with:
```python
from config.paths import DETECTION_ALERT_DB
print(DETECTION_ALERT_DB)
```

## alert_queue Schema (SQLite)
Mirrors the MariaDB `alert_queue` table. Key columns: `id`, `alert_type`, `symbol`, `severity`, `payload`, `status`, `request_llm_analysis`, `created_at`.

## Cron Report Pattern
1. Run `python3.10 detection_triggers.py --sqlite` from `/root/.hermes/workspace/investment-agent`.
2. Parse stdout for per-trigger counts and total.
3. Query the DB for today's rows to separate new alerts from stale carryover:
   ```sql
   SELECT alert_type, COUNT(*) FROM alert_queue WHERE date(created_at) = date('now') GROUP BY alert_type;
   ```
4. Report counts by type. If total is 0 and exit_code is 0, state "0 alerts, clean run."

## Stale Alerts
Pre-existing alerts from prior runs may remain in the DB if EOD sync has not yet executed. They appear with older `created_at` timestamps. Always filter by `date(created_at)` when summarizing.

## End-of-Day Sync
Run after market close:
```bash
python3 scripts/sync-sqlite-alerts-to-mariadb.py
```
After sync, the SQLite `alert_queue` is cleared.
