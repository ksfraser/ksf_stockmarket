# Lead-Response Cron Job Conversion — Shell Script to Agent

## Background

On 2026-09-16, three lead-response cron jobs (FHS, KSFP, ASPD) were failing for 3+ months.
All three used `no_agent: true` with a shell script (`reddit_scan_*.sh`) that only hit the
PullPush.io Reddit API. PullPush.io returned HTTP 429 (rate-limited) on every run — zero leads
for 90+ days.

The fix was converting them to agent jobs using the `ksfii-lead-response` skill's multi-source
`web_search` approach.

## Before — Broken Pattern

```json
{
  "name": "Reddit Lead Response — Fraser Highland Shoppe",
  "script": "reddit_scan_fhs.sh",
  "no_agent": true,
  "schedule": "15 8 * * *",
  "deliver": "discord:1503814248344846397"
}
```

Shell script (`reddit_scan_fhs.sh`):
```bash
#!/bin/env bash
bash "$(dirname "$0")/reddit_scan_common.sh" "FHS" "kilt OR Scottish gifts OR tartan OR highland dress"
```

`reddit_scan_common.sh` — single API call:
```bash
curl -s -m 30 -w '%{http_code}' -G "https://api.pullpush.io/reddit/search/submission/" \
  --data-urlencode "q=$QUERY" --data-urlencode "size=10" \
  --data-urlencode "sort=new" --data-urlencode "fields=$FIELDS"
```

Problem: one API, no fallback, no reasoning, no web_search tool access.

## After — Working Pattern

```json
{
  "name": "Reddit Lead Response — Fraser Highland Shoppe",
  "skills": ["ksfii-lead-response"],
  "no_agent": false,
  "script": null,
  "schedule": "15 8 * * *",
  "deliver": "discord:1503814248344846397"
}
```

Agent prompt: business-specific scan instructions using `web_search` across:
1. Reddit (5-6 queries)
2. General web (5-7 queries)
3. Canadian forums / local directories (1-2 queries)
4. Facebook Groups (1-2 queries)

## Why Agent Jobs Work Better for Lead Scanning

| Factor | no_agent shell | agent with skill |
|--------|---------------|-----------------|
| Single API failure | Job produces nothing forever | web_search across multiple sources |
| Rate limiting | HTTP 429 = zero leads | try different sources, different queries |
| Query adaptation | Fixed query in shell script | Agent adapts queries based on results |
| Quality scoring | None (raw titles) | Agent scores leads 1-6 with reasoning |
| Business specificity | Separate shell script per business | One skill, business-specific prompt |

## Query Count per Business Type

**Retail/merchandise (FHS — kilts, Scottish gifts, tartan):**
- Reddit: 5 queries (broad + city-specific + niche subreddit)
- General web: 7 queries (shops, rentals, wedding, fabric)
- Forums/directories: 2 queries
- Facebook: 2 queries
- Total: 16 queries

**Instruction/performance (KSFP — bagpipe lessons, pipe band):**
- Reddit: 5 queries
- General web: 5 queries (lessons, hiring, performance, instruction)
- Forums/directories: 1 query
- Facebook: 1 query
- Total: 12 queries

**Community band (ASPD — pipe band recruitment, performances):**
- Reddit: 6 queries (broad + city + events + niche)
- General web: 6 queries (recruitment, events, societies, performances)
- Forums/directories: 1 query
- Facebook: 1 query
- Total: 14 queries

## Old Scripts Removed

- `/root/.hermes/scripts/reddit_scan_fhs.sh`
- `/root/.hermes/scripts/reddit_scan_ksfp.sh`
- `/root/.hermes/scripts/reddit_scan_common.sh`

## Post-Conversion Execution Results

### 2026-09-17 — First runs after conversion

**KSFP (K.S. Fraser Piping)** — 2026-09-17 08:36 UTC:
- 4 new leads inserted into dedup DB (score 5/4/4/3)
- Score 5: Facebook group post — parent looking for bagpipe lessons for child (beginner pipeline, youth aging-out potential)
- Score 4: CDPB (Calgary & District Pipe Band) recruitment signal — competitor intel + potential cross-referral
- Score 4: 2026 Alberta event calendar — Calgary Celtic Festival (Jul 4), Canmore Highland Games (Sep), Red Deer Highland Games (Jun) — event-opportunity leads
- Score 3: Older event-hire market signal — casual wedding/ceremony bagpiper demand
- 1 duplicate at score 2 excluded (already in DB)
- Sources: Reddit (5 queries, scanner timeout as expected), General web (5 queries), Forums (1), Facebook (1)
- Delivery: cron auto-delivery to discord:1503814224810610811
- **Confirmed**: multi-source web_search produces leads where single PullPush API produced nothing for 90+ days

**FHS (Fraser Highland Shoppe)** — 2026-09-17 08:20 UTC:
- 3 qualified leads found (scores 5, 4, 3)
- Lead 1 (score 5): Reddit post — visitor in Calgary asking where to buy a kilt for a wedding, specific timeline
- Lead 2 (score 4): Reddit post — person asking about Scottish wedding accessories in Edmonton
- Lead 3 (score 3): General web — tartan fabric inquiry from Alberta
- 4 additional entries inserted below score-3 threshold (monitoring only)
- Dedup DB schema verified live: `url` UNIQUE constraint confirmed, `date_scanned` column used (not `date_posted`)
- Market signal: summer/event season driving Scottish clothing demand; rental/merchandise bundle opportunity identified
- Delivery: cron auto-delivery to discord:1503814248344846397

### 2026-09-18 — Second runs confirm consistency

**FHS** — 2026-09-18 08:15 UTC:
- web_search primary (scanner timeout expected — PullPush.io still returning HTTP 429)
- 2 qualified leads (fhs-001 score 5, fhs-005 score 3), 4 deduped
- DB schema verified live
- Event-calendar signal confirmed: Canmore Highland Games, Calgary Celtic Festival, Red Deer Highland Games all referenced in leads
- Delivery confirmed via cron auto-delivery

**KSFP** — 2026-09-18 08:30 UTC:
- web_search primary (scanner timeout expected)
- 0 new qualified leads (4 new entries inserted below score 3)
- Dedup DB schema verified live
- Business-variant (KSFP bagpipe/recruitment) validated — different intent signals than FHS (lessons/recruitment vs. retail purchase)
- Delivery via cron auto-delivery to discord:1503814224810610811

## Key Takeaway

Any `no_agent: true` cron job that depends on a single external API should be a candidate for
conversion to an agent job with multi-source fallback. The `ksfii-lead-response` skill's SCAN
stage already documents the multi-source query templates — the agent prompt just needs to specify
the business's products/services and target geography.
