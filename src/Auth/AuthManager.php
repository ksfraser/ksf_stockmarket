<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth;

use Ksf\StockMarket\Model\Database;
use Ksf\StockMarket\Model\User as UserModel;

/**
 * AuthManager — orchestrates authentication providers.
 *
 * Responsibilities:
 *  - Register auth providers (local password + any number of plugin providers).
 *  - Expose the list of available redirect-based providers for the login UI.
 *  - Delegate credential validation to the right provider.
 *  - On successful auth, create or update the local users row and start a
 *    session via AuthController (so the rest of the app sees a normal session).
 *
 * This is the FA-style "provider registry" that makes it possible to add
 * Kerberos, LDAP, GSSAPI, OIDC, etc. by dropping in a new provider class and
 * registering it — no core login logic changes required.
 */
class AuthManager
{
    /** @var array<string, AuthProviderInterface> */
    private array $providers = [];

    /** @var array<string, array<string, mixed>> */
    private array $providerConfig = [];

    public function __construct()
    {
    }

    // ── Provider registration ────────────────────────────────────────────────

    /**
     * Register an auth provider instance.
     */
    public function register(AuthProviderInterface $provider, array $config = []): void
    {
        $name = $provider->getName();
        $this->providers[$name] = $provider;
        $this->providerConfig[$name] = $config;
    }

    /**
     * Get a registered provider by name, or null.
     */
    public function getProvider(string $name): ?AuthProviderInterface
    {
        return $this->providers[$name] ?? null;
    }

    /**
     * List of all registered providers.
     *
     * @return array<string, AuthProviderInterface>
     */
    public function getProviders(): array
    {
        return $this->providers;
    }

    /**
     * List of redirect-based providers suitable for rendering login buttons.
     *
     * @return array<string, AuthProviderInterface>
     */
    public function getRedirectProviders(): array
    {
        $out = [];
        foreach ($this->providers as $name => $p) {
            if ($p->isAvailable() && $p->isRedirectBased()) {
                $out[$name] = $p;
            }
        }
        return $out;
    }

    /**
     * Whether any provider is currently available.
     */
    public function hasAnyAvailable(): bool
    {
        foreach ($this->providers as $p) {
            if ($p->isAvailable()) {
                return true;
            }
        }
        return false;
    }

    // ── Authentication ────────────────────────────────────────────────────────

    /**
     * Authenticate using a provider that handles its own credential validation
     * (local password, LDAP bind, etc.).
     *
     * @param string $providerName  Registered provider name.
     * @param array<string, mixed> $credentials  Provider-specific credential blob.
     * @return array<string, mixed>|null  Normalized user on success, null on bad credentials.
     * @throws AuthProviderException  On provider errors.
     */
    public function authenticate(string $providerName, array $credentials): ?array
    {
        $provider = $this->getProvider($providerName);
        if ($provider === null) {
            throw new AuthProviderException("Unknown auth provider: $providerName");
        }
        if (!$provider->isAvailable()) {
            throw new AuthProviderException("Auth provider unavailable: $providerName");
        }

        $user = $provider->validateCredentials($credentials);
        if ($user === null) {
            return null; // bad credentials — not an exception
        }

        return $this->upsertLocalUser($user);
    }

    /**
     * Handle an OAuth/OIDC/etc. callback and return a normalized user.
     *
     * @param string $providerName
     * @param array<string, mixed> $callbackData
     * @return array<string, mixed>
     * @throws AuthProviderException
     */
    public function handleCallback(string $providerName, array $callbackData): array
    {
        $provider = $this->getProvider($providerName);
        if ($provider === null) {
            throw new AuthProviderException("Unknown auth provider: $providerName");
        }
        if (!$provider->isAvailable()) {
            throw new AuthProviderException("Auth provider unavailable: $providerName");
        }

        $identity = $provider->handleCallback($callbackData);
        $user = $provider->normalizeUser($identity);

        return $this->upsertLocalUser($user);
    }

    // ── Local user upsert ─────────────────────────────────────────────────────

    /**
     * Create or update the local users row for a successfully authenticated
     * identity, then return the full user row.
     *
     * This keeps the rest of the app unaware of which provider was used — every
     * logged-in user looks the same to controllers.
     */
    private function upsertLocalUser(array $normalized): array
    {
        $userModel = new UserModel();

        // Try to find an existing local account by email OR by provider+id.
        $existing = null;
        if ($normalized['email'] !== null && $normalized['email'] !== '') {
            $existing = $userModel->findByEmail($normalized['email']);
        }

        // If we didn't find by email, try provider linkage.
        if ($existing === null && isset($normalized['provider']) && isset($normalized['id'])) {
            // Look up by a provider linkage table if one exists; for now fall
            // back to username match which is what the local provider uses.
            $existing = $userModel->findByUsername($normalized['username']);
        }

        if ($existing !== null) {
            // Existing account — update display name if changed.
            $update = false;
            if (($existing['display_name'] ?? '') !== ($normalized['display_name'] ?? '')) {
                // We would update display_name here if we had an update() method.
                $update = true;
            }
            // Merge provider id into raw_payload for future linking.
            $existing['provider'] = $normalized['provider'];
            $existing['provider_id'] = $normalized['id'];
            return $existing;
        }

        // New user — create a local account.
        // Username derives from email local-part or display name fallback.
        $username = $this->deriveUsername($normalized);
        $email = $normalized['email'] ?? '';

        $userId = $userModel->create(
            $username,
            $email,
            bin2hex(random_bytes(16)), // random tmp password — user must reset
            $normalized['role'] ?? 'viewer',
            $normalized['first_name'] ?? '',
            $normalized['last_name'] ?? ''
        );

        $created = $userModel->findById($userId);
        $created['provider'] = $normalized['provider'] ?? '';
        $created['provider_id'] = $normalized['id'] ?? '';
        $created['password_reset_token'] = bin2hex(random_bytes(32));
        $created['password_reset_expires_at'] = date('Y-m-d H:i:s', strtotime('+24 hours'));

        // TODO: send a "welcome / set your password" email using the reset token.
        // error_log('[Auth] New social user created: ' . $username . ' email=' . $email);

        return $created;
    }

    /**
     * Derive a unique username from the normalized identity.
     */
    private function deriveUsername(array $normalized): string
    {
        // Prefer email local part.
        if ($normalized['email'] !== null && str_contains($normalized['email'], '@')) {
            $base = substr($normalized['email'], 0, strpos($normalized['email'], '@'));
            $base = preg_replace('/[^a-zA-Z0-9._-]/', '', $base);
            if (strlen($base) >= 3) {
                return $base;
            }
        }

        // Fall back to display name slug.
        $name = preg_replace('/[^a-zA-Z0-9]/', '', $normalized['display_name'] ?? 'user');
        if (strlen($name) >= 3) {
            return strtolower($name);
        }

        return 'user_' . bin2hex(random_bytes(4));
    }

    // ── Configuration ─────────────────────────────────────────────────────────

    /**
     * Get the config array for a provider.
     */
    public function getProviderConfig(string $name): array
    {
        return $this->providerConfig[$name] ?? [];
    }
}
