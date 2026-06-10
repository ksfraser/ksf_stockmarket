---
id: monitor-alert-queue
name: Monitor Alert Queue
description: Poll MariaDB alert_queue table for pending alerts and trigger LLM analysis
version: 1.0.0
author: Kevin Fraser
tags: [monitoring, alert, maria-db, llm, discord]
---

# Monitor Alert Queue

Poll MariaDB every 2 minutes for pending alerts. When found, trigger LLM analysis and respond via Discord.

## Workflow

1. Every 2 minutes, SELECT pending alerts where `request_llm_analysis = 1`
2. For each alert, call LLM with appropriate prompt
3. Write LLM response to `alert_responses` table
4. Update `alert_queue.status = 'completed'`
5. Send formatted response to Discord #stock-sell-alerts channel

## Database Schema

```sql
-- alert_queue table
CREATE TABLE alert_queue (
    id VARCHAR(64) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(50),
    symbol VARCHAR(20),
    severity ENUM('low','medium','high','critical'),
    payload JSON,
    status ENUM('pending','processing','completed','failed') DEFAULT 'pending',
    request_llm_analysis TINYINT DEFAULT 1
);

-- alert_responses table  
CREATE TABLE alert_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id VARCHAR(64),
    response_text TEXT,
    response_type ENUM('discord','email','direct'),
    responder VARCHAR(100),
    action_taken VARCHAR(255),
    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Alert Types

| Type | Trigger | LLM Prompt Focus |
|------|---------|------------------|
| volume_spike | Volume 3x+ average | Mean reversion, catalyst assessment |
| natr_spike | NATR 2x+ avg | Volatility regime (predictive, r=0.16@20d) |
| oscillator_extreme | RSI >70 or <30 | Regime filter, not direction |
| gap_up | Open >2% prev close | News context, trade setup |

## Implementation

This skill is designed to run as a cron job or background process. See `cron/alert_cron` for scheduling.

## SQL Setup

Run `sql/alert_system.sql` to create the tables.

## Configuration

Add to vault:
```yaml
# Discord webhook for notifications
discord_alert_webhook: "https://discord.com/api/webhooks/..."
```

## Testing

```bash
# Run once
python3 python/src/alerts/hermes_alert_monitor.py --once

# Check alerts
python3 python/src/alerts/detection_triggers.py

# View pending alerts
mysql -e "SELECT * FROM alert_queue WHERE status='pending'"
```