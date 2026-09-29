<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth\Provider;

use Ksf\StockMarket\Auth\AuthProviderInterface;
use Ksf\StockMarket\Auth\AuthProviderException;

/**
 * Base class for OAuth2 / OpenID Connect providers.
 *
 * Concrete providers (Google, Facebook, generic OIDC, etc.) extend this class
 * and only need to supply the provider-specific configuration and user info
 * mapping.  The authorization URL construction, state management, and callback
 * token exchange are handled here.
 *
 * Loosely inspired by thephpleague/oauth2-client but kept minimal and
 * dependency-free so new providers can be added without pulling in extra
 * packages unless they are genuinely needed.
 */
abstract class AbstractOAuth2Provider implements AuthProviderInterface
{
    /** @var string Provider name (e.g. 'google', 'facebook', 'oidc') */
    protected string $name;

    /** @var string Brand icon class for the login button */
    protected string $brandClass;

    /** @var string|null Client ID from the provider */
    protected ?string $clientId = null;

    /** @var string|null Client secret from the provider */
    protected ?string $clientSecret = null;

    /** @var string|null Redirect URI registered with the provider */
    protected ?string $redirectUri = null;

    /** @var string|null Authorization endpoint URL */
    protected ?string $authEndpoint = null;

    /** @var string|null Token endpoint URL */
    protected ?string $tokenEndpoint = null;

    /** @var string|null User info endpoint URL (OIDC) or profile API */
    protected ?string $userInfoEndpoint = null;

    /** @var array<string> Scopes to request */
    protected array $scopes = ['openid', 'email', 'profile'];

    /** @var bool Whether PKCE is required/used */
    protected bool $pkce = true;

    /** @var string|null Temporary state value set during login redirect */
    private ?string $pendingState = null;

    /** @var string|null Pending code verifier (PKCE) */
    private ?string $pendingCodeVerifier = null;

    public function __construct(string $name, string $brandClass = 'fa-sign-in-alt')
    {
        $this->name = $name;
        $this->brandClass = $brandClass;
    }

    // ── Configuration (called by concrete provider or DI container) ──────────

    public function setClientId(string $id): self
    {
        $this->clientId = $id;
        return $this;
    }

    public function setClientSecret(string $secret): self
    {
        $this->clientSecret = $secret;
        return $this;
    }

    public function setRedirectUri(string $uri): self
    {
        $this->redirectUri = $uri;
        return $this;
    }

    public function setAuthEndpoint(string $url): self
    {
        $this->authEndpoint = $url;
        return $this;
    }

    public function setTokenEndpoint(string $url): self
    {
        $this->tokenEndpoint = $url;
        return $this;
    }

    public function setUserInfoEndpoint(string $url): self
    {
        $this->userInfoEndpoint = $url;
        return $this;
    }

    public function setScopes(array $scopes): self
    {
        $this->scopes = $scopes;
        return $this;
    }

    public function setPkce(bool $pkce): self
    {
        $this->pkce = $pkce;
        return $this;
    }

    // ── AuthProviderInterface ─────────────────────────────────────────────────

    public function getName(): string
    {
        return $this->name;
    }

    public function getBrandClass(): string
    {
        return $this->brandClass;
    }

    public function isAvailable(): bool
    {
        return $this->clientId !== null
            && $this->clientSecret !== null
            && $this->redirectUri !== null
            && $this->authEndpoint !== null;
    }

    public function getLoginUrl(): ?string
    {
        if (!$this->isAvailable()) {
            return null;
        }

        $state = $this->generateState();
        $codeVerifier = $this->pkce ? $this->generateCodeVerifier() : null;

        // Store for callback verification.
        $_SESSION['auth_state_' . $this->name] = $state;
        if ($codeVerifier !== null) {
            $_SESSION['auth_pkce_' . $this->name] = $codeVerifier;
        }

        $params = [
            'client_id'     => $this->clientId,
            'redirect_uri'  => $this->redirectUri,
            'response_type' => 'code',
            'scope'         => implode(' ', $this->scopes),
            'state'         => $state,
        ];

        if ($this->pkce && $codeVerifier !== null) {
            $params['code_challenge'] = $this->pkceCodeChallenge($codeVerifier);
            $params['code_challenge_method'] = 'S256';
        }

        return $this->authEndpoint . '?' . http_build_query($params);
    }

    public function isRedirectBased(): bool
    {
        return true;
    }

