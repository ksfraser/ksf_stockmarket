# 2026-09-13 indicators migration: log trim + monitor restart + cron pause sweep

Session context: the indicators_json → indicators columnar migration had stalled (898,426
rows frozen for over an hour), `/tmp` was 1.5GB (mostly `migrate_indicators.log` at 2.8GB),
and a cron-pause sweep had accidentally paused jobs that should have stayed active.

## What happened

1. **Migration stalled:** background process was dead (no `ps` match), row count static at
   898,426 for >1 hour. Root cause not definitively diagnosed — likely a deadlock hang.
2. **`/tmp` bloat:** `migrate_indicators.log` had grown to 2.8GB (2,834,493,544 bytes)
   because the migration script logs every indicator field for every row. `/tmp` mounted at
   1.5GB total, so it had consumed essentially all of it.
3. **Stale process:** a pre-existing background process (`proc_c4a6b6170cd9`) finished
   during the session with exit 124 (timeout kill) — that was the old unlimited 1000-symbol
   version, superseded by the time-budget fix. Benign, no action needed.

## What was done

### Migration restart

The migration was restarted via background terminal:

```bash
cd /home/ksf_stockmarket/ksf_stockmarket
DB_PASS="Zaqwsx9sm1@" DB_USER="ksfraser_stockmarket" DB_NAME="ksfraser_stock_market"
nohup python3 -u migrate_indicators_json_to_columnar.py >> /tmp/migrate_indicators.log 2>&1 &
```

After restart, the row count dropped from 898,426 to 329,528 (569k rows processed), confirming
the stall was a dead process, not a script bug.

### Log trim

Trimmed `migrate_indicators.log` to last 5000 lines via `tail`:

```bash
tail -5000 /tmp/migrate_indicators.log > /tmp/migrate_indicators.log.trimmed
mv /tmp/migrate_indicators.log.trimmed /tmp/migrate_indicators.log
```

Result: log went from 2.8GB to 228KB. `/tmp` total went from 1.5GB to 56MB.
Other files in `/tmp` left untouched (opencode 42M×2, populate_analyst_ratings.log 24K,
tv_screener_cron.log 8K, alert files, html stubs — all their own).

**Important:** the migration script *itself* still logs every row. This is a script issue,
not a log-trim issue. If the log grows again, the script needs a `--quiet` / errors-only mode,
not another tail trim.

### Cron pause sweep

Paused all non-migration cron jobs so only the migration watchdog fires. Final state:

- **Active (1 job):** `59fc71e44a68` — indicators-migration-monitor (every 15 min)
- **Paused (all others):** every other cron job in the system

The three stragglers from the pause sweep (Reddit Lead Response FHS, Nightly symbol-info
reconciliation, KSFII annual compliance review) plus a fourth found in the full list
(Nightly Analyst Ratings Population) were all explicitly paused.

### Self-removing monitor

A self-removing cron monitor (`59fc71e44a68`, every 15 min) was created to watch the
migration. It checks `pgrep -f migrate_indicators_json_to_columnar.py`, queries
`indicators_json` count, restarts if dead+rows remain, and removes itself when count hits
zero. Documented in the cronjobs skill under "Self-removing completion monitors."

## Outcome

- Migration alive and processing (329,528 remaining, 1,053,536 rows in indicators)
- `/tmp` recovered to 56MB
- Only the watchdog cron active; all others paused
- Self-removing monitor in place so the migration stays alive and cleans up after itself

## Lessons

- **Don't trust a static row count for more than a few minutes.** If the count hasn't moved
  for 15+ minutes, check the process. A dead process is the common case (stalled counts
  were all dead-process cases this session).
- **A verbose log kills /tmp fast.** A migration that logs every row at 1000+ chars/row
  will fill a 1.5GB /tmp in under an hour at 1000 rows/second. Error-only logging or
  sampled logging is required for long-running batch jobs.
- **The cron pause sweep was too broad.** It paused jobs that should have stayed active.
  When pausing "all non-migration" jobs, verify the full list afterward for stragglers —
  especially jobs that were active before the sweep (the Daily Investment Monitor was active
  at the start and got paused as part of the sweep).

## Related

- [Exchange routing module — reference implementation](exchange-routing-module.md) — the
  DAO/repository layer built in the same session.
- devops/cronjobs skill — self-removing monitors, import-path pitfall, workflow preference.
