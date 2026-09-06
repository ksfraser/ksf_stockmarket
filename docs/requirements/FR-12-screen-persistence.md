# FR-12: Screen Persistence & Sharing

**BABOK v2.0** | **Category:** Functional Requirement | **Parent:** BR-12
**Module:** Personal Screens (`?action=personal_screens`)
**Author:** KSF | **Status:** Draft | **Date:** 2026-09-04

## Statement
The system shall persist named filter sets ("screens") per user, allow reload by ID, and
support a public flag that makes the screen visible to all logged-in users.

## Schema
- `user_screens` (new):
  - `id` INT AUTO_INCREMENT PK
  - `user_id` INT NOT NULL (FK → users.id)
  - `name` VARCHAR(120) NOT NULL
  - `description` VARCHAR(500) NULL
  - `universe` ENUM('stocks','segfunds') NOT NULL
  - `filters_json` JSON NOT NULL
  - `is_public` TINYINT(1) NOT NULL DEFAULT 0
  - `is_deleted` TINYINT(1) NOT NULL DEFAULT 0  (soft delete)
  - `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  - `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
  - INDEX `(user_id, is_deleted)`, INDEX `(is_public, is_deleted)`, INDEX `(universe)`
- `screen_shares` (new; optional for explicit per-user shares):
  - `screen_id` INT NOT NULL (FK → user_screens.id)
  - `shared_with_user_id` INT NOT NULL (FK → users.id)
  - `permission` ENUM('view','edit') NOT NULL DEFAULT 'view'
  - `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  - PK `(screen_id, shared_with_user_id)`

## Endpoints (under `?action=personal_screens`)
- `GET ?action=personal_screens` — list own + public screens.
- `GET ?action=personal_screens&screen=42` — load screen #42 (any user, with view perm).
- `POST ?action=personal_screens&op=save` — body: `name`, `universe`, `filters_json`,
  `is_public`. Returns new screen id.
- `POST ?action=personal_screens&op=update&id=42` — update name, description,
  `is_public`, `filters_json`. Author or shared-with-edit only.
- `POST ?action=personal_screens&op=delete&id=42` — soft-delete (author only).
- `POST ?action=personal_screens&op=restore&id=42` — undo soft-delete (author only,
  within 30 days).
- `POST ?action=personal_screens&op=duplicate&id=42` — copy filters into a new screen
  owned by the current user.

## Validation
- `filters_json` must validate against the per-universe filter spec (see BR-12):
  - `stocks` keys: carrier, change_1q/2q/4q/1y/2y/5y/10y (min/max pairs),
    lipper_total_min, zacks_eps_change_f1_4w_min, rsi_14_min/max, market_cap_min.
  - `segfunds` keys: carrier, category, risk_rating, death_pct, mat_pct, bucket_1y/5y/10y/ytd.
  - Unknown keys → 400 Bad Request with a list of unknown keys.

## Tests
- Save a screen, verify row in `user_screens` with `is_public=0`.
- Reload, verify filters reproduce the same result set.
- Toggle `is_public=1`, verify another logged-in user sees the screen in their list.
- Soft-delete, verify it disappears from default list but appears in trash.
- Cross-user edit attempt → 403.

## Risks
- Public screens reveal the advisor's filter logic to other users. The toggle is
  explicit; UI confirmation "Other users will see this filter spec" is required.
- Filter spec evolution: when a new filter dimension is added, existing screens don't
  have it; the engine treats missing keys as "no filter" (correct). Old unknown keys
  are rejected loudly to surface stale screens.

## Related
- BR-12, FR-11
- UC-12: Save and share a personal screen
