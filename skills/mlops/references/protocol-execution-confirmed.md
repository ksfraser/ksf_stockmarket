# Verified execution — stock alert protocol (2026-09-29)

Protocol executed successfully with zero errors; 2 pending alerts delivered and committed.

Steps verified:
1. `python3 /root/.hermes/scripts/sqlite_alert_consumer.py --format` → 2 `@@ALERT@@` blocks.
2. `hermes send --to discord:#stock-sell-alerts --file /tmp/alert_1.md` (RUS.TO) → `sent` (exit 0).
3. `hermes send --to discord:#stock-sell-alerts --file /tmp/alert_2.md` (WJX.TO) → `sent` (exit 0).
4. `python3 /root/.hermes/scripts/sqlite_alert_consumer.py --commit osc-RUS.TO-20260929091550 osc-WJX.TO-20260929091550` → committed 2, purged stale rows.

No `[NO ALERTS]` silence; no delivery failures; no stale-row accumulation after `--commit`.
Confirms `hermes send` CLI (not `send_message` tool) is the working delivery path in this cron deployment.
