# BR-12: Personal Screens — Save, Load, Share

**BABOK v2.0** | **Category:** Business Requirement | **Priority:** Must Have
**Module:** All Symbols + Seg-Funds screener (`?action=personal_screens`)
**Author:** KSF | **Status:** Draft | **Date:** 2026-09-04

## Statement
The user shall be able to **define, save, name, reload, edit, delete, and optionally
publish** a set of filters against the All Symbols (stocks) view and the Seg-Funds list.
The intent is to let a user pin "the screen our personas would care about" — e.g.
*"`Lipper_Score ≥ 4 AND zacks_eps_change_f1_4w ≥ 5 AND rsi_14 < 70 AND mcap ≥ 1B AND
pe_ttm ≤ 25`"* — and have it reloadable on demand or shared with other users.

## Rationale
Every backtest persona (e.g. Value, Dividend Growth, Quality Compounder, Technical Breakout)
maps to a *specific* set of filters. Without screen persistence, the advisor rebuilds
the same filter set every time the page reloads. With persistence, a screen becomes a
*named, versionable, shareable asset* — the same way a TradingView preset works.

Sharing is useful because Kevin (advisor) often wants to show a client "here is what a
'Conservative Dividend Growth' screen looks like in our universe"; the client (or another
advisor on the team) can load the public screen without recreating it.

## Current State
- `?action=list` (All Symbols) and `?action=seg_funds` accept GET filters but don't
  persist them. Reloading clears state.
- No user-bound screen storage exists. TradingView presets live only on TV.
- No public/private screen concept.

## Target State
- New table `user_screens` (per-user):
  - `id`, `user_id`, `name`, `universe` ('stocks' | 'segfunds'),
  - `filters_json` (JSON-encoded filter spec),
  - `is_public` (TINYINT), `created_at`, `updated_at`.
- New table `screen_shares` (lightweight, optional; same DB):
  - `screen_id`, `shared_with_user_id`, `permission` ('view' | 'edit'),
  - `created_at`. (Public screens don't need an explicit share row — `is_public=1` is
    the share.)
- New page `?action=personal_screens`:
  - "Saved Screens" list (own + public), with **Load / Edit / Delete / Duplicate / Share**
    buttons.
  - "Create New" button → opens a screen-builder that mirrors the All Symbols / Seg-Funds
    filter panel with live results count.
  - "Save Filters" button → modal asks for **name** + **is_public** toggle.
- Public screens appear in the public list for any logged-in user; the author can
  toggle `is_public` off at any time.

## Screen JSON spec (filters_json)
```json
{
  "universe": "stocks",
  "filters": {
    "carrier": ["Canada Life", "Manulife"],
    "risk_rating": ["Low", "Low-Med"],
    "death_benefit_pct": [75, 100],
    "maturity_benefit_pct": [75, 100],
    "bucket_5y": "10-15",
    "bucket_10y": "8-12",
    "change_1q_min": -5, "change_1q_max": 5,
    "change_4q_min": 0,  "change_4q_max": 30,
    "change_1y_min": 0,  "change_1y_max": 50,
    "change_2y_min": null,"change_2y_max": 100,
    "change_5y_min": null,"change_5y_max": null,
    "change_10y_min":null,"change_10y_max": null,
    "lipper_total_min": 3,
    "zacks_eps_change_f1_4w_min": 5,
    "rsi_14_min": 0, "rsi_14_max": 70,
    "market_cap_min": 1000000000
  }
}
```
The screener engine validates unknown keys (rejects) and coerces types; missing keys mean
"no filter on this dimension".

## Acceptance Criteria
1. A logged-in user can save the current filter state of `?action=list` to a named
   screen, reload it later, and have the result set reproduce exactly.
2. The same applies to `?action=seg_funds`.
3. Marking a screen `is_public=1` makes it visible to all logged-in users; the screen
   list page shows "by <author> · <date>".
4. The author can flip `is_public` back to 0; non-authors no longer see the screen.
5. Deleting a screen is soft (`is_deleted=1`) and the author can restore from a trash
   view for 30 days.
6. URL is shareable: `?action=personal_screens&screen=42` loads screen #42's filters
   and renders the result set.

## Stakeholders
- Kevin Fraser (advisor / primary user)
- Clients (downstream consumers of public screens)

## Risks
- Filter spec drift: a future dimension added to the All Symbols view should be
  optional in the screen JSON. Reject unknown keys (don't silently ignore) so authors
  notice a screen that's now stale.
- Public screens could leak advisor IP. UI must make `is_public` an explicit checkbox
  with a confirmation ("Other users will see your filter spec").

## Related
- BR-11: Seg-Fund Filtering
- FR-11: Seg-Fund Filter Engine
- FR-12: Screen Persistence & Sharing
- UC-11: Filter the Seg-Fund list
- UC-12: Save and share a personal screen
