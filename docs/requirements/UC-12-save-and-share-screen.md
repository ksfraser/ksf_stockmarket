# UC-12: Save and share a personal screen

**BABOK v2.0** | **Category:** Use Case | **Parent:** BR-12, FR-12
**Actor:** Advisor (Kevin)
**Trigger:** User has built a filter combination they want to re-use or share.

## Main Flow
1. User navigates to `?action=personal_screens`. Page shows:
   - "My Screens" list (own, non-deleted)
   - "Public Screens" list (other users' is_public=1)
2. User clicks "Create New" → screen-builder opens at `?action=personal_screens&new=1`.
3. User picks universe (Stocks / Seg Funds), configures filters via the same controls as
   `?action=list` or `?action=seg_funds`. Result count updates live (with debounce).
4. User clicks "Save Filters" → modal asks for **name** (required), **description** (optional),
   **Make Public** checkbox (off by default).
5. User enters "Quality Compounder — Conservative", toggles Make Public on, confirms.
6. POST to `?action=personal_screens&op=save`. Server validates `filters_json`, inserts
   row, returns `{id: 42}`.
7. Page navigates to `?action=personal_screens&screen=42` showing the saved filter and
   its current result set.
8. Another user logs in, opens `?action=personal_screens`, sees the screen under
   "Public Screens" with `Quality Compounder — Conservative by Kevin · 2026-09-04`.

## Alternative Flows
- **A1: Edit existing screen.** From the list, user clicks "Edit" on a screen they own.
  Filter spec loads, user modifies, clicks "Save Filters" → POST `op=update&id=42`.
- **A2: Duplicate public screen.** User clicks "Duplicate" on a public screen → POST
  `op=duplicate&id=42` → new private screen owned by the current user, named
  "Copy of <original>".
- **A3: Delete + restore.** User clicks "Delete" → POST `op=delete&id=42`. Screen
  disappears from list but appears in "Trash" with a "Restore" button. After 30 days
  a nightly cron hard-deletes (`is_deleted=1 AND created_at < NOW() - INTERVAL 30 DAY`).
- **A4: Cross-user edit attempt.** User A tries to edit User B's private screen →
  `op=update` returns 403 with message "You don't own this screen and don't have edit
  permission."
- **A5: Anonymous user.** Public screens are visible to logged-in users only. Anonymous
  visitors are redirected to login.

## Postconditions
- Row in `user_screens` with `filters_json` matching the form state.
- If `is_public=1`, the screen is listed under "Public Screens" for all logged-in users.
- The result set is deterministic: reloading `?action=personal_screens&screen=42`
  applies the filters and renders the same rows (modulo data drift in source tables).

## Validation rules
- `name` 3–120 chars, required.
- `filters_json` must parse as JSON object.
- `universe` ∈ {'stocks','segfunds'}.
- Unknown filter keys → 400 (loud, not silent).
- `is_public` is 0/1; toggling to 1 requires explicit user confirmation.
