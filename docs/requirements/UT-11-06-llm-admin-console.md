# Unit Test Outline: UT-11-06 — LLM Admin Console

## Requirement Coverage
- FR-13: LLM Advisor Admin Screen
- BR-11: LLM Admin & Configuration

## Preconditions
- Test database with `system_settings` table
- Admin user account with admin role
- Mock LLM endpoints (or recorded responses) for connection testing

## Test Cases

### TC-11-06-01: Admin screen loads for admin user
**Given** an admin user is logged in
**When** the user navigates to `/admin/llm-config`
**Then** the page loads in < 2 seconds
**And** all three endpoint sections (primary, secondary, fallback) are visible
**And** the advisor-LLM profile assignment table is visible
**And** the connection health dashboard is visible

### TC-11-06-02: Admin screen denied for non-admin user
**Given** a non-admin user (trader or viewer role) is logged in
**When** the user navigates to `/admin/llm-config`
**Then** access is denied (403 or redirect to login)

### TC-11-06-03: Save primary endpoint configuration
**Given** the admin is on the LLM config screen
**When** the admin enters URL, model, and token for the primary endpoint
**And** clicks Save
**Then** the values are stored in `system_settings` with keys `llm_primary_url`, `llm_primary_model`, `llm_primary_token`
**And** the token is stored encrypted (not plaintext)

### TC-11-06-04: Save all three endpoints
**Given** the admin is on the LLM config screen
**When** the admin enters URL, model, and token for all three endpoints
**And** clicks Save
**Then** all 9 values (3 endpoints x 3 fields) are stored correctly
**And** the connection health dashboard shows the saved values

### TC-11-06-05: Test connection button - successful
**Given** a valid LLM endpoint URL and token are configured
**When** the admin clicks Test Connection on the primary endpoint
**Then** the system pings the endpoint
**And** the UI shows success status with latency (e.g., "Online (120ms)")
**And** the token is NOT logged or displayed in the response

### TC-11-06-06: Test connection button - failed
**Given** an invalid LLM endpoint URL is configured
**When** the admin clicks Test Connection
**Then** the UI shows failure status (e.g., "Offline (connection refused)")
**And** the error message does NOT contain the token (shows [REDACTED])

### TC-11-06-07: Add advisor-LLM profile mapping
**Given** the admin is on the LLM config screen
**When** the admin selects an advisor from the dropdown
**And** selects a LLM profile (primary/secondary/fallback)
**And** clicks Add mapping
**Then** a new row is added to `advisor_llm_profiles`
**And** the mapping appears in the assignment table

### TC-11-06-08: Remove advisor-LLM profile mapping
**Given** an existing advisor-LLM profile mapping
**When** the admin clicks Remove on the mapping
**Then** the row is deleted from `advisor_llm_profiles`
**And** the mapping disappears from the assignment table

### TC-11-06-09: Fallback chain routing
**Given** primary endpoint is configured but unreachable
**And** secondary endpoint is configured and reachable
**When** an LLM-enabled advisor makes a request
**Then** the system routes to the secondary endpoint
**And** the response is returned successfully

### TC-11-06-10: Fallback chain - all endpoints down
**Given** all three endpoints are unreachable
**When** an LLM-enabled advisor makes a request
**Then** the system returns an error or uses cached data
**And** no token values are leaked in the error message

### TC-11-06-11: Credential security - no token in logs
**Given** the system is configured with LLM tokens
**When** any operation is performed (save, test, query)
**Then** no log file, error message, or API response contains the token value in plaintext
**And** all token references show [REDACTED]

## Postconditions
- `system_settings` contains the configured LLM endpoint values
- `advisor_llm_profiles` contains the configured mappings
- No tokens are present in any log file or error output

## Related
- FR-13: LLM Advisor Admin Screen
- `docs/advisors/REQUIREMENTS_DESIGN.md` §LLM Admin Screen
- `docs/architecture/architecture-document.md` §10.8
