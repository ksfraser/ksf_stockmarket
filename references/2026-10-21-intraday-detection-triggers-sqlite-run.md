---
name: 2026-10-21-intraday-detection-triggers-sqlite-run.md
description: Intraday alert detection (app-root shim, --sqlite, ephemeral SQLite only, no MariaDB writes). Verified complete.
date: 2026-10-21
tag: intraday-alert-detection
---

# 2026-10-21 Intraday Alert Detection — SQLite (app-root shim)

## Source / confirmation
- Script: `/root/Documents/stockmarket/php/stockmarket-app/detection_triggers.py` — **app-root shim** (NOT canonical investment-agent).
- Confirmed shim: `grep -c KNOWN_TSX` = 3; `_market_open` = 0; `get_monitored_symbols` = 0.
- No market-hours gate (shim has none).

## Command executed
`cd /root/Documents/stockmarket/php/stockmarket-app && /usr/bin/python3.10 -u detection_triggers.py --sqlite`
- `--sqlite` routes writes to SQLite; symbol list still from hardcoded KNOWN_TSX + KNOWN_US (~70 symbols).
- Background launch (long network-bound scan); wrapper PID 243079, python child PID 243123.

## Market-hours / timing context
- Launch (naive local MDT): 2026-10-21 08:15:43.
- ET clock: 2026-10-21 10:15:43 EDT (Wednesday, in market hours 09:30–16:00 ET).
- Gate (shim): none (not applicable — no `_market_open()`).

## Duration / exit
- Exit code: 0.
- Uptime (wrapper session `proc_48c38a2a1082`): 840 s (~14 min). Within expected 15–20 min range for 70 symbols × 4 triggers.
- Child state at exit: completed cleanly; no stalls (verified non-trivial %CPU ~13% throughout, no flat-run-window stall).

## SQLite target (verified — durable file, WAL checkpointed)
- Path: `/root/Documents/stockmarket/php/stockmarket-app/data/analysis_results.db`
- Pre-run total `alert_queue`: 6 rows (all `gap_up`, pre-existing from earlier sessions: 07:31Z and 08:14Z).
- Post-run total `alert_queue`: 8 rows.
- WAL checkpoint: `PRAGMA wal_checkpoint(TRUNCATE)` executed at finalize (verified via fresh connection).
- No MariaDB writes (expected for `--sqlite`; `ANALYTICS_DB` = repo-relative SQLite, not MariaDB `alert_queue`).
- `price_intraday`: 13,409 rows (unchanged; not part of this alert run).

## Alert counts — exact per type (run-window: `created_at IS NOT NULL AND created_at >= 2026-10-21T08:15:43`, naive MDT)
- `volume_spike`: **0**
- `natr_spike`: **0**
- `oscillator_extremes`: **0**
- `gap_up`: **2** (both new this run)
- Total new run-window rows: 2.
- Status: both `pending`.

## Alert details (from payload + DB)
| id | alert_type | symbol | severity | triggered_at (MDT) | payload snippet |
|---|---|---|---|---|---|
| NVDA_gap_up_20261021082749 | gap_up | NVDA | medium | 2026-10-21T08:27:49 | gap_pct=2.07, open=220.96, prev_close=216.47, filled=false |
| TSLA_gap_up_20261021082824 | gap_up | TSLA | medium | 2026-10-21T08:28:24 | gap_pct=2.09, open=381.51, prev_close=373.71, filled=false |

## Errors / non-fatal resolution skips (separate category — not failure)
- 16 × HTTP 404 (`quoteSummary` not found) — expected, non-fatal, do not contribute to alerts.
- Breakdown (verified by `grep -o` on log):
  - `NPI`: 4
  - `XFN`: 4
  - `XIT`: 4
  - `MICC.TO`: 4
- No timeouts, no 429 rate-limit errors in log, no tracebacks, no `Exception` / `timeout` messages.
- Log endpoint: `/tmp/detection_triggers_sqlite_run.log` (final line: `Alerts queued: [NVDA] ... [TSLA] ...`).
- Note: per-symbol 404 bursts match the 4-trigger inner-loop (volume, natr, oscillator, gap) per delisted symbol.

## Pre-existing / attribution (do NOT confuse with new)
- Pre-run `gap_up`: 6 rows (AMZN 07:31Z–13:02Z range; timestamps 07:37Z–13:02Z from earlier 2026-10-19 / 2026-10-21 runs).
- Only new after `run_start`: 2 `gap_up` (NVDA, TSLA). Confirmed by `created_at >= 2026-10-21T08:15:43` filter; `TRIGGERED_AT` inside payload (08:27, 08:28) corroborates.

## Verification steps performed
- Shim confirmation (`KNOWN_TSX` / `KNOWN_US`, no `_market_open`).
- Pre-launch stale-pipeline guard: `ps | grep detection_triggers` → none running; launched clean.
- Child PID tracked: 243123 (python); wrapper 243079. Polling loop verified alive/non-stalled (CPU 13.1–13.3%, `Rl/Sl`, not `Sl` at 0%).
- Log growth verified: 0 → 4 → 8 → 12 → 13 → 16 404 lines; final buffer flush at exit; `Alerts queued:` line present.
- SQLite attribution: `PRAGMA wal_checkpoint(TRUNCATE)` + `SELECT ... WHERE created_at IS NOT NULL AND created_at >= '2026-10-21T08:15:43'` — 2 new `gap_up` only. No `volume_spike` / `natr_spike` / `oscillator_extremes` new.
- No concurrent `detection_triggers.py` after exit (orphan check clean).
- Store path explicitly stated above; no `~/.hermes/cache/analysis_results.db` used (shim uses repo-relative `<repo>/data/analysis_results.db`).
