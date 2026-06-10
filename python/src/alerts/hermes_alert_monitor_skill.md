---
id: hermes-alert-monitor
name: Hermes Alert Monitor
description: Monitor alert_queue and Discord for stock alerts, trigger LLM analysis and respond
version: 1.0.0
author: Kevin Fraser
tags: [alert, monitoring, llm, discord, async]
---

# Hermes Alert Monitor

Monitor MariaDB alert_queue table and Discord channels for stock market alerts. When an alert arrives, trigger LLM analysis and write results back to the database.

## Trigger Conditions

- Poll MariaDB `alert_queue` table every 2 minutes
- Monitor Discord #stock-sell-alerts channel for `!analyze` commands
- Watch for email alerts to `hermes@ksfraser.ca`

## Workflow

```
1. Alert detected → alert_queue table (pending)
2. Hermes polls every 2 min → finds pending alerts
3. Hermes calls LLM for analysis → gets response
4. Hermes writes to alert_responses table
5. Hermes updates alert_queue.status = 'completed'  
6. Hermes sends Discord notification with analysis
```

## Alert Processing

### Volume Spike (3x+ average)
- **Trigger**: `detection_triggers.py` writes to queue
- **LLM Prompt**: "Analyze {symbol} unusual volume (5x avg). What does this indicate?"
- **Response**: Brief analysis + action recommendation

### NATR Spike (2x average)  
- **Trigger**: Volatility spike - NATR is predictive (r=0.16@20d)
- **LLM Prompt**: "NATR volatility spike for {symbol}. Analyze implications for next 20 days."
- **Response**: Regime assessment + timing suggestions

### Gap Up (>2%)
- **Trigger**: Opening gap detected
- **LLM Prompt**: "Gap up {pct}% for {symbol}. Catalyst assessment and trade setup."
- **Response**: News context + entry/exit levels

## Database Operations

```python
# Read pending alerts
SELECT * FROM alert_queue WHERE status = 'pending' AND request_llm_analysis = 1

# Write LLM analysis
INSERT INTO alert_responses (alert_id, response_text, response_type, responder)
VALUES (%s, %s, 'hermes', %s)

# Update alert status
UPDATE alert_queue SET status = 'completed', llm_analysis = %s, completed_at = NOW()
WHERE id = %s
```

## Discord Integration

**Send alerts to Hermes:**
- Monitor #stock-sell-alerts for `!analyze SYMBOL` commands
- Watch for `!alert {"type": "...", "symbol": "..."}` JSON notifications

**Respond with analysis:**
- Post to #stock-sell-alerts with LLM findings
- Include action recommendation (buy/sell/hold)

## Usage

Run as a cron job or background process:

```bash
# Every 2 minutes during market hours
*/2 9-16 * * 1-5 /usr/bin/python3 /home/ksf_stockmarket/ksf_stockmarket/python/src/alerts/hermes_alert_monitor.py

# Or run continuously
python3 hermes_alert_monitor.py --daemon
```

## Configuration

Add to `group_vars/vault.yml`:
```yaml
discord_alert_webhook: "https://discord.com/api/webhooks/..."
hermes_discord_channel_id: "1497324630212345957"
mariadb_host: "ksfraser.ca"
```