# Lead Scoring — Alternative Factored Model

## When to Use This Instead of the Decision Tree

The decision tree in the main scoring-criteria.md works well for clean, fresh leads. But in web_search fallback mode (which is the default for cron), you often encounter leads that are older but have strong other signals — high-net-worth indicators, extreme price pain, specific locations, multi-product potential. The decision tree's "age first" orientation can under-score these.

The factored model below scores each dimension independently and sums them. It handles "old but valuable" leads better than the age-first decision tree.

**Rule of thumb:** Use the factored model when the lead comes from web_search (not direct scanner output) or when the lead is older than 30 days but has strong non-age signals.

---

## Factored Scoring Rubric

Score each dimension independently, then sum. Cap at 1-6.

### Dimension 1: Freshness

| Age | Points |
|-----|--------|
| ≤14 days | +3 |
| 15-30 days | +2 |
| 31-60 days | +1 |
| 61-90 days | 0 |
| >90 days | -1 |

### Dimension 2: Intent Clarity

| Signal | Points |
|--------|--------|
| Explicit "looking for X" / "recommend me X" / "anyone have X" + specific product/broker/advisor | +2 |
| Clear need expressed ("I need", "I'm seeking") but less specific | +1 |
| Implicit need or general discussion only | 0 |

### Dimension 3: Budget / Pain Signal

| Signal | Points |
|--------|--------|
| Price shock documented (specific % or $ amount, renewal increase) | +2 |
| High-net-worth indicator (inheritance, business asset, significant savings) | +2 |
| Active shopping behavior (got quotes, comparing, "shopping around") | +1 |
| Price mentioned as concern but no specific number | +1 |
| No budget/pain signal | 0 |

### Dimension 4: Location Specificity

| Signal | Points |
|--------|--------|
| Named city + province (e.g., "Calgary, AB", "Edmonton SW") | +2 |
| Province only (e.g., "Alberta") | +1 |
| Canada-wide or unspecified | 0 |

### Dimension 5: Multi-Product / Lifetime Value Potential

| Signal | Points |
|--------|--------|
| Two or more products/services of interest identified | +1 |
| Strong lifetime value indicator (new immigrant, new homeowner, inheritance, new business) | +1 |
| Single product, no expansion signal | 0 |

### Dimension 6: Active Shopping / Switching Signal

| Signal | Points |
|--------|--------|
| Explicitly shopping/switching ("looking to switch", "got a better quote", "tired of current provider") | +1 |
| No active shopping signal | 0 |

---

## Scoring Example: Good Insurance Broker (r/Calgary)

| Dimension | Signal | Points |
|-----------|--------|--------|
| Freshness | 373 days old | -1 |
| Intent clarity | "Good Insurance Broker" — looking for broker recs | +2 |
| Budget/pain | Zenith exit, 30% auto + 100% home increase, actively shopping | +2 |
| Location | Calgary, AB (city + province) | +2 |
| Multi-product | Auto + home insurance | +1 |
| Active shopping | "Actively shopping for a new broker" | +1 |
| **Total** | | **6** |

**Result: Score 6 (HOT)** — despite being 373 days old, the extreme price pain + active shopping + city-level location + multi-product bundle opportunity more than compensate.

---

## Scoring Example: What Are Some of the Best Life Insurance Companies? (r/alberta)

| Dimension | Signal | Points |
|-----------|--------|--------|
| Freshness | 366 days old | -1 |
| Intent clarity | "finally starting to look into life insurance" — beginner, seeking | +1 |
| Budget/pain | No price signal, no shopping behavior | 0 |
| Location | Alberta (province only) | +1 |
| Multi-product | Life insurance only, no expansion signal | 0 |
| Active shopping | No shopping signal | 0 |
| **Total** | | **2** |

**Result: Score 2 (SKIP)** — despite clear intent, the lack of budget signal, province-wide location, no shopping behavior, and old age make this a low-priority educational opportunity, not an active lead.

---

## Comparison: Decision Tree vs. Factored Model

| Scenario | Decision Tree | Factored Model | Which Is Right? |
|----------|--------------|----------------|-----------------|
| Fresh lead (≤14d), explicit ask, city location, shopping | Score 6 | Score 6 | Same — both correct |
| Old lead (300d+), extreme price shock, city location, multi-product | Score 3-4 (age penalty dominates) | Score 5-6 (signals compensate) | **Factored** — the price pain and location are real, the lead is valuable despite age |
| Medium lead (60d), vague need, province-only | Score 3 (decision tree mid-range) | Score 2-3 (thin signals) | Same — both correctly flag as weak |
| Old lead (200d+), high-net-worth ($75k inheritance), city location | Score 3 (age penalty) | Score 5-6 (inheritance + location compensate) | **Factored** — high-net-worth is a strong signal, worth pursuing even if post is old |

**Key insight:** The factored model's advantage is that it lets strong non-age signals (price shock, high-net-worth, city location, multi-product) compensate for age. In web_search fallback mode where you can't always get the freshest posts, this prevents throwing away valuable leads just because they're a few months old.
