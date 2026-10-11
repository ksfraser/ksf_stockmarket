# External Auth Architecture Notes

## Tables
- `external_auth_tokens`: per-user/per-provider tokens with expiry/refresh
- `system_settings`: app credentials stored as [REDACTED] password-type values

## Controller flow
`ExternalAuthController`:
- `authorize()` — builds provider-specific authorize URL, redirects
- `callback()` — exchanges code for token, INSERT ... ON DUPLICATE KEY UPDATE
- `revoke()` — DELETE by user+provider

## Extensibility pattern
To add a new provider:
1. Add entry to `ExternalAuthController::$map` with `client_url`, `token_url`, `scopes`, `pkce` bool
2. Add config keys in `AdminSettingsController::$allowedKeys`
3. Add fetch function in `research_agent.py` following `_reddit_search(conn, ...)` pattern
4. Add setting defaults in `AdminSettingsController::getSettings()`

## Security rules
- Client secrets: `password` type in `system_settings`, never displayed in plaintext
- Access/refresh tokens: stored as `password` semantics, masked in UI/logs
- All error messages use `[REDACTED]` instead of real tokens
- Revoke endpoint returns success/failure without exposing token values
