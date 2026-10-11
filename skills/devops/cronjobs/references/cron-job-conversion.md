# Cron Job Conversion — FHS, KSFP, ASPD (2026-09-16)

## What was broken

Three cron jobs were running as `no_agent: true` shell scripts that hit PullPush.io Reddit API:

| Job ID | Name | Script | Last successful run | Problem |
|--------|------|--------|---------------------|---------|
| `1ffb1334b730` | Reddit Lead Response — Fraser Highland Shoppe | `reddit_scan_fhs.sh` | 2026-09-06 | HTTP 429 every run since |
| `b461da09fa1d` | Reddit Lead Response — K.S. Fraser Piping | `reddit_scan_ksfp.sh` | 2026-09-06 | HTTP 429 every run since |
| `3479b35ac955` | Reddit Lead Response — ASPD Pipe Band | (direct `reddit_scan_common.sh` call) | 2026-09-06 | HTTP 429 every run since |

All three called `bash reddit_scan_common.sh <LABEL> <QUERY>` which hits only `https://api.pullpush.io/reddit/search/submission/` — a single endpoint that had been rate-limiting (HTTP 429) for 3+ months.

## Detection

From `cronjob action=list` output, the pattern is:

```json
{
  "no_agent": true,
  "script": "reddit_scan_fhs.sh",
  "last_status": "ok",
  "last_run_at": "2026-09-13T08:15:53..."
}
```

And the output files (`/root/.hermes/cron/output/<job_id>/*.md`) all show:
```
FHS Reddit scan: source unavailable (HTTP 429) — no leads fetched
```

**Detection heuristic**: `no_agent: true` + `script: reddit_scan_*.sh` + last 3+ runs all show "HTTP 429" or "no leads fetched" = dead API endpoint. Convert immediately.

## Conversion steps

### Step 1: Write business-specific agent prompts

Each job gets a prompt that uses `web_search` across multiple source types. The prompts are tailored to each business:

- **FHS**: kilts, Scottish gifts, tartan, highland dress — 18 queries across Reddit (7), General Web (7), Forums (2), Facebook (2)
- **KSFP**: bagpipes, pipe band, bagpiper, highland dress, lessons — 16 queries across Reddit (5), General Web (5), Forums (1), Facebook (1)  
- **ASPD**: pipe band, bagpipes, highland games, drumming, recruitment — 18 queries across Reddit (6), General Web (6), Forums (1), Facebook (1)

The prompts follow the KSFII lead-response pipeline structure: SCAN → DEDUP → SCORE → REPORT, with explicit query templates per source type and scoring criteria (1-6 scale, minimum threshold 3+).

### Step 2: Convert cron jobs

For each job, call `cronjob action=update` with:
- `no_agent: false` (or omit)
- `script: ""` (clear the shell script reference)
- `skills: ["ksfii-lead-response"]`
- New business-specific `prompt`

Example for FHS:
```bash
cronjob action=update --job_id=1ffb1334b730 \
  --no_agent=false \
  --script="" \
  --skills='["ksfii-lead-response"]' \
  --prompt="<FHS-specific prompt with 18 web_search queries>"
```

### Step 3: Delete obsolete shell scripts

```bash
rm /root/.hermes/scripts/reddit_scan_fhs.sh
rm /root/.hermes/scripts/reddit_scan_ksfp.sh
rm /root/.hermes/scripts/reddit_scan_common.sh
```

### Step 4: Re-enable (they were paused during migration work)

```bash
cronjob action=resume --job_id=1ffb1334b730
cronjob action=resume --job_id=b461da09fa1d
cronjob action=resume --job_id=3479b35ac955
```

## 2026-09-17 KSFP run results (verification)

The KSFP job ran on 2026-09-17 and produced real leads via multi-source web_search:

| Score | Source | Intent | Notes |
|-------|--------|--------|-------|
| 5 | Facebook group | Beginner seeking lessons | Parent group post, youth pipeline |
| 4 | Reddit | CDPB recruiting | Competitor signal — healthy community pipeline |
| 4 | General web | Alberta events calendar | Calgary Celtic Festival Jul 4, Canmore Highland Games Sep, Red Deer Jun |
| 3 | General web | Older event-hire signal | Casual market present but aging |

Total: 4 new leads, 0 duplicates. Dedup DB updated. Report saved to `/tmp/ksfp_email.txt`.

This confirmed the multi-source web_search approach works for non-financial businesses (pipe band recruitment) — not just the original KSFII financial use case.

## Query template patterns used

### Reddit (highest intent signal)
```
site:reddit.com <INTENT> Alberta Calgary Edmonton Airdrie 2025 2026
site:reddit.com/r/Calgary <INTENT> 2026
site:reddit.com/r/Edmonton <INTENT> 2026
site:reddit.com/r/alberta <INTENT> 2026
site:reddit.com/r/bagpipes <INTENT> 2026
```

### General web — people looking to buy/learn
```
<INTENT> Calgary Alberta recommendation best
"<product>" store Edmonton Alberta
<product> Alberta buy <service>
"<service>" outfitters Calgary Alberta
```

### Canadian forums & local directories
```
site:alberta-local.ca OR site:findglocal.com <INTENT> Calgary AB
"<product>" OR "<service>" Calgary Alberta recommendation
```

### Facebook Groups
```
site:facebook.com <INTENT> Calgary Alberta group
"<product>" Calgary Alberta facebook group recommendations
```

## Why the old approach failed silently for 3 months

The `reddit_scan_common.sh` script has a tolerant error model — it never crashes, it just prints "source unavailable" and exits 0. This means:

1. The cron job status is "ok" (exit 0) even though it produced nothing
2. The output is a one-line "no leads fetched" message
3. Nobody notices because there's no alert for "zero leads for N consecutive runs"
4. The job keeps running every day, burning a cron tick, producing zero value

**Lesson**: `last_status: "ok"` does NOT mean the job is producing value. Check the actual output content, not just the exit status. A job that exits 0 but produces "no leads" for 3 months is broken.

## What to check before converting

1. **Is the skill loaded?** The target skill (e.g. `ksfii-lead-response`) must exist and have `web_search` as an available tool. Verify with `skill_view(name="ksfii-lead-response")`.
2. **Does the skill cover this business type?** The skill may be named for one business (KSFII Financial) but have business-variant guidance. The `ksfii-lead-response` skill explicitly documents how to adapt to other businesses (recruitment, services, events, Scottish/gift).
3. **What's the deliver target?** Preserve the existing `deliver` value (Discord channel ID) when converting. Don't change where results go.
4. **What's the schedule?** Preserve the existing schedule. The conversion changes HOW the job runs, not WHEN.
