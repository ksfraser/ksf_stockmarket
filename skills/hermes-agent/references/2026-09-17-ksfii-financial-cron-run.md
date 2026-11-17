# 2026-09-17 KSFII Financial Cron Run — Validation & Results

**Date:** 2026-09-17 | **Business:** KSFII Financial (insurance/financial advisory) | **Pipeline:** Full SCAN→DEDUP→SCORE→CRM→CONTENT→APPROVAL→POST→KB

## Scanner Outcome

- `reddit_scanner.py` returned **0 posts** (exit 0, not a timeout)
- Skipped `workflow.py` fallback per documented guidance
- Went directly to **multi-source web_search** as effective primary path

## Web Search Validation — Query Patterns

### Query 1: Broad Reddit intent + location + year (WORKED — 10 results)
```
site:reddit.com insurance financial advisor Alberta Calgary Edmonton 2025 2026
```
Surface-active threads in r/Calgary, r/alberta, r/PersonalFinanceCanada. Captured price-shock leads, carrier-displacement leads, financial advisor seekers.

### Query 2: Subreddit-targeted + insurance keywords (FAILED — 0 results)
```
site:reddit.com/r/PersonalFinanceCanada OR site:reddit.com/r/InsuranceCanada Alberta life insurance renewal 2026
```
Overly narrow subreddit targeting with AND semantics returned nothing. **Do not over-narrow.** Prefer Query 1's broader pattern.

### Query 3: City-targeted + intent + year (WORKED — 5 results)
```
site:reddit.com/r/Calgary OR site:reddit.com/r/Edmonton insurance broker financial planning recommendation 2026
```
Good for city-specific threads. Complements Query 1.

### Additional queries that proved valuable (beyond skill templates)

**Market data / news:**
```
Alberta insurance broker recommendation Calgary house auto renewal increased 2026
"looking for" OR "recommend" financial advisor insurance broker Calgary Alberta reddit OR forum 2025 2026
"house insurance" OR "home insurance" renewal doubled increase 2025 2026 Calgary Edmonton rant
```

These returned: Insurance Portal (Applied Systems Q2 2026), Global News (coverage denial T3J/T3N), CBC (StatsCan 400% hike), Canadian Underwriter (Surex two-tier analysis), competitor broker sites.

**Key insight:** Market-signal sources (news, industry pubs, broker review sites) are **first-class lead sources**, not just context. They surface carrier exits, coverage-denial patterns, rate-increase data, and competitor intelligence.

## Dedup DB Validation

**Live schema confirmed:**
```sql
CREATE TABLE scan_dedup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE, author TEXT, source TEXT, subreddit TEXT,
    title TEXT, date_scanned TEXT, lead_score INTEGER,
    intent TEXT, products_interest TEXT, location TEXT, notes TEXT
);
```

**Results:** 20 checked → 14 new inserts, 6 skipped (URL match). Author+title fallback coded but not triggered. Schema matches skill documentation. No mismatch.

## Scoring Validation

**Distribution:** 3 hot (5-6), 4 warm (4), 9 cold (3), 4 excluded (1-2)

**Score 6 — Market signal:** Q2 2026 Applied Systems data (Alberta +22.6% auto, +11.9% property — highest in Canada). Fresh (49d), Alberta-specific, amplifies all other leads, actionable context. Validates that market-signal leads can score 6.

**Score 5 — Two leads:** CairnMom (Calgary SW financial advisor, trust concern) + Global News coverage-denial (T3J/T3N displacement). Both validated as correct high-score awards.

**Score calibration:** Rubric produced reasonable distribution. No recalibration needed.

## Content Approach Validation

1. **Carrier-displacement angle** — Sonnet + Zenith exited Alberta → powerful framing: "your carrier abandoned you, let's find a new home"
2. **Credential-first for advisor leads** — Pyramid-scheme concern is #1 barrier. Lead with CFP, Alberta licensing, fiduciary duty, verification steps. Do NOT pitch products first.
3. **Coverage denial = strongest signal** — People denied coverage have no choice but to find new coverage. Higher intent than price-shopping.
4. **Two-tier market segmentation** — 7.5% good-driver cap creating abandoned segment. Position KSFII for everyone, not just easy cases.
5. **Forward-looking education** — Care-First/no-fault 2027 transition = proactive education opportunity.

## Delivery Validation

| Channel | Result |
|---------|--------|
| Email (fraser.ks@gmail.com) | ✅ SUCCESS — first attempt |
| Email fallback chain | Not needed |
| Discord | Cron auto-delivery |
| File | /tmp/ksfii_email.txt (14,845 bytes) |

## Market Signals (KB record)

1. Alberta insurance crisis — home +400%/20yr, auto +22.6% YoY Q2 2026, highest in Canada
2. Carrier exit displacement — Sonnet + Zenith exited Alberta residential market
3. Calgary SW = affluent advisor market — trust concerns are #1 barrier
4. Two-tier auto market — 7.5% cap creating abandoned segment
5. Coverage denial hotspots — T3J/T3N (northeast Calgary)
6. Care-First / no-fault transition by 2027
7. Competitor activity — Sharp (2981 reviews, 4.4★), Surex (digital-first, multi-lingual), BIG Insurance (Kensington NW, 20+ carriers, 5 languages), BrokerLink/Intact (largest presence)

## Pipeline Status

All 8 stages completed. No failures. No workarounds beyond documented web_search fallback.

## Artifacts

- `/tmp/ksfii_scan_posts.json` — 20 leads, canonical JSON
- `/tmp/ksfii_email.txt` — full report + delivery notes
- Dedup DB: 14 new rows

## What Not to Repeat

- Do NOT over-narrow subreddit queries with AND semantics (Query 2 → 0 results)
- Do NOT treat market-signal sources as "just context" — they are first-class lead sources
- Do NOT skip live schema inspection before inserting into dedup DB
