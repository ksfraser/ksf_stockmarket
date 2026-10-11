---
name: sqlite_alert_consumer.py protocol for pending stock alerts
---

# SQLite Alert Consumer Protocol

Used by scheduled cron jobs to process pending oscillator/extreme alerts from the `sqlite_alert_consumer.py` script.

## Read pending formatted alerts

```bash
python3 /root/.hermes/scripts/sqlite_alert_consumer.py --format
```

Output format:
```
@@ALERT@@ id=<ID>
<formatted message text>
@@END@@
```

If no alerts: prints `[NO ALERTS]`.

## Send messages

Extract text between `@@ALERT@@` and `@@END@@`. Deliver each block to the target Discord channel (`#stock-sell-alerts`).

If `send_message` bot token unavailable, fall back to webhook (`DISCORD_ALERT_WEBHOOK`) via `curl`.

## Commit delivered IDs

```bash
python3 /root/.hermes/scripts/sqlite_alert_consumer.py --commit <ID1> <ID2> ...
```

This marks the alerts as completed/purged in the SQLite store.

## Key rules

- Do NOT re-summarize alert contents in final delivery — the send_message (or webhook) delivers them directly.
- Report only count delivered (or `[SILENT]` if none).
