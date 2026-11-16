# BR-11: Seg-Fund Filtering & Risk / Benefit Decomposition

**BABOK v2.0** | **Category:** Business Requirement | **Priority:** Must Have
**Module:** Segregated Funds (`?action=seg_funds`)
**Author:** KSF | **Status:** Draft | **Date:** 2026-09-04

## Statement
The Seg-Fund list (`?action=seg_funds`) shall expose **risk rating**, **death benefit %**, and
**maturity benefit %** as first-class filterable dimensions in addition to the existing
**carrier**, **category**, and **series** filters. The yearly return columns
(`return_1yr / 3yr / 5yr / 10yr / 15yr / ytd / 1mo / 3mo / 30day / inception`) shall each be
filterable by a 5-bucket distribution so advisors can quickly bracket "top 20%", "above-median",
"bottom 20%" without typing numbers.

## Rationale
Advisors and clients selecting segregated funds for retirement accounts (LIRA, RRSP, TFSA)
care about three things above all else:
1. **Risk** — without a risk rating the list is unactionable (a "Conservative" fund is
   fundamentally different from an "Aggressive Growth" fund and they cannot be compared on raw
   return alone).
2. **Guarantee structure** — death and maturity benefit percentages drive the
   insurance-engine side of the product; the current `series` text (e.g. "75/75", "75/100",
   "100/100", "Basic 75/75", "Enhanced 75/100", "Optimal 100/100") is meaningful to an
   advisor but invisible to the database query layer. The numbers must be queryable so the
   advisor can say "show me all funds with death benefit ≥ 100%".
3. **Return distribution** — returns are currently a sortable column but not filterable by
   a bucket. A 5-bucket distribution ("≤5%", "5-9%", "10-15%", "16-20%", "≥20%") gives the
   advisor a one-click filter analogous to Amazon shopping facets.

## Current State (As-Is)
- `seg_funds.series` holds text like "75/75 A", "75/100 A", "100/100 F", "Basic 75/75",
  "Enhanced 75/100", "Optimal 100/100", "A-Class", "MPS4444", etc.
- No `risk_rating` column exists. Risk is implied by `category` (e.g. "Canadian Dividend
  Equity" vs "Global Equity") but not stored as a normalized value.
- Returns are sortable but not bucket-filterable.
- The filter UI (`templates/seg_funds.php`) offers carrier/category/series dropdowns and
  free-text search only.

## Target State (To-Be)
- New columns: `risk_rating ENUM('Low','Low-Med','Medium','Med-High','High')`, 
  `death_benefit_pct TINYINT`, `maturity_benefit_pct TINYINT`.
- Filter UI adds:
  - **Risk Rating** checkboxes (5 values)
  - **Death Benefit** checkboxes: 75, 100 (multi-select; "show me ≥75%")
  - **Maturity Benefit** checkboxes: 75, 100 (multi-select; "show me ≥75%")
  - **5Y Return** range: dropdown of 5 buckets (≤5%, 5-9%, 10-15%, 16-20%, ≥20%)
  - **10Y Return** range: same 5-bucket dropdown
  - **YTD Return** range: same 5-bucket dropdown
- Bucket boundaries are **computed from the live distribution** (NTILE(5) over the active
  return column) so the ranges are always meaningful, not hardcoded.

## Acceptance Criteria
1. Filtering by `risk_rating = 'High'` reduces the table to only funds explicitly rated
   High; "Equity" generic-category funds with no rating default to Medium.
2. Filtering by `death_benefit_pct IN (75, 100)` includes all `series` rows whose first
   number is 75 or 100 (including "75/75", "75/100", "100/100", "Basic 75/75", "Enhanced
   75/100", "Optimal 100/100").
3. Filtering by `5Y Return bucket = "10-15%"` returns only funds whose 5Y return falls in
   the 3rd NTILE-quintile of the active distribution.
4. All filters AND together (carrier AND risk AND death AND return bucket).
5. Filter state is reflected in the URL (`?risk=High&death=75,100&bucket5y=10-15`) so
   the view is shareable.

## Stakeholders
- Kevin Fraser (advisor / end user)
- Clients (downstream consumer of advisor-built screen outputs)

## Risks
- Bucket boundaries shift as new returns are loaded. The NTILE-based approach ensures
  buckets always have equal population, so the labels are stable in the *URL* but the
  numeric ranges move over time. Document this in the UI tooltip.

## Fund Screener Scoring (NEW - 2026-11)
### 4-Formula Weighted Scoring Model
The Seg-Fund list supports risk-adjusted screening via the `fund_screener` view
and a 4-formula weighted scoring model:

| # | Formula | Description |
|---|---------|-------------|
| **F1** | **Effective LT Return** | `10yr` with fallback to `5yr` if 10yr missing |
| **F2** | **Weighted Composite Return** | `0.45*10yr + 0.30*5yr + 0.15*3yr + 0.10*1yr` |
| **F3** | **Risk-Adjusted Score** | `composite_return / std_dev` |
| **F4** | **Hybrid Score** | `rank(composite) + rank(std_dev ascending)` |

**Weights rationale (8-year horizon):**
- 45% to 10yr annualized: aligns investment horizon (~8yr) with the longest
  available cycle (10yr ≈ 1.25x the horizon)
- 30% to 5yr: captures half-decade compound growth
- 15% to 3yr: medium-term resilience (e.g., post-COVID 2022 rate shock)
- 10% to 1yr: short-term momentum, dampened to avoid single-year noise

**Implementation:**
- MariaDB view: `fund_screener`
- Python scoring engine: `python/fund_screener.py`
- Output: `fund_screener_ranked.csv` + `fund_screener_top_risk_adjusted.csv`
- New tab on `?action=seg_funds`: "Screener" showing ranked results

**Data coverage:**
- 2,487 funds with valid composite scores (weighted composite = 45%*10yr +
  30%*5yr + 15%*3yr + 10%*1yr)
- 0 funds have `std_dev` populated in MariaDB `seg_funds` table at import time
- std_dev must be backfilled from `seg_fund_screen` table (`s.std`) before
  Formula 3 and 4 can be fully computed
- Recommend supplementing from Google Sheets export (which has full metrics)

## Related
- BR-11, FR-11
- `python/fund_screener.py`

- Existing `series` parsing must be tolerant of all observed text variants. The migration
  uses a regex `(\d{2,3})/(\d{2,3})` as the primary extractor with carrier-specific
  fallbacks (Beneva "Basic 75/75" → (75, 75)).

## Related
- FR-11: Seg-Fund Filter Engine
- BR-12: Personal Screens
- FR-12: Screen Persistence & Sharing
