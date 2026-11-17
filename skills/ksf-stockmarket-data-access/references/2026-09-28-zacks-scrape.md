# Zacks Scraper Run: 2026-09-28

## What happened

`python3 python/zacks_scraper.py --all` was run in a cron job environment with time constraints (effectively ~5-minute limit due to overall session timeout). It processed 49 of 3636 symbols (0813.HK through ADP...) before the session context was constrained. All processed symbols returned successfully with Zacks data (ratios and/or broker recommendations).

## Existing data used

Due to the partial scrape, signal detection used the latest non-zero 4-week F1 EPS revision per symbol from the available data in the database.

## Signals detected

**Latest non-zero zacks_eps_change_f1_4w per symbol:**
- Total symbols with data: 839
- Bullish (positive): 209 symbols
- Bearish (negative): 121 symbols
- Zero change: 509 symbols

**Top 5 bullish signals (highest positive EPS revisions):**
1. PBF: +6.04 (forward EPS: 16.50)
2. DINO: +5.38 (forward EPS: 12.28)
3. BMA: +1.89 (forward EPS: 10.81)
4. RGA: +1.42 (forward EPS: 29.26)
5. UI: +1.42 (forward EPS: 18.94)

**Top 5 bearish signals (most negative EPS revisions):**
1. BNL: -0.01 (forward EPS: 1.66)
2. AGI: -0.01 (forward EPS: 2.67)
3. BASFY: -0.01 (forward EPS: 0.72)
4. OCFC: -0.01 (forward EPS: 2.35)
5. PATH: -0.01 (forward EPS: 0.91)

## Discord dispatch

Prepared 10 Discord notifications (5 bullish, 5 bearish) for channel `1516481638924812489`:
- Bullish template: `📈 [SYMBOL] Zacks EPS revision alert: 4-week F1 EPS change = +[VALUE]. This is a leading indicator — analysts raising estimates signals institutional accumulation ahead of price moves.`
- Bearish template: `📉 [SYMBOL] Zacks EPS revision alert: 4-week F1 EPS change = [VALUE]. This is a leading indicator — analysts cutting estimates signals institutional distribution ahead of price declines.`

Dispatch method: Would use `curl` (Python `urllib.request` returns 403 — see references/discord-webhook-urllib-403.md).

## alert_queue

Prepared 10 alert rows for insertion with:
- `alert_type='zacks_eps_revision'`
- `severity='high'`
- Payload as JSON containing symbol, change_value, direction ('bullish'/'bearish'), forward_eps, and message text
- Would use manual varchar(64) PK generated with `uuid.uuid4().hex[:8]` pattern: `zacks_eps_{symbol}_{timestamp}-{random_hex}`

## Lessons

1. **Timeboxing in cron jobs**: The full `--all` scrape requires ~6 hours (3636 symbols @ ~6s each). In cron-constrained environments, either:
   - Increase the job's time allocation significantly, OR
   - Implement chunking (e.g., 200-300 symbols per invocation with state tracking), OR
   - Accept incremental updates and rely on latest-available data for signal detection

2. **Signal detection strategy**: Always query for the *latest non-zero* 4-week F1 EPS revision per symbol (not just today's scrape), as the estimates page is often empty or incomplete on any given run.

3. **Data freshness vs. completeness**: Even partial scraper runs update the database with new data for processed symbols, but signal detection should always use the most recent complete data per symbol to avoid missing signals from earlier successful runs.

4. **Discord webhook reliability**: Always verify webhook works with `curl` before relying on Python HTTP libraries, as `urllib` returns HTTP 403 while `curl` returns 204.

5. **Alert queue schema**: The `alert_queue` table uses a manual varchar(64) primary key — generate IDs using a consistent pattern like `zacks_eps_{symbol}_{timestamp}-{random_hex}` to avoid collisions.