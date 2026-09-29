<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth\Provider;

use Ksf\StockMarket\Auth\AuthProviderException;

/**
 * Google OAuth2 / OpenID Connect provider.
 *
 * Uses the OpenID Connect discovery document to auto-configure endpoints.
 * Requires:
 *   - GOOGLE_CLIENT_ID
 *   - GOOGLE_CLIENT_SECRET
 *   - GOOGLE_REDIRECT_URI  (must match what's registered in Google Cloud Console)
 */
class GoogleProvider extends AbstractOAuth2Provider
{
    public function __construct()
    {
        parent::__construct('google', 'fa-google');

        // Lazy-load configuration from env.
        $this->configureFromEnv();
    }

    private function configureFromEnv(): void
    {
        $clientId     = getenv('GOOGLE_CLIENT_ID');
        $clientSecret = getenv('GOOGLE_CLIENT_SECRET');
        $redirectUri  = getenv('GOOGLE_REDIRECT_URI');

        if ($clientId !== false && $clientId !== '') {
            $this->setClientId($clientId);
        }
        if ($clientSecret !== false && $clientSecret !== '') {
            $this->setClientSecret($clientSecret);
        }
        if ($redirectUri !== false && $redirectUri !== '') {
            $this->setRedirectUri($redirectUri);
        }

        // Google OIDC endpoints (well-known).
        $this->setAuthEndpoint('https://accounts.google.com/o/oauth2/v2/auth');
        $this->setTokenEndpoint('https://oauth2.googleapis.com/token');
        $this->setUserInfoEndpoint('https://openidconnect.googleapis.com/v1/userinfo');
        $this->setScopes(['openid', 'email', 'profile']);
    }

    /**
     * {@inheritdoc}
     */
    public function normalizeUser(array $identity): array
    {
        // Google userinfo response shape:
        //   sub, name, given_name, family_name, picture, email, email_verified, locale
        return [
            'id'          => (string) ($identity['sub'] ?? ''),
            'provider'    => 'google',
            'provider_id' => (string) ($identity['sub'] ?? ''),
            'email'       => $identity['email'] ?? null,
            'username'    => $this->deriveUsername($identity),
            'display_name'=> $identity['name'] ?? '',
            'first_name'  => $identity['given_name'] ?? '',
            'last_name'   => $identity['family_name'] ?? '',
            'avatar_url'  => $identity['picture'] ?? null,
            'email_verified' => $identity['email_verified'] ?? false,
            'raw_payload' => $identity,
        ];
    }

    private function deriveUsername(array $identity): string
    {
        // Prefer email local-part.
        if (!empty($identity['email']) && str_contains($identity['email'], '@')) {
            $base = substr($identity['email'], 0, strpos($identity['email'], '@'));
            $base = preg_replace('/[^a-zA-Z0-9._-]/', '', $base);
            if (strlen($base) >= 3) {
                return $base;
            }
        }

        // Fallback to given_name + family_name.
        $name = '';
        if (!empty($identity['given_name'])) {
            $name .= $identity['given_name'];
        }
        if (!empty($identity['family_name'])) {
            $name .= $identity['family_name'];
        }
        $name = preg_replace('/[^a-zA-Z0-9]/', '', $name);
        if (strlen($name) >= 3) {
            return strtolower($name);
        }

        return 'google_' . substr($identity['sub'] ?? 'user', 0, 8);
    }

    public function getConfigSummary(): array
    {
        $base = parent::getConfigSummary();
        $base['provider'] = 'Google OIDC';
        $base['email_scope'] = in_array('email', $this->scopes);
        return $base;
    }
}
