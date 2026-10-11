---
name: mlops
description: "ML model operations: discovery, local inference, evaluation, serving, segmentation, stock alert monitoring, and financial data maintenance."
tags: [mlops, huggingface, llama.cpp, vllm, sam, stock-alerts, financial-data, backfill, cache, evaluation]
---

# MLOps

Class-level umbrella for machine learning operations and related monitoring/data maintenance.

## 1) ML Model Ops — `ml-model-ops`

Discovery (HuggingFace Hub), local inference (llama.cpp), evaluation (lm-eval-harness), serving (vLLM), and segmentation (Meta SAM).

## 2) Stock Alert Monitoring — `stock-alert-monitoring`

Detection, queueing, LLM analysis, Discord delivery, template fallback, cleanup, and monitoring. Covers the full alert lifecycle.

**Intraday detection trigger (ephemeral SQLite):**
```bash
cd /root/.hermes/workspace/investment-agent && python3.10 detection_triggers.py --sqlite
```
- `--sqlite` writes to `DETECTION_ALERT_DB` from `config/paths.py`, which resolves to `/home/ksf_stockmarket/ksf_stockmarket/data/analysis_results.db`.
- The DB file in the project directory (`alert_queue.sqlite`, `alerts_ephemeral.db`) is NOT the active store; ignore it.
- Output lines like `N alerts written to alert_queue` reflect only the current run. Pre-existing stale alerts may already be in the DB.

**EOD sync to canonical MariaDB:**
```bash
python3 /root/.hermes/workspace/investment-agent/scripts/sync-sqlite-alerts-to-mariadb.py
```
Syncs `alert_queue` from the ephemeral SQLite to the remote MariaDB, then clears the SQLite queue.

**Alert count reporting for cron jobs:**
- Capture the script's per-trigger counts from stdout.
- Additionally query the SQLite DB for today's rows:
  `SELECT alert_type, COUNT(*) FROM alert_queue WHERE date(created_at)=date('now') GROUP BY alert_type;`
  This distinguishes new alerts from stale carryover from prior sessions.
- If total count is 0 and there are no errors, report clearly; do not fabricate activity.

**Consumer / Discord delivery (the missing link that caused a 15-day silence):**
Detection writes to the SQLite store, but **nothing was draining it to Discord**. `monitor_daemon.py` (the legacy "entrypoint") reads **MariaDB** `alert_queue` and does NOT send to Discord — it only writes `alert_response` rows. So the SQLite store must be drained by a separate consumer.

Working consumer: `/root/.hermes/scripts/sqlite_alert_consumer.py`
- `--format` → prints fresh pending alerts as `@@ALERT@@ id=<ID>\n<msg>\n@@END@@` blocks (no state change).
- `--commit <ID...>` → marks ids completed + purges stale rows.
- Freshness is keyed off the **timestamp embedded in the alert id** (e.g. `vol-RUS-20260809...`); the `created_at` column is often NULL, so never filter on it.

Scheduled via Hermes cron job (market hours, `*/5 9-16 * * 1-5`): the agent runs `--format`, sends each block to Discord `#stock-sell-alerts` via the **`hermes send` CLI** — the `send_message` tool is NOT present in cron agent toolsets, so `hermes send --to discord:#stock-sell-alerts --file <msg>` is the working equivalent (it reuses the Discord bot token, no running gateway needed) — then runs `--commit <ids>`. A packaged dispatcher lives at `scripts/dispatch_stock_alerts_hermes.py`.

