# references/sqlite-only-intraday-verification.md
--- Session: 2026-09-23 (cron, 13:46 ET / 17:46 UTC) ---

Single-run verification of `detection_triggers.py --sqlite` (intraday, SQLite-only).
Durable rules live in SKILL.md Pitfalls; this file captures the session-level verification recipe.

## Canonical command (verified this session)
```
cd /root/.hermes/workspace/investment-agent && /usr/bin/python3.10 detection_triggers.py --sqlite
```
No `PYTHONPATH` export needed (security scan blocks `export PYTHONPATH`); the file has internal `sys.path.insert` above its `from src.db...` imports.

## DB to verify (never repo-root decoys)
`from config.paths import ANALYTICS_DB` resolves to `~/.hermes/cache/analysis_results.db`. Workspace `detection_alerts.db`, `price_intraday.db`, `intraday_alerts.db`, `alerts.db`, `alerts_ephemeral.db`, `investment.db` are all decoys (0 bytes / empty / no tables).

## Verification query
```sql
SELECT alert_type, severity, COUNT(*) FROM alert_queue GROUP BY alert_type, severity;
```
Compare against stdout counts. Stdout = ATTEMPT count; `volume_spike` / `gap_up` have observed real-id-but-absent-from-store anomalies. `oscillator_extremes` is the known-good persistence control.

## This session's result (exit 0, no errors)
- Mode: SQLite-only (`--sqlite`). No MariaDB alert writes (read-only `watchlist_symbols` SELECT hit MariaDB as expected).
- `volume_spike`: 1 (WJX.TO 2.17x high) — persisted this run.
- `oscillator_extremes`: 2 (RUS.TO RSI 93.4 high / 5d; WJX.TO RSI 84.3 medium / 2d)
- `natr_spike`: 0 (genuine); `gap_up`: 0 (genuine)
- Total: 3 rows in `ANALYTICS_DB`.

## Operational reminders
- Do NOT expect MariaDB writes during intraday (`--sqlite`).
- Verify against `ANALYTICS_DB`, never workspace `.db` files.
- Reconcile stdout vs SQLite store; reported-but-absent = suspected persistence bug (not benign dedup, since dedup yields `None` id).
- If `sqlite3.OperationalError: database is locked` hits, retry ONCE before diagnosing (WAL transient).
