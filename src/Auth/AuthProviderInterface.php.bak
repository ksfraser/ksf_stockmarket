<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth;

/**
 * Authentication Provider interface.
 *
 * Every auth backend (local passwords, Google, Facebook, LDAP, Kerberos,
 * OIDC, etc.) implements this interface.  The AuthManager delegates to
 * registered providers to authenticate a user and return a user record.
 *
 * Loosely modelled on FrontAccounting's module/provider pattern so that new
 * authentication methods can be dropped in without touching core login logic.
 */
interface AuthProviderInterface
{
    /**
     * Human-readable name shown in the login UI (e.g. "Google", "LDAP").
     */
    public function getName(): string;

    /**
     * Icon/brand class or SVG identifier used by the login template.
     *
     * Return a simple string like 'fa-google' or 'fa-user'.  The template
     * decides how to render it.
     */
    public function getBrandClass(): string;

    /**
     * Whether this provider is currently configured and usable.
     *
     * A provider that is missing required env vars or has invalid credentials
     * should return false so the login form can hide its button.
     */
    public function isAvailable(): bool;

    /**
     * Return the URL to which the login form should redirect to start an
     * OAuth / OIDC / SAML / Kerberos handshake.
     *
     * Return null for local/authenticator providers that handle credentials
     * directly in validateCredentials() (e.g. LDAP bind, Kerberos ticket).
     */
    public function getLoginUrl(): ?string;

    /**
     * Handle an OAuth/OIDC/etc. callback.
     *
     * Called after the provider redirects back to our callback endpoint with
     * a code / token / ticket.  Should exchange the temporary credential for
     * a verified user identity and return a normalized user array.
     *
     * @param array<string, mixed> $callbackData  GET/POST params from the provider callback
     * @return array<string, mixed>  Normalized user record (see normalizeUser() docblock)
     * @throws AuthProviderException  On invalid code, network error, etc.
     */
    public function handleCallback(array $callbackData): array;

    /**
     * Validate credentials directly (non-OAuth providers: local password, LDAP
     * simple bind, Kerberos, etc.).
     *
     * @param array<string, mixed> $credentials  Framework-agnostic credential blob.
     * @return array<string, mixed>|null  Normalized user record or null on failure.
     * @throws AuthProviderException  On unexpected errors (not on bad credentials).
     */
    public function validateCredentials(array $credentials): ?array;

    /**
     * Normalize a provider-specific user identity into our canonical shape.
     *
     * The returned array MUST contain at minimum:
     *   - id        : string   Unique provider-side identifier (sub, dn, uid, etc.)
     *   - provider  : string   Provider name (matches getName())
     *   - email     : string|null
     *   - username  : string   Locally-unique username (derived or preferred)
     *   - display_name : string
     *   - avatar_url : string|null
     *
     * Additional fields are stored in raw_payload and made available to
     * implementers that need them.
     */
    public function normalizeUser(array $identity): array;

    /**
     * Whether this provider requires an interactive redirect (OAuth/OIDC) vs a
     * form-based credential entry (local/LDAP/Kerberos).
     */
    public function isRedirectBased(): bool;

    /**
     * Optional: scopes or configuration summary for debugging/admin UI.
     */
    public function getConfigSummary(): array;
}
