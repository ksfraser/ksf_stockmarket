# Local verification when MariaDB is unreachable
Use these steps when stock alert runs succeed on stdout but queue state is uncertain.

1. Detect presence of fallback un-Delivered messages if any:
   - /tmp/alert_discord_msg.txt

2. Inspect local SQLite analysis cache:
   - /root/.hermes/cache/analysis_results.db
   - Tables of interest: alert_queue, alert_responses, volume_spikes, price_alerts

3. Re-run detection + monitor only after restoring DB connectivity:
   - /usr/bin/python3.10 /root/detection_triggers.py --all
   - /usr/bin/python3.10 /root/hermes_stock_alert_monitor.py --once

Expected bad state:
- No new rows in alert_queue/responses on MariaDB
- Discord fallback file exists with content
- Monitor logs "Completed alert" while DB writes actually failed

Recovery order:
1. Restore MariaDB routing/service.
2. Reset stuck `processing` back to `pending`: UPDATE alert_queue SET status='pending' WHERE status='processing';
3. Ensure request_llm_analysis=1 for all pending rows.
4. Rerun detection + monitor.
5. If Discord webhook now reachable, deliver queued messages.
