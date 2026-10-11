# Intraday detection cron (investment-agent)

## Canonical cron command

```bash
cd /root/.hermes/workspace/investment-agent && /usr/bin/python3.10 detection_triggers.py --sqlite
```

This is a weekday market-hours trigger (`09:30-16:00 ET`) that writes alerts to a throwaway
SQLite `alert_queue` instead of MariaDB.

## Key facts for cron debugging

- **`--sqlite` = SQLite-only writes.** The only DB writes are to `alert_queue` in
  `ANALYTICS_DB` = `~/.hermes/cache/analysis_results.db`. **No MariaDB writes occur intraday.**
- **MariaDB IS still contacted read-only.** The script reads the active monitored-symbol list from
  `watchlist_symbols` via a `pymysql SELECT` — so a clean run still touches MariaDB, just never writes.
- **The live store is the cache DB, NOT any workspace `*.db`.** There are ~9 empty decoy `*.db` files
  in the workspace (`price_intraday.db`, `detection_alerts.db`, `alerts.db`, `alerts_ephemeral.db`,
  `intraday_alerts.db`, `alerts_intraday.db`, `investment.db`, `cron_jobs.db`, `cron_queue.db`).
  They are zero-byte / no-tables decoys. A naive `sqlite3 <workspace-db> "SELECT ..."` returns empty
  and looks like a failed run.
- **`APP_ROOT` is a red herring.** A non-empty decoy at `/var/www/stockmarket-app/data/analysis_results.db`
  looks like the target but holds stale ksf_stockmarket data. Confirm the path by importing
  `from config.paths import ANALYTICS_DB` — never guess from filename or env var.

## Verification recipe (after every run)

1. Read the canonical DB path:
   ```python
   import sys, os, sqlite3
   sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
   from config.paths import ANALYTICS_DB
   print('DB:', ANALYTICS_DB)
   ```
2. Sum by type over the live store:
   ```sql
   SELECT alert_type, COUNT(*) FROM alert_queue GROUP BY alert_type;
   ```
   Column name is `alert_type`, NOT `type` — `GROUP BY type` raises `no such column`.
3. Cross-check against the run's stdout summary. A mismatch between reported-written and store-count
   is the primary suspected-persistence-bug signal — see the anomaly class below.

## The stdout-vs-store anomaly class (suspected persistence bug, not dedup)

`write_alert()` returns `None` for a duplicate open within the 300s dedup window, but each
`run_*_check` increments `alerts_written` unconditionally. That alone produces printed counts that
exceed rows. **Worse: a real (non-None) alert id can be printed yet still not land in the store.**
Observed in two separate runs:
- `volume_spike` (2026-08-13 ~19:00 UTC): printed `alert_id: vol-XIC.TO-...`, counted 1, store had 0.
- `gap_up` (2026-09-09 ~12:30 ET): printed `alert_id: gap-CEF-...`, counted 1, store entirely empty afterwards.

This is NOT the dedup miscount — dedup yields `alert_id: None`. Here the id is a real value,
so the write path returned a value but no row persisted. The anomaly is **non-deterministic** (gap_up
persisted on a later 2026-09-11 run), so any single run's reported-but-absent alert is a suspected
bug requiring investigation, not a benign miscount.

Operational rule: **trust the store, not stdout.** `oscillator_extremes` is the known-good control —
it persists reliably across runs and confirms the write path is up. If any reported alert type has
stdout count > 0 but store count = 0, flag it as a suspected persistence bug rather than assuming
success or dedup.

## Market-hours gate

Outside weekdays `09:30-16:00 ET` the script prints "Outside market hours ... skipping detection."
and exits 0 with 0 alerts. That is correct, not a bug.

## Correct verification queries (use UTC, not ET)

`alert_queue.created_at` is stored in UTC. The alert id embeds an ET time (e.g. `osc-CEF-20260824130132`)
so the run *looks* like 13:01 ET, but the column holds `2026-08-24 19:01:32` UTC. Time-filter by UTC,
or just `GROUP BY alert_type, severity` over the whole ephemeral table (the store is throwaway, so a
whole-table snapshot is a valid run view).

## Deep write-path anomaly writeup

For the full anomaly detail, controlled reproduction, and operational rule, see the canonical reference:
`investment-agent-data-access/references/detection-triggers.md` (same classes of bug, same command,
same store).

## See also

- `devops/cronjobs/SKILL.md` — the parent skill governing Hermes cron-job debugging generally.
- `investment-agent-data-access/references/detection-triggers.md` — deep dive on this cron.
- `investment-agent-data-access/references/sqlite-decoy-dbs.md` — full decoy inventory + verification recipe.
