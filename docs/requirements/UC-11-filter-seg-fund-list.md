# UC-11: Filter the Seg-Fund list

**BABOK v2.0** | **Category:** Use Case | **Parent:** BR-11, FR-11
**Actor:** Advisor (Kevin)
**Trigger:** User opens `?action=seg_funds` and applies one or more filters.

## Main Flow
1. User opens `?action=seg_funds`. Page loads with no filters, full list.
2. User checks **Risk Rating = Medium** checkbox.
3. User checks **Death Benefit = 75%** and **Death Benefit = 100%**.
4. User selects **5Y Return bucket = "10–15%"** from the dropdown.
5. Page re-fetches with `?action=seg_funds&risk_rating=Medium&death_pct=75,100&bucket_5y=10-15`.
6. Result set shrinks; URL reflects filter state.
7. User clicks "Save Filters" → modal asks for name + public toggle.
8. User names screen "Conservative Dividend Growth" and clicks Save.
9. Page navigates to `?action=personal_screens&screen=42` showing the result set under
   the saved filter.

## Alternative Flows
- **A1: User clears filters.** Clicking "Clear" removes all params from URL and reloads
  the unfiltered list.
- **A2: User shares publicly.** During save, user ticks "Make Public" checkbox. The
  screen becomes visible to all logged-in users.
- **A3: User changes a filter live.** Any checkbox toggle re-fetches with the new state
  (no manual submit button).

## Postconditions
- A row exists in `user_screens` with the chosen filter JSON if Save was invoked.
- URL is shareable: anyone with the URL sees the same result set (filters live in URL;
  the named screen is a convenience for re-loading).

## UI
- 5 Risk Rating checkboxes (single-select per dimension, multi-value within).
- 2 Death Benefit checkboxes (75, 100), 2 Maturity Benefit (75, 100).
- 4 bucket dropdowns (1Y, 5Y, 10Y, YTD).
- "Clear" button on the right.
- "Save Filters" button is primary-blue.
