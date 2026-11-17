# KSFII Lead Scoring Criteria — Detailed Rubric

## Score 6 — FRESH LEAD (Priority Hot)

**Definition**: Posted within 14 days, explicitly asking for recommendations or help, clear budget/product signal, specific location (city + province).

**Required criteria (ALL must be met):**
- Age: ≤14 days
- Intent: Explicit "looking for X", "recommend me X", "anyone have X", "need help with X"
- Location: City + province (e.g., "Edmonton, AB", "Calgary SW")
- Shopping signal: Actively shopping, comparing quotes, frustrated with current provider, asking for alternatives

**Example from this run:**
> r/Edmonton — "Auto insurance is getting crazy…" — TD renewal $3,996→$4,500. Zero claims, zero tickets. 2014 Hyundai Accent. Asking for company recommendations. Age: 14 days. Score: 6.

**Why it scores 6**: Fresh (14 days), explicit asking behavior, clean risk profile (good customer), price pain driving active shopping, specific location.

---

## Score 5 — HIGH INTENT

**Definition**: Clear need, actively seeking, good location data, strong product interest. May be slightly older than 14 days or missing one Score-6 criterion.

**Required criteria (at least 3 of 4):**
- Age: ≤30 days (or older but resurfaces as active discussion)
- Intent: Clear need expressed ("I need", "I'm looking for", "Can anyone help")
- Location: City + province OR province with specific neighborhood
- Product interest: Specific product type identified (auto, life, home, financial planning)

**Examples from this run:**
- r/alberta — New UK immigrant, $6-7K/yr auto insurance as "new driver", actively seeking cheaper options, Alberta. Score: 5.
- r/InsuranceCanada — Buying house, union covers 90% for them only, partner NOT covered, seeking life insurance for partner, first-time buyer. Score: 5.
- r/Calgary — Home insurance +500% after hailstorm, NW Calgary, Max Insurance, shopping around, quotes all ~$8K/yr. Score: 5.
- r/Edmonton — Inheritance, looking for financial planner, posted from throwaway (privacy concern), wants to know who to AVOID. Score: 5.

---

## Score 4 — MODERATE INTENT

**Definition**: Needs identified, some shopping intent, decent location info. May lack freshness, explicit asking, or specific budget signal.

**Required criteria (at least 2 of 4):**
- Age: ≤90 days (or older but in active discussion thread)
- Intent: Need expressed but may be implicit or background context
- Location: Province + general area, or city only
- Product interest: General category identified

**Examples from this run:**
- r/alberta — Looking for financial advisor in Calgary SW, worried about pyramid schemes. Score: 4. (Location specific, clear concern, but older post — 1 year — and no active shopping signal.)
- r/PersonalFinanceCanada — Terminally ill husband, NO critical illness insurance, caring leave, seeking financial guidance. Score: 4. (High need, insurance gap identified, but sensitive situation requires careful approach — not a cold pitch.)

---

## Score 3 — WEAK SIGNAL

**Definition:** Older post, deleted author, vague need, or thin data. Still relevant keywords but insufficient for active outreach.

**Characteristics:**
- Age: >90 days, often much older
- Intent: Vague or only implicit
- Location: Province only or missing
- Data quality: Deleted author, minimal comments, no clear action signal

**Examples from this run:**
- r/Calgary — Fee-based financial planner seeker, posted 2023, distinguishes "planner" from "advisor". Score: 3. (Keyword-rich and sophisticated, but very old.)
- r/alberta — Car insurance broker recommendations, deleted author. Score: 3. (Thin data, old.)

---

## Score 2 — ALREADY CONVERTED / REFERRAL ONLY

**Definition:** Poster has already switched providers or solved their problem. Not a lead for outreach, but may be a referral source.

**Example from this run:**
- r/alberta — "House Insurance" — switched from TD to Economical via INOVA brokers, saved $3,500/year. Score: 2. (Already converted. May know others facing similar issues — referral potential.)

---

## Score 1 — NOT A LEAD

**Definition:** Irrelevant, archived/locked with no actionable intent, wrong geography, or clearly not a potential client.

**Do not pursue.**

---

## Scoring Decision Tree

```
Is the post ≤14 days old?
  YES → Does the poster explicitly ask for recommendations/help?
    YES → Is location city+province?
      YES → Does the poster show active shopping behavior?
        YES → SCORE 6
        NO  → SCORE 5
      NO  → SCORE 4
    NO  → SCORE 4
  NO  → Is the post ≤30 days old?
    YES → Is there clear intent + location?
      YES → SCORE 5
      NO  → SCORE 4
    NO  → Is it ≤90 days with relevant keywords?
      YES → SCORE 3
      NO  → SCORE 2 or 1
```

---

## Multi-Product Potential Bonus

Add +1 to the base score (capped at 6) when the lead shows signs of multi-product potential:

- **New immigrant to Alberta/Canada**: Auto now → tenants/home soon → life/business later
- **First-time homebuyer**: Mortgage protection / life insurance → home insurance → future wealth planning
- **New business owner**: Commercial insurance → personal coverage → succession planning
- **Inheritance recipient**: Wealth management → estate planning → tax optimization → insurance review
- **Family formation** (new child, marriage): Life insurance → disability → education savings → mortgage protection

---

## Lead Scoring Quick Reference

| Signal | Points |
|--------|--------|
| ≤14 days old | +2 |
| ≤30 days old | +1 |
| Explicit "looking for/recommend me" | +2 |
| Clear need expressed | +1 |
| City + province location | +1 |
| Province only | +0.5 |
| Active shopping (quotes, comparing, frustrated) | +1 |
| Price pain mentioned | +1 |
| Specific product identified | +1 |
| High-net-worth indicator (inheritance, business) | +1 |
| Multi-product potential | +1 (cap at 6) |
| Already converted | -3 (min score 2) |
| Sensitive/health situation | No score change — flag for human review |
