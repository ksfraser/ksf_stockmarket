---
id: async-alert-monitoring
name: Async Alert Monitoring
description: Monitor alerts from stock market app and coordinate LLM analysis
version: 1.0.0
author: Kevin Fraser
tags: [alert, llm, async, discord, monitoring]
---

# Async Alert Monitoring

Monitor alert_queue table and Discord channels for stock market alerts, then trigger LLM analysis and update app status.

## Architecture

```
Stock Market App (Detection Script)
         |
         v
   alert_queue table  <--->  Hermes Monitors  <--->  LLM Analysis  <--->  DB Update
         ^                      ^
         |                      |
   Discord webhook        Response messages
```

## Alert Types

- `volume_spike` - Volume 3x+ normal average
- `gap_up` - Opening >2% above previous close  
- `regime_change` - Bull/Bear/Sideways transition
- `price_anomaly` - Price moves outside standard deviation bands
- `divergence` - TA indicator divergence detected

## Monitoring Workflow

1. **Detection scripts** write to `alert_queue` table or post to Discord
2. **Hermes observes** alert via database poller or Discord monitoring
3. **LLM analysis** runs asynchronously (non-blocking)
4. **Results written** back to `alert_responses` table
5. **Status updated** in `alert_queue.status = 'completed'`
6. **Notifications sent** to discord/email via Hermes messaging

## One-Way Communication Pattern

The app does NOT wait for LLM response. It:
- Writes alert → exits immediately
- LLM/Hermes processes independently
- Updates database
- Sends notifications separately

This prevents app delays and allows continuous monitoring.

## SQL Schema

See `/sql/alert_system.sql` for table definitions.

## Implementation

### Detection Script (One-Way)
```python
# python/src/alerts/detect_volume_spikes.py
from async_alert_engine import check_volume_anomaly, send_to_hermes

def scan_volume():
    # ... fetch data ...
    alert = check_volume_anomaly(conn, symbol, curr_vol, avg_vol)
    if alert:
        send_to_hermes(alert)  # Non-blocking
        # Script exits immediately, no wait
```

### Alert Trigger Examples
```
# Send to Discord webhook (Hermes monitors)
!alert {"type": "volume_spike", "symbol": "AAPL", "severity": "high", 
        "payload": {"volume": 5000000, "avg": 1000000}}

# Or write directly to queue table
```

### Hermes Response Action
When Hermes sees an alert:
1. Acknowledge with "🔍 Analyzing AAPL volume spike..."
2. Call LLM for analysis
3. Write results to `alert_responses`
4. Update `alert_queue.status = 'completed'`
5. Send notification: "AAPL: Unusual volume (5x avg). Bullish bias indicated by LLM."