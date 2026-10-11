# Lead-Response Pipeline — Delivery Troubleshooting

## Delivery Model: Cron Auto-Delivery (PRIMARY)

### How cron delivery works

This pipeline runs as a **scheduled cron job**. The cron scheduler automatically delivers the agent's final response to the configured Discord destination. **Do NOT call `send_message`, `hermes send`, webhooks, or any direct delivery tool.** 

**Correct behavior:**
1. Produce the full report as the final response body
2. The cron system auto-delivers it to the configured target
3. If there is genuinely nothing to report, respond exactly `[SILENT]` (nothing else)

**What NOT to do:**
- Do NOT call `send_message` or `hermes send` — these will conflict with cron auto-delivery
- Do NOT use `curl` to Discord API or webhooks — the system handles delivery
- Do NOT combine `[SILENT]` with content — either report findings OR say `[SILENT]`

**"Skipped send_message" is expected:** If any delivery tool prints "Skipped send_message to discord:... This cron job will already auto-deliver its final response to that same target" — this is NOT an error. It confirms the cron auto-delivery model is working. Put content in the final response body.

---

## Fallback: When Auto-Delivery Fails

If the cron system does NOT deliver (rare — usually a configuration issue):

1. Save the full report to `/tmp/<business>_pipeline_report.md`
2. Note the delivery failure in the report itself
3. The report file serves as the permanent local record

---

## Email Delivery (KSFII-specific — legacy)

### Primary tool: `smtp_send.py`

```bash
python3 /root/.hermes/skills/.archive/investment-monitor/references/smtp_send.py \
  --to fraser.ks@gmail.com \
  --subject "KSFII Reddit Lead Report — [DATE]" \
  --body-file /tmp/ksfii_email.txt
```

### SMTP fallback chain

When SMTP rejects the recipient or times out, retry in this order:

1. `fraser.ks@gmail.com` (primary)
2. `fraser.ks@ksfraser.ca` (secondary)
3. `kevin@fraserhighlandshoppe.ca` (tertiary)

If ALL three fail:
- Save the email body to `/tmp/ksfii_email.txt`
- Note the SMTP failure in the pipeline report
- Continue — the report is still available locally

---

## "No Leads" Delivery

Even when the pipeline finds ZERO leads, it must still deliver a status confirmation:

- **Cron auto-delivery**: Produce a brief "no new leads" status report as the final response. The cron system delivers it.
- **Local file**: Write the status to `/tmp/<business>_pipeline_report.md`

**Respond with `[SILENT]` only when:**
1. There is genuinely nothing new to report AND
2. The cron auto-delivery has been confirmed working for this run

The `[SILENT]` convention suppresses cron delivery entirely. It is for "absolutely nothing happened this run" — not for "no leads found but here's a status report."

---

## Common Error Codes

| Error | Platform | Meaning | Fix |
|-------|----------|---------|-----|
| HTTP 403, code 1010 | Discord API | "Bots cannot use this endpoint" | Do NOT use raw API — rely on cron auto-delivery |
| HTTP 403 | Discord webhook | Webhook forbidden/missing | Do NOT use webhooks — rely on cron auto-delivery |
| HTTP 401 | Discord API | Unauthorized token | Do NOT use raw API — rely on cron auto-delivery |
| SMTP reject/timeout | Email (legacy) | Recipient rejected or server timeout | Retry next email in fallback chain |
| Exit code 124 | Scanner | Timeout (60s or 120s) | Fall back to `web_search` immediately — expected under cron |
| "Skipped send_message" | Hermes send | Cron auto-delivery conflict detected | Expected behavior — put content in final response |
| Raw HTTP to Discord API (urllib/requests/curl with Bot token or webhook URL) | Any | Attempted self-delivery when token absent or cron active | Anti-pattern — same class of mistake as `send_message`. The cron system auto-delivers the final response. Do not attempt your own HTTP delivery to Discord under any circumstances in a cron run, regardless of whether a token appears to be available. |
