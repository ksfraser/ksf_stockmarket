---
name: Discord webhook fallback when send_message bot token unavailable
---

# Discord Webhook Fallback for Alert Delivery

When running as a cron job or in environments where `DISCORD_BOT_TOKEN` is not set, the Hermes `send_message` tool (target: `discord:#channel-name`) fails with:

```json
{"error": "Discord standalone send: DISCORD_BOT_TOKEN is not set"}
```

The `DISCORD_ALERT_WEBHOOK` environment variable contains the webhook URL. Delivering via `curl` succeeds (HTTP 204) and reaches the same `#stock-sell-alerts` channel.

## Pattern

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${DISCORD_ALERT_WEBHOOK}" \
  -H "Content-Type: application/json" \
  -d '{"content":"message text"}'
```

## When to use

- Cron job contexts where gateway bot token isn't available
- Any time `send_message` returns `DISCORD_BOT_TOKEN is not set`
- Manual alert dispatch outside the gateway process

## Verification

- Exit code 0 + no output = HTTP 204 (success)
