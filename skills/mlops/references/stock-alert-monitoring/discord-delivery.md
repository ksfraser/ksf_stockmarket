# Stock Alert Discord Delivery (working path)

The end-to-end alert lifecycle that actually delivers to Discord:

```
detection_triggers.py --sqlite  (cron 0273fd37307d, */15 9-16 Mon-Fri)
        │  writes to ephemeral SQLite
        ▼
/home/ksf_stockmarket/ksf_stockmarket/data/analysis_results.db  (table: alert_queue)
        │  NOBODY was draining this  →  15-day silence
        ▼
sqlite_alert_consumer.py  (cron e40f7cae1a3a, */5 9-16 Mon-Fri)
   step 1: --format   → prints fresh pending alerts as blocks
   step 2: AGENT sends each block to #stock-sell-alerts via the `hermes send` CLI (the `send_message` tool is absent from cron agent toolsets — use `hermes send`)
   step 3: --commit <ids>  → marks completed + purges stale
```

## Why the old design was silent
- Detection (`--sqlite`) writes to SQLite `analysis_results.db.alert_queue`, NOT MariaDB.
- `monitor_daemon.py` reads **MariaDB** `alert_queue` and never sends Discord — it only
  records `alert_responses`. So the SQLite store had no consumer.
- `hermes_tools` is NOT importable in a bare subprocess (incl. a cron terminal), so a
  script cannot `from hermes_tools import send_message` and deliver. Delivery MUST be
  done by the agent via its `send_message` tool.

## Consumer script: /root/.hermes/scripts/sqlite_alert_consumer.py
Modes:
- `--format` — print fresh pending alerts (no state change). Block format:
  ```
  @@ALERT@@ id=<ID>
  <formatted message>
  @@END@@
  ```
- `--commit <ID> [<ID>...]` — mark ids completed + purge stale/old rows.
- `--dry-run` — same as `--format` (no changes).

Freshness: keyed off the timestamp embedded in the alert id (regex `\d{14}$`,
`YYYYMMDDHHMMSS`). The `created_at` column is frequently NULL — never filter on it.
Stale = id older than `MAX_AGE_DAYS` (2) or NULL `created_at`.

## Cron job (Hermes) protocol
Schedule `*/5 9-16 * * 1-5`. Prompt:
1. Run `python3 /root/.hermes/scripts/sqlite_alert_consumer.py --format`
2. If `[NO ALERTS]` → output `[SILENT]` and stop.
3. Else for each `@@ALERT@@ … @@END@@` block, send the message to Discord
   channel `#stock-sell-alerts` using the **`hermes send` CLI** — the `send_message`
   tool is NOT present in cron agent toolsets. Command:
   `hermes send --to discord:#stock-sell-alerts --file /tmp/alert_<id>.txt`
   (or pipe: `echo "<msg>" | hermes send --to discord:#stock-sell-alerts`).
   A packaged dispatcher is at `mlops/scripts/dispatch_stock_alerts_hermes.py`.
4. Run `python3 /root/.hermes/scripts/sqlite_alert_consumer.py --commit <id1> <id2> …`
5. Report a one-line count (or `[SILENT]`).

## Validation recipe (local, self-cleaning — no prod/MariaDB touch, no Discord send)
```bash
DB=/home/ksf_stockmarket/ksf_stockmarket/data/analysis_results.db
TS=$(date +%Y%m%d%H%M%S)
python3 - <<PY
import sqlite3, json
from datetime import datetime
c=sqlite3.connect("$DB")
c.execute("INSERT INTO alert_queue (id,created_at,alert_type,symbol,severity,payload,status,request_llm_analysis) VALUES (?,?,?,?,?,?,?,?)",
  (f"vol-RUS-$TS", datetime.now().isoformat(), "volume_spike", "RUS", "high",
   json.dumps({"volume_ratio":3.2,"today_volume":1500000,"avg_volume":470000,"price_change_pct":4.1,"severity":"high"}), "pending", 1))
c.commit(); c.close()
PY
python3 /root/.hermes/scripts/sqlite_alert_consumer.py --format   # agent would send this
python3 /root/.hermes/scripts/sqlite_alert_consumer.py --commit "vol-RUS-$TS"
python3 -c "import sqlite3;c=sqlite3.connect('$DB');print('pending:',c.execute(\"SELECT COUNT(*) FROM alert_queue WHERE status='pending'\").fetchone()[0])"
# expect pending: 0
```

## Delivering from cron — no send_message tool, dead webhooks (2026-08-12)

The protocol above references the agent's `send_message` tool. In this deployment that
tool is **NOT present in the cron agent toolset**, so it cannot be called. Use the
**`hermes send` CLI** instead — it reuses the Discord bot token from `.env` and needs no
running gateway:

```bash
# one alert
hermes send --to discord:#stock-sell-alerts --file /tmp/alert_<id>.txt
# or pipe
echo "<formatted message>" | hermes send --to discord:#stock-sell-alerts
```

`hermes send -l` lists reachable targets; `--to discord:#<channel-name>` resolves the
channel by name. Exit code 0 = delivered (JSON shows `message_id`); 1 = backend error.

**Webhook path is currently broken:** the six `DISCORD_*_WEBHOOK` URLs in
`/root/.hermes/alert_webhooks.env` all return `HTTP 403 / error code: 1010`, so a script
that POSTs directly to them fails. `hermes send` uses the bot token, not those URLs, and
works. If you ever see `403 / 1010` from a webhook POST, fall back to `hermes send`
rather than assuming delivery succeeded.

**Packaged dispatcher:** `mlops/scripts/dispatch_stock_alerts_hermes.py` parses
`--format` output, writes each block to a temp file, calls `hermes send` per block (skips
any already-delivered ID passed via `--skip`), and prints the successfully-delivered IDs
one per line — feed those straight into `--commit`.
```
