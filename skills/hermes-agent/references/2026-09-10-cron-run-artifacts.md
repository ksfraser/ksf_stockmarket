# 2026-09-10 Cron Run — Artifacts and Effective Delivery Path

Reference for future cron executions of this pipeline. Captures what was produced, where, and what actually delivered.

## Run summary

- **Date:** 2026-09-10
- **Scanner:** `reddit_scanner.py` returned 0 posts; `workflow.py` timed out at 120s (exit 124). Both are expected cron behavior.
- **Effective data source:** `web_search` across r/alberta, r/Edmonton, r/Calgary, r/PersonalFinanceCanada (4 queries, 40 results total, 10 new leads after dedup).
- **Dedup DB:** `/root/.hermes/cache/scan_dedup.db` — 10 leads inserted into `posts`, `scan_dedup`, and `seen_posts`.
- **Leads scored:** 3 hot (score 5-6), 4 warm (score 4), 3 monitor (score ≤2).

## Artifacts produced

| File | Purpose | Size |
|------|---------|------|
| `/tmp/ksfii_email.txt` | Full pipeline report — email body | ~10.8 KB |
| `/tmp/ksfii_scan_posts.json` | 10 scored leads in pipeline JSON format | ~5.7 KB |
| `/tmp/ksfii_discord_summary.txt` | Condensed Discord summary (no emoji/variation selectors) | ~1.5 KB |

## Delivery results

| Channel | Status | Notes |
|---------|--------|-------|
| Email (smtp_send.py) | **Sent** | `fraser.ks@gmail.com` accepted on first attempt. |
| Discord (cron auto-delivery) | **Handled by cron** | Final response body is the full report; cron delivers automatically. |
| Discord (fallback summary) | **Saved, not sent** | `/tmp/ksfii_discord_summary.txt` exists if manual posting is needed later. Raw HTTP was NOT used. |

## What not to repeat

- Do **not** attempt raw HTTP delivery to Discord (urllib, requests, curl). The cron system auto-delivers the final response. Attempting it produced no value and risked conflicting with auto-delivery.
- Do **not** retry `reddit_scanner.py` or `workflow.py` after a timeout/zero result. Go straight to `web_search` as documented in the skill.
- If `DISCORD_BOT_TOKEN` is not set, skip Discord self-delivery entirely — save a summary file for manual posting and let cron handle the rest.

## Follow-up actions (manual)

- Post `/tmp/ksfii_discord_summary.txt` to the `#ksfii` Discord channel when credentials are available.
- Verify the email landed in the inbox (spam folder check for fraser.ks@gmail.com).
