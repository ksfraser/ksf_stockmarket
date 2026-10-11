# FHS (Fraser Highland Shoppe) — Event Pipeline & Scottish/Gift Lead Patterns

Session-derived observations from the 2026-09-17 cron run using `ksfii-lead-response` for Fraser Highland Shoppe (Scottish gifts, kilts, tartan, highland dress, Alberta).

## Alberta Event Pipeline (Recurring Annual)

These events were confirmed via web_search and event-directory queries during the scan. They represent recurring vendor/revenue opportunities for FHS.

| Event | Date (2026) | Location | Format | Opportunity |
|-------|-------------|----------|--------|-------------|
| Calgary Celtic Festival | July 4, 2026 | Spruce Meadows, Calgary, AB | Festival — piping, dance, athletics, vendors | Vendor booth; first step toward full Calgary Highland Games return in 2027 |
| Red Deer Highland Games | 4th Saturday June 2026 (since 1947) | Red Deer, AB | Highland Games — season kickoff in Alberta | Vendor booth; long-established event with loyal attendance |
| Canmore Highland Games | Sep 4-6, 2026 | Centennial Park, Canmore, AB | 3-day expanded format (piping, drumming, dance, athletics, Celtic vendors) | 34th year; vendor/sponsorship opportunity; free shuttle parking |
| Gathering of the Clans (GOTCHF) | Annual (date varies) | Sedgewick, AB | Highland festival — heavy events, dancing, petting zoo, artisans, food | Vendor booth; family-friendly audience |
| Prescott Highland Games | Oct 3-4, 2026 | Riverside Park, Prescott, AZ | Regional event (US side) — bagpipes, athletics, vendors | Cross-border opportunity; requires travel |

**Recommendation**: Contact event organizers 2-3 months ahead (vendor applications typically open early). Position FHS as a local Calgary-based Scottish merchandise supplier offering tartan products, gift bundles, and event-day accessories.

## Lead Type Variants for Scottish / Highland Businesses

The standard `ksfii-lead-response` pipeline uses `seeking_insurance`, `seeking_financial_advisor`, etc. For Scottish/gift/highland businesses, add these intent labels:

| Intent | Example Query / Post Pattern | Score Guidance |
|--------|------------------------------|----------------|
| `seeking_kilt_rental` | "Where to rent kilts in Calgary" (Facebook group); visitor for wedding/event | 5-6: Fresh (<7 days) + named city + explicit rental need |
| `event_opportunity` | Highland games, Celtic festivals, Scottish weddings listings | 4: Confirmed event date + organizer visibility + vendor potential |
| `buying_research` | "Best kilt shops", "tartan quality" discussions on Reddit/forums | 2-3: No Alberta location or old (>30 days) = low; fresh + city = moderate |
| `market_intel` | Competitor listings (The Highland Shoppe, The Scottish Shoppe), tourism features | 1-2: Not a direct lead but confirms market density and seasonal patterns |

## Facebook Group Pattern (High-Intent Template)

A concrete high-value lead pattern discovered in this session:

- Platform: Facebook group (e.g., AskCalgarians, local city/community groups)
- Pattern: "Where to [buy/rent/hire] [product] in [City]" — visitor or local asking for immediate supplier
- Indicators: Recent post (<7 days), named city, event context (wedding, visit, celebration), explicit request for recommendation or rental
- Response: Direct, helpful reply with pricing, availability, and quick contact — not a cold pitch

Example from this session: `fhs-lead-001` — AskCalgarians, "Where to rent kilts in Calgary" (visitor from Scotland, coming for wedding next week), score 5.

## Scoring Calibration for FHS Domain

| Factor | Financial Domain (original) | Scottish / Gift Domain (FHS) |
|--------|------------------------------|------------------------------|
| Freshness | <14 days = +2 | Same |
| Intent clarity | "looking for advisor" | "looking to rent/buy kilt" / "need Scottish gift" |
| Budget signal | Price shock / inheritance | Wedding/event budget (high) / visitor (unknown) |
| Location | Calgary / Edmonton / Airdrie | Same — event location = potential venue |
| Active shopping | "getting quotes" | "need rental for wedding next week" |
| Multi-product | New homeowner pipeline | Event vendor = merchandise bundles, gift packs, tartan accessories |

## Key Findings (Session 2026-09-17)

- 3 qualified leads found (1 Hot score 5, 2 Warm score 4) — all event-related or rental-related, no direct individual buyer discussion found on Reddit (consistent with niche market).
- Scanner timeouts confirmed (exit 124) — web_search fallback is the reliable primary path for this business domain.
- Market signals strong: tourism feature (July 2026), event calendar dense, competitor density high (3 established Calgary shops) — differentiation opportunity for FHS through gift-focused merchandise and event-specific bundles.
- No new Reddit buyer discussions in Alberta for Scottish merchandise — suggests the market is served through directories, events, and word-of-mouth rather than public forum posts. Event-based scanning is more productive than forum scanning for this domain.
