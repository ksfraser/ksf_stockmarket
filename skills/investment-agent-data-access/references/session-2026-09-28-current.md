---
name: session-2026-09-28-current.md
description: Intraday SQLite-only verification session for detection_triggers.py --sqlite (current session, 2026-09-28 12:32 ET / 16:32 UTC, weekday, inside market hours)
---

# Intraday SQLite-only verification — current session (2026-09-28 12:32 ET)

## Command executed
```
cd /root/.hermes/workspace/investment-agent && /usr/bin/python3.10 detection_triggers.py --sqlite
```
Exit 0. No errors. No MariaDB writes (sqlite_mode=True); only read-only `watchlist_symbols` SELECT hits MariaDB.

## SQLite store (live ephemeral DB — verified by import, not guess)
```
from config.paths import ANALYTICS_DB
# => /root/.hermes/cache/analysis_results.db
```
Workspace `.db` files (`price_intraday.db`, `detection_alerts.db`, `alerts.db`, `intraday_alerts.db`, `alerts_ephemeral.db`) are all 0-byte decoys — do NOT verify against them.

## Alert count by type (verified from SQLite `alert_queue` query)
```
SELECT alert_type, severity, COUNT(*) FROM alert_queue GROUP BY alert_type, severity;
```

| Type | Count | Severity | Details |
|---|---|---|---|
| `volume_spike` | 0 | — | Genuine (no trigger). |
| `natr_spike` | 0 | — | Genuine (no trigger). |
| `oscillator_extremes` | 2 | `high` | `osc-RUS.TO-20260928123046` (RSI 93.4, overbought, 8 days, price 86.52); `osc-WJX.TO-20260928123046` (RSI 83.7, overbought, 5 days, price 34.53) |
| `gap_up` | 0 | — | Genuine (no trigger). |

**Total confirmed in store:** 2 (`oscillator_extremes`). Both `status=pending`.

## Stdout vs store reconciliation (durable verification recipe)
- `oscillator_extremes`: stdout 2 → store 2 → MATCH (reliable persistence control).
- `volume_spike`: stdout 0 → store 0 → MATCH (genuine, not an anomaly this run).
- `natr_spike`: stdout 0 → store 0 → MATCH.
- `gap_up`: stdout 0 → store 0 → MATCH.

Always reconcile after every `--sqlite` run; stdout is an attempt count and can diverge from the store for `volume_spike`/`gap_up`.

## Key session learnings (embedded for future runs)
1. SQLite DB must be resolved via `ANALYTICS_DB` import — never guess filenames from workspace layout.
2. `created_at` is stored in UTC (`CURRENT_TIMESTAMP`); the alert `id` embeds ET. Filter/store verification uses UTC value or skips time filtering.
3. If `sqlite3.OperationalError: database is locked` appears, retry once (WAL + concurrent cron); only diagnose after a second failure.
4. `oscillator_extremes` = reliable persistence control; `volume_spike`/`gap_up` = suspected non-deterministic persistence bugs.
5. No MariaDB writes expected during intraday (`--sqlite`).
