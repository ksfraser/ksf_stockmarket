---
name: session-2026-09-29-current.md
description: Intraday SQLite-only verification session for detection_triggers.py --sqlite (2026-09-29, ~10:30 ET / 14:30 UTC, weekday, inside market hours)
---

# Intraday SQLite-only verification — 2026-09-29 (current run)

## Command executed
```
cd /root/.hermes/workspace/investment-agent && /usr/bin/python3.10 detection_triggers.py --sqlite
```
Exit 0. No errors. No MariaDB writes expected/observed; only read-only `watchlist_symbols` SELECT hits MariaDB.

## Alert results (stdout + verified SQLite `alert_queue`)

| Type | Stdout count | Store count (immediate) | Status | Symbol / id details |
|---|---|---|---|---|
| volume_spike | 0 | 0 | Genuine | — |
| natr_spike | 0 | 0 | Genuine | — |
| oscillator_extremes | 2 | 2 | Confirmed | `osc-RUS.TO-20260929103049` (RSI 99.7, overbought, 9 days, price 86.37); `osc-WJX.TO-20260929103049` (RSI 89.5, overbought, 6 days, price 36.25) |
| gap_up | 0 | 0 | Genuine | — |

Total: 2 alerts written and verified. `oscillator_extremes` remains the reliable persistence control.

## Stdout vs store reconciliation: FULL MATCH for all 4 types.
No divergence observed this run. `volume_spike`/`gap_up` did NOT trigger, so there was no opportunity to observe the non-deterministic persistence anomaly — but when they don't trigger, store = 0 is the correct verification, not a false-negative.

## Key observations
- SQLite ephemeral mode (`--sqlite`) writes only to `ANALYTICS_DB` (`/root/.hermes/cache/analysis_results.db`). Workspace `.db` files (`price_intraday.db`, `detection_alerts.db`, etc.) remain 0-byte decoys.
- The `sqlite3.OperationalError: database is locked` retry-once rule applies; no lock error observed on this run.
- `alert_queue.created_at` is UTC; the `id` embeds ET. Filter/store reconciliation should not use ET time filters.
- Immediate reconciliation query (before any sync/purge cron) is the only trustworthy verification.
