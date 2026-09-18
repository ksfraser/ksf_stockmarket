# FR-13: LLM Advisor Admin Screen

## Requirement

The system shall provide an admin screen for configuring LLM provider URLs (primary, secondary, fallback), model names, and API tokens. Per-advisor LLM profile assignment, connection health status, and automatic fallback routing are supported.

## Business Context

BR-11 requires that LLM endpoints be configurable via an admin UI rather than hardcoded. The system uses a three-tier fallback chain: primary -> secondary -> fallback. When the primary endpoint is unavailable (timeout, error, rate limit, 5xx), the system automatically routes to the secondary, then to the fallback.

## Admin Screen Layout

URL: `/admin/llm-config` (or `?action=admin&view=llm-config`)
Role: admin only

### Primary Endpoint Section
- URL field
- Model name field
- API token field (password-masked input)
- Test Connection button

### Secondary Endpoint Section (fallback)
- URL field
- Model name field
- API token field (password-masked input)
- Test Connection button

### Fallback Endpoint Section (last resort)
- URL field
- Model name field
- API token field (password-masked input)
- Test Connection button

### Per-Advisor LLM Profile Assignment
- Advisor dropdown (lists all advisors)
- LLM config set dropdown (primary / secondary / fallback profiles)
- Add mapping button
- Remove mapping button
- Table of current advisor -> LLM profile mappings

### Connection Health Dashboard
- Primary: status indicator (Online/Offline) + latency
- Secondary: status indicator + latency
- Fallback: status indicator + latency
- Auto-refresh every 60 seconds

## Credential Storage

LLM tokens are stored in the `system_settings` table:
- `setting_name` = 'llm_primary_token', 'llm_secondary_token', 'llm_fallback_token'
- `setting_value` = encrypted token (password-type DB field)
- Tokens are never logged in plaintext
- All error messages and logs show `[REDACTED]` for token values
- Admin screen requires admin role to access

## Fallback Chain Logic

```
Primary LLM Endpoint (URL + model + token)
  -> on timeout / error / rate limit / 5xx:
Secondary LLM Endpoint (URL + model + token)
  -> on timeout / error / rate limit / 5xx:
Fallback LLM Endpoint (URL + model + token)
  -> on failure:
Return error / use cached data / skip analysis
```

Each LLM-enabled advisor (FR-11) is assigned one of the three config sets. The assignment is stored in an `advisor_llm_profiles` table:

| Column | Type | Description |
|--------|------|-------------|
| advisor_id | VARCHAR(50) NOT NULL | Advisor identifier |
| llm_profile | ENUM('primary','secondary','fallback') NOT NULL | Which config set to use |
| updated_at | TIMESTAMP | |

## Acceptance Criteria

- [ ] Admin screen accessible at `/admin/llm-config` (admin role only)
- [ ] Primary, secondary, fallback URL/model/token fields save to `system_settings`
- [ ] Token field is password-masked in the UI
- [ ] Test Connection button pings endpoint and reports latency + success/failure
- [ ] Connection health dashboard shows real-time status for all 3 endpoints
- [ ] Per-advisor LLM profile assignment table supports CRUD
- [ ] Fallback chain automatically routes primary -> secondary -> fallback on failure
- [ ] LLM tokens never appear in logs or error messages (always [REDACTED])
- [ ] Admin screen loads in < 2 seconds

## Related

- BR-11: LLM Admin & Configuration
- FR-11: LLM Fundamental Data Tables (LLM-enabled advisors that use the fallback chain)
- `docs/advisors/REQUIREMENTS_DESIGN.md` §LLM Admin Screen
- `docs/architecture/architecture-document.md` §10.8
- `docs/requirements/UT-11-06-llm-admin-console.md`
