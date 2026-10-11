# Verified working webhook + hermes send delivery — 2026-09-24

Session: automated cron job processing `sqlite_alert_consumer.py --format`
for pending oscillator alerts (3 delivered: osc-RUS.TO-20260924111521,
osc-RY.TO-20260924111521, osc-WJX.TO-20260924111521).

## Protocol failure — `send_message` does not exist in this Hermes installation

The cron job protocol instructed `send_message --target discord:#stock-sell-alerts`.
That tool is NOT in the available-tools list. Calling it returned:

```
Tool 'send_message' does not exist. Available tools: ...
```

This is a phantom — the protocol's generic placeholder for "send to Discord,"
but the actual Hermes installation here has no such tool. Do not waste a turn
trying to call it. Instead, read `discord-webhook-delivery.md` and pick a working
path immediately.

## What worked — Path A: `hermes send` (preferred)

`hermes send` WAS available (`/root/.local/bin/hermes`) and worked in this
non-interactive cron context with zero LLM calls:

```bash
# Pre-flight: verify the broker is up
echo test | hermes send --to discord:#stock-sell-alerts

# Deliver each alert block (file = exact formatted text from the @@ALERT@@ block)
hermes send --to discord:#stock-sell-alerts --file /tmp/alert_<id>.txt
```

All three blocks returned `sent` (exit 0). Then `--commit` purged them and a
follow-up `--format` returned `[NO ALERTS]` — full round-trip verified.

## Key takeaways

- The stock-alert cron protocol's `send_message` instruction is a phantom tool.
  The working replacement is `hermes send --to discord:#channel --file <msg>`
  (Path A) or one of the `_cron_deliver_*_now.py` webhook scripts (Path D).
- `hermes send` is available in cron (no gateway/LLM needed) and should be the
  FIRST thing to try for Discord delivery in this environment — do not assume
  it's unavailable just because the session is non-interactive.
- Always verify after `--commit` with a follow-up `--format` expecting `[NO ALERTS]`.
- The 403-on-default-UA / Cloudflare 1010 gotcha still applies to any direct
  webhook path (curl or Python urllib), but it is IRRELEVANT when using
  `hermes send` — the gateway handles the HTTP layer.
