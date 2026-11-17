# Unit Test Outline — LLM Admin Console (UT-11.6)

Test the LLM provider fallback chain and admin settings.

## UT-11.6-001: LLMService fallback chain configuration

**Given** `system_settings` has `llm_primary_provider=openrouter`, `llm_secondary_provider=openai`, `llm_fallback_provider=ollama`, `llm_fallback_mode=failover`

**When** `LLMService::getInstance()` loads settings

**Then** the service has 3 provider configs in priority order: openrouter, openai, ollama

## UT-11.6-002: Failed primary falls through to secondary

**Given** primary provider returns HTTP 500

**When** `LLMService::complete()` is called

**Then** the service tries secondary provider and returns its response if successful

## UT-11.6-003: Rate limit triggers fallback

**Given** primary provider returns HTTP 429

**When** `LLMService::complete()` is called

**Then** the service logs the rate limit and tries secondary provider, without retrying primary

## UT-11.6-004: All providers fail returns null

**Given** primary, secondary, and fallback all return errors

**When** `LLMService::complete()` is called

**Then** the method returns null (graceful degradation per NFR-2.2)

## UT-11.6-005: round_robin mode cycles providers

**Given** `llm_fallback_mode=round_robin` with 3 providers configured

**When** `LLMService::complete()` is called 3 times successfully

**Then** each call uses a different provider in round-robin order

## UT-11.6-006: primary_only mode does not fallback

**Given** `llm_fallback_mode=primary_only`

**When** primary provider fails

**Then** the method returns null without attempting secondary or fallback

## UT-11.6-007: Admin settings save persists all LLM fields

**Given** admin POST to `?action=admin_settings` with all LLM fields

**When** `AdminSettingsController::saveSettings()` runs

**Then** all 12 LLM settings (primary/secondary/fallback × provider/model/key/url) are stored in `system_settings`

## UT-11.6-008: LLM keys are not exposed in UI

**Given** admin views `?action=admin_settings&tab=llm`

**When** the template renders

**Then** API key fields show masked values (e.g. `****`) or empty fields, never the raw key

---

*Prerequisite test infrastructure:* `tests/Unit/LLMServiceTest.php` — new file, follows existing `tests/Unit/AppTest.php` pattern. Requires mocking HTTP calls to LLM providers (use `Mockery` or PHPUnit built-in mocking for the curl calls in `LLMService`).
