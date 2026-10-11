# Delivering alert-consumer output to Discord (agent/standalone)

The `sqlite_alert_consumer.py` two-step protocol (see the script docstring) prints
formatted alert blocks via `--format` and marks them done via `--commit <ID...>`.

## Path A — `hermes send` (preferred)

**This is the preferred path when Hermes CLI is available.** The `hermes send`
command reuses the gateway's platform credentials and requires no LLM call.
It works in both interactive and non-interactive cron contexts:

```bash
hermes send --to discord:#stock-sell-alerts --file /tmp/alert_0.txt
```

Inline text also works for short single-line/block messages:

```bash
hermes send --to discord:#stock-sell-alerts "**CM.TO Oscillator Alert** 📈 ..."
```

Exit codes: `0=ok`, `1=delivery/backend error`, `2=usage error`.

## Pre-flight check — Discord broker must be running

Discord delivery here depends on the Hermes gateway/broker being live. `hermes send`
POSTs to the Hermes API, which itself dispatches to Discord. If the broker is down,
`hermes send` will fail with connection or auth errors — the command is correct but
the downstream is not reachable. Before a full batch, test with the smallest possible
delivery:

```bash
echo test | hermes send --to discord:#stock-sell-alerts
```

If that fails, check whether the Hermes Discord broker process is running and restart
it if needed. The same caveat applies to any `hermes send`-based cron path.

## Pre-flight check — Discord broker must be running

Before a full batch, verify the Hermes Discord broker is up. `hermes send` POSTs
to the Hermes gateway/API, which itself dispatches to Discord. If the broker is
down, `hermes send` will fail with connection or auth errors — the command is
correct but the downstream is not reachable.

Test with the smallest possible delivery:

```bash
echo test | hermes send --to discord:#stock-sell-alerts
```

If that fails, check whether the Hermes Discord broker process is running and
restart it if needed. The same caveat applies to any `hermes send`-based cron
path.

## Path B — `send_message` tool (DOES NOT EXIST — do not use)

The `send_message` tool name appears in some cron job protocol instructions as a
generic placeholder for "send to Discord," but there is **no `send_message` tool**
in this Hermes installation (verified: tool not in the available-tools list).
Any protocol that instructs `send_message --target discord:#channel` will fail
with `Tool 'send_message' does not exist.` Use Path A (`hermes send`) or Path D
(webhook scripts) instead. The `discord-cron-delivery.md` reference in the
social-media skill has the full translation table.

## Path D — pre-existing cron delivery scripts (fallback when `hermes send` is unavailable)

These scripts consume `--format` output, POST each block with the correct
Cloudflare-bypassing User-Agent, and print the delivered IDs. Use when the
`hermes send` CLI is not reachable from the current environment.

- `/root/.hermes/scripts/_cron_deliver_osc_blocks_via_webhook.py` — oscillator alert blocks (current alert type)
- `/root/.hermes/scripts/_cron_deliver_pending_osc_now.py` — same, alternate name
- `/root/.hermes/scripts/_cron_deliver_osc_sell_now.py` — oscillator + sell combined
- `/root/.hermes/scripts/_cron_deliver_stock_sell_pending_now.py` — sell alerts
- `/root/.hermes/scripts/_cron_deliver_stock_sell_webhook_now.py` — sell alerts via webhook
- `/root/.hermes/scripts/_cron_deliver_pending_blocks_now.py` — generic pending blocks

All of them read `DISCORD_SELL_WEBHOOK` from `/root/.hermes/alert_webhooks.env` or
the environment, set a browser-like `User-Agent`, POST each block, print
`DELIVERED id=... http=204`, and end with `IDS: <space-separated ids>`. Run the
script directly; it handles `--format` internally.

## Path C — webhook direct (fallback when scripts are unavailable)

When none of the above scripts exist or are runnable, deliver directly to the
Discord webhook via `DISCORD_SELL_WEBHOOK` env var using a browser User-Agent.

## Webhook env-var → channel mapping

- `DISCORD_SELL_WEBHOOK` = webhook named **"Hermes Stock Alerts"** → the
  `#stock-sell-alerts` channel. This is the dedicated sell-alerts webhook.
- `DISCORD_ALERT_WEBHOOK` = legacy alias for the SAME `#stock-sell-alerts` channel
  (== sell). Either env var works for stock alerts; prefer `DISCORD_SELL_WEBHOOK`.
- `DISCORD_KSFII_WEBHOOK` = webhook named **"KSFII hook"** → a different (KSFII)
  channel. Do NOT use it for stock alerts.