    /**
     * Handle the OAuth callback: exchange code for token, fetch user info,
     * return normalized identity.
     */
    public function handleCallback(array $callbackData): array
    {
        if (!isset($callbackData['code'])) {
            throw new AuthProviderException('Missing authorization code in callback.');
        }

        $state = $callbackData['state'] ?? '';
        $sessionState = $_SESSION['auth_state_' . $this->name] ?? '';

        if (!hash_equals($sessionState, $state)) {
            throw new AuthProviderException('Invalid state parameter — possible CSRF.');
        }

        // Clear state immediately after use.
        unset($_SESSION['auth_state_' . $this->name]);

        $codeVerifier = null;
        if ($this->pkce) {
            $codeVerifier = $_SESSION['auth_pkce_' . $this->name] ?? null;
            unset($_SESSION['auth_pkce_' . $this->name]);
        }

        // Exchange authorization code for access token.
        $tokenResponse = $this->exchangeCodeForToken(
            $callbackData['code'],
            $this->redirectUri,
            $codeVerifier
        );

        if (!isset($tokenResponse['access_token'])) {
            throw new AuthProviderException('Token exchange failed: ' . ($tokenResponse['error'] ?? 'unknown'));
        }

        // Fetch user info.
        $identity = $this->fetchUserInfo(
            $tokenResponse['access_token'],
            $tokenResponse['id_token'] ?? null
        );

        if ($identity === null) {
            throw new AuthProviderException('Failed to fetch user info from provider.');
        }

        return $identity;
    }

    public function validateCredentials(array $credentials): ?array
    {
        throw new \LogicException('OAuth providers do not use direct credential validation.');
    }

    /**
     * Normalize a raw identity from the provider into our canonical shape.
     *
     * Concrete providers override this.
     */
    abstract public function normalizeUser(array $identity): array;

    // ── Internals (override in concrete providers as needed) ─────────────────

    /**
     * Build the authorization URL.  Override if provider uses non-standard params.
     */
    protected function buildAuthUrl(string $state, ?string $codeVerifier): string
    {
        return $this->getLoginUrl(); // already built — but some providers need custom params
    }

    /**
     * Exchange authorization code for tokens via POST to token endpoint.
     *
     * Default implementation is generic OAuth2.  Override for provider quirks
     * (e.g. Facebook uses GET for some endpoints, Google uses POST with specific fields).
     */
    protected function exchangeCodeForToken(string $code, string $redirectUri, ?string $codeVerifier): array
    {
        $payload = [
            'grant_type'    => 'authorization_code',
            'code'          => $code,
            'redirect_uri'  => $redirectUri,
            'client_id'     => $this->clientId,
            'client_secret' => $this->clientSecret,
        ];

        if ($codeVerifier !== null) {
            $payload['code_verifier'] = $codeVerifier;
        }

        $ch = curl_init($this->tokenEndpoint);
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => http_build_query($payload),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER     => ['Accept: application/json'],
            CURLOPT_TIMEOUT        => 15,
            CURLOPT_SSL_VERIFYPEER => true,
        ]);

        $response = curl_exec($ch);
        $errno = curl_errno($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($errno !== 0 || $httpCode < 200 || $httpCode >= 300) {
            return ['error' => 'Token endpoint request failed (curl error: ' . $errno . ', HTTP ' . $httpCode . ')'];
        }

        $data = json_decode($response, true);
        if (!is_array($data)) {
            return ['error' => 'Invalid JSON from token endpoint'];
        }

        return $data;
    }

    /**
     * Fetch user info from the provider.  Override per provider.
     */
    protected function fetchUserInfo(string $accessToken, ?string $idToken): ?array
    {
        if ($this->userInfoEndpoint === null) {
            // Fallback: decode ID token if available (OIDC).
            if ($idToken !== null) {
                return $this->decodeIdToken($idToken);
            }
            return null;
        }

        $ch = curl_init($this->userInfoEndpoint);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER     => [
                'Accept: application/json',
                'Authorization: Bearer ' . $accessToken,
            ],
            CURLOPT_TIMEOUT        => 15,
            CURLOPT_SSL_VERIFYPEER => true,
        ]);

        $response = curl_exec($ch);
        $errno = curl_errno($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($errno !== 0 || $httpCode < 200 || $httpCode >= 300) {
            return null;
        }

        $data = json_decode($response, true);
        return is_array($data) ? $data : null;
    }

    /**
     * Decode an OIDC ID token (JWT) without verifying signature.
     *
     * NOTE: In production you MUST verify the JWT signature against the
     * provider's JWKS endpoint.  This stub is for prototyping only.
     * For production use, add firebase/php-jwt or lcobucci/jwt as a dependency
     * and implement full verification.
     */
    protected function decodeIdToken(string $idToken): ?array
    {
        $parts = explode('.', $idToken);
        if (count($parts) !== 3) {
            return null;
        }

        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+/')), true);
        return is_array($payload) ? $payload : null;
    }

    // ── State / PKCE helpers ──────────────────────────────────────────────────

    private function generateState(): string
    {
        return bin2hex(random_bytes(32));
    }

    private function generateCodeVerifier(): string
    {
        return bin2hex(random_bytes(32));
    }

    private function pkceCodeChallenge(string $verifier): string
    {
        $hash = hash('sha256', $verifier, true);
        return rtrim(strtr(base64_encode($hash), '+/', '-_'), '=');
    }

    public function getConfigSummary(): array
    {
        return [
            'type'          => 'oauth2',
            'client_id'     => $this->clientId !== null ? substr($this->clientId, 0, 8) . '...' : 'not set',
            'redirect_uri'  => $this->redirectUri,
            'auth_endpoint' => $this->authEndpoint,
            'scopes'        => $this->scopes,
            'pkce'          => $this->pkce,
        ];
    }
}