**Discord delivery must go through the agent or a terminal-based webhook path.**
`hermes_tools` is **NOT importable inside a bare subprocess** (including a cron job's terminal), so a script cannot `from hermes_tools import send_message`. More importantly, the `send_message` **tool is absent from cron agent toolsets** in this deployment — use the **`hermes send` CLI** instead (`hermes send --to discord:#<channel> --file <msg>`; it reuses the Discord bot token and needs no running gateway).

The reliable pattern is: script formats (`--format`) + the **agent** delivers each block via `hermes send`, then script commits (`--commit <ids>`). Do NOT write `send_message` calls inside the consumer script.

**Webhook fallback:** if `hermes send` is unavailable, the `DISCORD_ALERT_WEBHOOK` / `DISCORD_SELL_WEBHOOK` webhook URL can be POSTed directly from the terminal tool. The original 403 / Cloudflare error 1010 is **User-Agent specific** (Discord rejects `Python-urllib/X.Y`); terminal `curl` does not use that UA and returns `204` on success. Use a one-liner like:
`curl -s -o /dev/null -w "%{http_code}" -X POST "$DISCORD_ALERT_WEBHOOK" -H "Content-Type: application/json" -d '{"content":"<msg>"}'` (This is why the old "cron delivers automatically" assumption was wrong and alerts went silent.)

**Remote DB config (do NOT start local MariaDB):**
```yaml
DB_HOST: ksfraser.ca
DB_USER: ksfraser_stockmarket
DB_PASSWORD: Zaqwsx9sm1@
DB_NAME: ksfraser_stock_market
```

**Routing rules:**
- `natr_spike` → LLM analysis (volatility interpretation)
- `volume_spike`, `oscillator_extreme`, `oscillator_extremes`, `gap_up`, `gap_down` → template-based response via `simple_response()` (NO LLM call)

**Pitfalls:**
- When DB_HOST is remote, never attempt to install/start local MariaDB — the queue lives on `ksfraser.ca`.
- **Deliver via the `hermes send` CLI (`hermes send --to discord:#stock-sell-alerts --file <msg>`), NOT `hermes_tools` inside the script** (not importable in a subprocess). The `DISCORD_*_WEBHOOK` POST path is a valid fallback **from `curl`/terminal** (returns `204`), but Python's default `urllib.request` UA gets `HTTP 403 / error code: 1010` from Cloudflare — so never use bare `urllib` to POST. The format→send→commit protocol is mandatory; when `hermes send` is unavailable, `curl -X POST -H "Content-Type: application/json" -d '{"content":"<msg>"}' "$DISCORD_ALERT_WEBHOOK"` is the working direct path.
- If the SQLite store has no fresh alerts, the agent replies `[SILENT]`.
- The `--sqlite` store path is defined in `config/paths.py` (`DETECTION_ALERT_DB` → `/home/ksf_stockmarket/ksf_stockmarket/data/analysis_results.db`); always resolve it. The project-dir DB files are NOT the active store.
- Stale rows (e.g. `created_at=NULL` from prior sessions) accumulate and block/confuse the store — purge them (the consumer's `--commit` does this). The 4 stale July-10 rows from a prior run were purged this way.
- `monitor_daemon.py` reads MariaDB, NOT the SQLite store, and does not deliver Discord — do not treat it as the delivery path.

**See:**
- `references/stock-alert-monitoring/discord-delivery.md`
- `references/protocol-execution-confirmed.md` — verified 2026-09-29: 2 alerts delivered + committed via `hermes send` CLI (no `send_message` tool in cron toolset).
- `references/stock-alert-monitoring/monitor_daemon.md`
- `references/stock-alert-monitoring/sqlite-intraday-workflow.md`
- `references/stock-alert-monitoring/discord-delivery.md`
- `scripts/dispatch_stock_alerts_hermes.py` — packaged dispatcher (parse `--format`, `hermes send` each block, print delivered IDs for `--commit`); use when the `send_message` tool is unavailable.

## 3) Financial Data Maintenance — `Financial-Data-Maintenance`

Maintain financial time-series and fundamental data: repair, backfill, deduplication, caching. Covers fundamentals backfill, indicator cache refresh, sparse-data recovery, and related maintenance procedures.

## Rules

1. Always verify model hash after download before switching to local inference.
2. Cache financial indicator data to avoid redundant computation.
3. Clean up stale alerts after delivery to prevent duplicate notifications.