- Identify which is which with a `GET` to the webhook URL (see "Verify without
  posting" below) — it returns JSON including `"name"` (and `channel_id`).

## CRITICAL GOTCHA — default urllib User-Agent → HTTP 403 (Cloudflare error 1010)

`urllib.request.urlopen` POSTs to a Discord webhook **fail with `HTTP 403`**, even
though a `GET` to the same URL returns `200` and the webhook JSON. The block is
**Cloudflare's WAF in front of Discord** (the POST response body is
`error code: 1010`), NOT a Discord-side auth failure — the default
`Python-urllib/X.Y` User-Agent is on Cloudflare's reject list.
(Verified 2026-08-27: default UA → `403 error code: 1010`; a browser UA → `204`.)

- Symptom: `GET` works, every `POST` with the default UA returns 403/1010.
- Fix option A (curl, simplest):
  `curl -s -o /dev/null -w "%{http_code}" -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" -H "Content-Type: application/json" -d '{"content":"..."}' "$DISCORD_SELL_WEBHOOK"` → returns `204` on success.
- Fix option B (Python): set a **browser-like** `User-Agent` on the `Request`:
  `urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})`.
- A custom token UA (e.g. `HermesAlertBot/1.0`) also usually passes, but if you
  still see `1010`, switch to the full browser UA above — that is the verified one.
- Always send `{"content": "<formatted text>"}`. Markdown (`**`, `_`, emoji) is
  rendered by Discord. Keep each message ≤2000 chars (these blocks are short).
- A ready-to-run Python helper that posts with the correct UA is in this skill's
  `scripts/deliver_alert_blocks.py` (takes a `blocks.json` of
  `[{"id","message"}]`, prints `<id> -> HTTP <status>`).

## Verify the webhook WITHOUT posting (GET)

Never POST a "test" message to check the webhook (see hazard below). Instead, send
a `GET` to the webhook URL (with a non-default UA — even a GET 403s under the
default `Python-urllib` UA) and read the returned JSON: it includes `"name"`
(e.g. `"Hermes Stock Alerts"`) and `"channel_id"`. That confirms the channel and
validity with zero side effects:

```bash
curl -s -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" "$DISCORD_SELL_WEBHOOK"
```

## Stray test-message hazard (cannot be deleted)

Webhook POSTs return `204` with **NO body**, so you never get the message `id` back.
There is also **no Discord bot token configured** in this environment. Consequence:
a message you POST by mistake (e.g. a debugging `"test"`) **cannot be deleted** and
will sit in the channel. Mitigations:

- Validate the webhook via `GET` (above) — never a POST test.
- Post only the real, parsed alert blocks.
- If you must smoke-test delivery, do it against a throwaway/known channel, not
  `#stock-sell-alerts`.

## Two-step delivery recipe

1. `python3 /root/.hermes/scripts/sqlite_alert_consumer.py --format`
   → prints `@@ALERT@@ id=<ID>` … `@@END@@` blocks, or `[NO ALERTS]`.
   If `[NO ALERTS]`, stop (report `[SILENT]`).
2. For each block, deliver the inner `<formatted message text>` to `#stock-sell-alerts`.
   - **Primary (preferred):** `hermes send --to discord:#stock-sell-alerts --file <tempfile>` (Path A).
     Inline text also works for short single-block messages.
   - **Fallback (bare cron / no hermes CLI):** run one of the `/root/.hermes/scripts/_cron_deliver_*_now.py` scripts (Path D) — they handle parsing, UA, and POSTing automatically.
   - **Fallback (webhook direct):** POST to `DISCORD_SELL_WEBHOOK` with a browser `User-Agent` (curl or `scripts/deliver_alert_blocks.py`).
   Collect the `<ID>`s delivered.
3. `python3 /root/.hermes/scripts/sqlite_alert_consumer.py --commit <ID1> <ID2> ...`
   → marks them `completed` and purges stale rows.
4. **Verify:** re-run `--format`; it MUST print `[NO ALERTS]`. If pending alerts remain,
   the commit failed or IDs were incomplete — re-deliver the remaining IDs before
   reporting done.
5. Report a one-line summary (count delivered), not a re-summary of contents.

## Minimal curl loop (bash) — single-line blocks only

```bash
while IFS= read -r line; do
  curl -s -o /dev/null -w "delivered HTTP %{http_code}\n" \
    -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" \
    -H "Content-Type: application/json" \
    -d "$(printf '{"content":"%s"}' "$line")" "$DISCORD_SELL_WEBHOOK"
done < <(python3 /root/.hermes/scripts/sqlite_alert_consumer.py --format | sed -n '/@@ALERT@@/,/@@END@@/p' | grep -v '@@')
```

(For multi-line blocks, prefer the `scripts/deliver_alert_blocks.py` helper or
building JSON in Python to avoid shell-escaping the newlines/emoji — the single-line
curl loop above mangles multi-line formatted messages.)
