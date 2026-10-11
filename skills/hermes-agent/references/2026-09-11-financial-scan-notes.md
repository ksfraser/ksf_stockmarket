# Financial Advisory Lead Scanning — 2026-09-11 Session Notes

## Web search results that produced actionable leads

### Query patterns that worked

**Reddit financial advisor seeking (Alberta):**
```
site:reddit.com insurance financial advisor Alberta Calgary Edmonton 2026
site:reddit.com/r/PersonalFinanceCanada insurance Alberta 2026
site:reddit.com/r/alberta "financial advisor" Calgary 2026
```
These returned the core actionable leads: Calgary SW advisor seeker (Score 6), Edmonton inheritance seeker (Score 5), life insurance beginner (Score 4), AMA comparison shopper (Score 4).

**Reddit auto insurance pain points:**
```
site:reddit.com/r/alberta car insurance AMA quote 2026
site:reddit.com/r/alberta "moved from" Alberta insurance 2024 2025 2026
site:reddit.com/r/alberta new driver insurance cost comparison
```
Returned: UK expat $6K/year shock (Score 5), AMA comparison thread (Score 4), new driver cost discussion (Score 3).

**General web competitive landscape:**
```
"financial advisor" Calgary OR Edmonton Alberta recommendation independent fee-only 2026
```
Returned the competitive landscape: Money Coaches Canada, Tetrault Wealth, Moraine Wealth, Ascendant Financial, Cresco/Wellington-Altus, Cardinal Point, Maple Groove Financial (Trevor Lawrence CFP/CIM), McGuire Financial Group. Useful for market awareness and competitive differentiation messaging.

### Queries that returned empty

These returned 0 results in this session — may be too narrow or the search backend may have limited Reddit crawl depth:
```
site:reddit.com/r/alberta car insurance renewal increased rate shock 2025 2026
site:reddit.com/r/Calgary auto insurance broker new driver young driver 2026
site:reddit.com/r/Edmonton life insurance mortgage protection first time home buyer 2026
site:reddit.com/r/InsuranceCanada life insurance term life Alberta 2026
```

### Reddit subreddits with active financial leads (Alberta)

| Subreddit | Lead type | Notes |
|-----------|-----------|-------|
| r/alberta | Auto insurance pain, life insurance beginners, financial advisor seeking, newcomer insurance shock | Highest yield for Alberta-specific leads |
| r/Calgary | Financial advisor recommendations, fee-only advisor discussions | Calgary SW affluent segment |
| r/Edmonton | Financial advisor seeking, inheritance planning | Edmonton market, smaller volume |
| r/PersonalFinanceCanada | Life insurance shopping, advisor recommendations, inheritance planning | Canada-wide but Alberta posters identifiable |
| r/InsuranceCanada | No Alberta-specific results this run | Low yield for this vertical |

### Recurring lead archetypes (financial advisory, Alberta)

1. **"I need a financial advisor" — Calgary SW** (Score 6)
   - Explicitly anti-pyramid-scheme, wants independent/fiduciary
   - Calgary SW = affluent area, premium market
   - Key messaging: CFP credentials, fee transparency, independent model, fiduciary duty

2. **"I have money sitting idle" — inheritance** (Score 5)
   - Edmonton $75K inheritance example
   - Self-identified financial inexperience (no TFSA/RRSP)
   - Key messaging: comprehensive plan, RRSP/TFSA optimization, insurance review, debt check

3. **"Insurance is shockingly expensive" — newcomer** (Score 5)
   - UK expat: 5 years experience, $6K/year quote
   - International driving experience not recognized
   - Key messaging: broker comparison across 10+ carriers, newcomer specialist, multi-product (auto + life + mortgage + RRSP)

4. **"I'm comparing quotes right now" — active shopper** (Score 4)
   - AMA comparison: convenient but not cheapest
   - Key messaging: independent broker can beat AMA on price while matching convenience

5. **"I'm overwhelmed, where do I start?" — beginner** (Score 4)
   - First-time life insurance shopper
   - Key messaging: education-first, term vs. mortgage insurance, coverage gap analysis, hand-holding

6. **"I want to avoid my bank" — anti-conflict** (Score 3-4)
   - Edmonton financial advisor seeker avoiding bank advisors
   - Key messaging: independent, no product bias, fiduciary standard

### Scoring calibration notes (this run)

- **Score 6**: Active thread (CairnMom, r/alberta) — still receiving engagement, explicitly seeking, specific affluent location. Only score 6 lead this run.
- **Score 5**: Clear capital signal ($75K inheritance) or strong price shock (UK expat $6K). Both have multi-product potential.
- **Score 4**: Good intent but either older post or vague location. Community already recommending independent brokers (aligns with KSFII model).
- **Score 3**: Older posts (2023), thin intent, informational rather than direct asking. Still valuable for market awareness.

### Delivery

- SMTP: `smtp_send.py` to `fraser.ks@gmail.com` succeeded on first attempt (exit 0)
- No fallback chain needed this run
- Discord: auto-delivered by cron scheduler
