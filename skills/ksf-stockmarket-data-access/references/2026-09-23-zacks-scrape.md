# Zacks Scraper Run: 2026-09-23

## What happened

`python3 python/zacks_scraper.py --all` was run with a 300-second timeout. It processed 48 of 3636 symbols before timing out. No new data was written for tonight's date (2026-09-23).

## Existing data used

Signal detection fell back to the latest available scrape data: **fetch_date = 2026-09-04** (830 symbols with F1 EPS 4-week revision data in `fundamentals`).

## Signals detected

**Bullish (5):** PBF (+6.04), DINO (+5.38), BMA (+1.89), UI (+1.42), RGA (+1.42)

**Bearish (5):** INTU (-3.67), NUTX (-2.53), QFIN (-1.32), LULU (-1.28), CPA (-0.83)

## Discord dispatch

All 10 alerts sent to channel `1516481638924812489` via webhook. All returned HTTP 204 (success).

Dispatch method: `curl` (Python `urllib.request` returns 403 — see references/discord-webhook-urllib-403.md).

## alert_queue

All 10 rows inserted with `alert_type='zacks_eps_revision'`, `severity='high'`, `discord_dispatched=1`.

## Lessons

1. `--all` needs 6+ hours; never run with 300s timeout. Use chunking.
2. Always verify webhook works with curl before relying on Python HTTP libraries.
3. alert_queue has manual varchar PK — generate IDs with uuid.
