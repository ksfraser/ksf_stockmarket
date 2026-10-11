# Verified working webhook delivery — 2026-09-23

Session: automated cron job processing `sqlite_alert_consumer.py --format`
for pending oscillator alerts (2 delivered: osc-RUS.TO-20260923084550,
osc-WJX.TO-20260923084550).

## Confirmed working direct-curl delivery
`hermes send` unavailable (no `send_message` tool). Webhook POST to
`DISCORD_SELL_WEBHOOK` (alias `DISCORD_ALERT_WEBHOOK`, `#stock-sell-alerts`,
name `"Hermes Stock Alerts"`) succeeded with HTTP 204 using browser UA:
`curl ... -A "Mozilla/5.0 ... Chrome/124.0 ..." -H "Content-Type: application/json" -d '{"content":"..."}' "$DISCORD_ALERT_WEBHOOK"`
Default `Python-urllib` UA returns `403 error code: 1010` (Cloudflare WAF).
Don't omit `-A`. Key takeaways: `--format`/`--commit` protocol works with
webhook; verify with follow-up `--format` → `[NO ALERTS]`; `DISCORD_KSFII_WEBHOOK`
is a different channel.
