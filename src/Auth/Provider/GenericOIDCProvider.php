<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth\Provider;

use Ksf\StockMarket\Auth\AuthProviderException;

/**
 * Generic OpenID Connect provider.
 *
 * Suitable for Keycloak, Okta, Auth0, Azure AD, or any OIDC-compliant provider.
 * Auto-discovers provider configuration from the .well-known/openid-configuration
 * endpoint if available.
 *
 * Requires:
 *   - OIDC_ISSUER        (e.g. https://keycloak.example.com/realms/myrealm)
 *   - OIDC_CLIENT_ID
 *   - OIDC_CLIENT_SECRET
 *   - OIDC_REDIRECT_URI
 *
 * Optional:
 *   - OIDC_DISCOVERY     (set to "0" to disable auto-discovery and use manual endpoints)
 *   - OIDC_AUTH_ENDPOINT
 *   - OIDC_TOKEN_ENDPOINT
 *   - OIDC_USERINFO_ENDPOINT
 *   - OIDC_SCOPES
 */
class GenericOIDCProvider extends AbstractOAuth2Provider
{
    /** @var string|null Issuer URL — used for discovery */
    private ?string $issuer = null;

    /** @var bool Whether discovery has been run */
    private bool $discovered = false;

    public function __construct()
    {
        parent::__construct('oidc', 'fa-openid');

        $this->configureFromEnv();
    }

    private function configureFromEnv(): void
    {
        $issuer = getenv('OIDC_ISSUER');

        if ($issuer !== false && $issuer !== '') {
            $this->issuer = rtrim($issuer, '/');
            $this->setClientId(getenv('OIDC_CLIENT_ID') ?? '');
            $this->setClientSecret(getenv('OIDC_CLIENT_SECRET') ?? '');
            $this->setRedirectUri(getenv('OIDC_REDIRECT_URI') ?? '');

            // Auto-discovery unless disabled.
            $disableDiscovery = (getenv('OIDC_DISCOVERY') ?? '1') === '0';
            if (!$disableDiscovery) {
                $this->runDiscovery();
            } else {
                // Manual endpoint config.
                $auth = getenv('OIDC_AUTH_ENDPOINT');
                $token = getenv('OIDC_TOKEN_ENDPOINT');
                $userinfo = getenv('OIDC_USERINFO_ENDPOINT');
                if ($auth !== false && $auth !== '') $this->setAuthEndpoint($auth);
                if ($token !== false && $token !== '') $this->setTokenEndpoint($token);
                if ($userinfo !== false && $userinfo !== '') $this->setUserInfoEndpoint($userinfo);

                $scopes = getenv('OIDC_SCOPES');
                if ($scopes !== false && $scopes !== '') {
                    $this->setScopes(explode(' ', $scopes));
                }
            }
        }
    }

    /**
     * Run OIDC discovery from the issuer's .well-known endpoint.
     */
    private function runDiscovery(): void
    {
        if ($this->issuer === null) {
            return;
        }

        $discoveryUrl = $this->issuer . '/.well-known/openid-configuration';

        $ch = curl_init($discoveryUrl);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 10,
            CURLOPT_SSL_VERIFYPEER => true,
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $errno = curl_errno($ch);
        curl_close($ch);

        if ($errno !== 0 || $httpCode < 200 || $httpCode >= 300) {
            // Discovery failed — not a fatal error; caller should check isAvailable().
            return;
        }

        $config = json_decode($response, true);
        if (!is_array($config)) {
            return;
        }

        // Map OIDC discovery fields to our endpoint setters.
        $mappings = [
            'authorization_endpoint' => 'setAuthEndpoint',
            'token_endpoint'         => 'setTokenEndpoint',
            'userinfo_endpoint'      => 'setUserInfoEndpoint',
            'jwks_uri'              => 'setJwksUri',    // not implemented yet
            'issuer'                => 'setIssuer',      // not a setter but we track it
        ];

        foreach ($mappings as $key => $method) {
            if (isset($config[$key]) && is_string($config[$key])) {
                $this->$method($config[$key]);
            }
        }

        // Scopes from discovery if present.
        if (isset($config['scopes_supported']) && is_array($config['scopes_supported'])) {
            // Intersection with our default scopes — only request what the provider supports.
            $supported = array_map('strtolower', $config['scopes_supported']);
            $requested = array_map('strtolower', $this->scopes);
            $common = array_intersect($requested, $supported);
            if (!empty($common)) {
                // Re-map back to original casing from our defaults.
                $cased = [];
                foreach ($this->scopes as $s) {
                    if (in_array(strtolower($s), $common)) {
                        $cased[] = $s;
                    }
                }
                if (!empty($cased)) {
                    $this->setScopes($cased);
                }
            }
        }

        $this->discovered = true;
    }

    public function isAvailable(): bool
    {
        if ($this->discovered) {
            return parent::isAvailable();
        }

        // If discovery hasn't run, fall back to basic config check.
        return parent::isAvailable();
    }

    /**
     * {@inheritdoc}
     */
    public function normalizeUser(array $identity): array
    {
        // OIDC standard claims: sub, name, given_name, family_name, email, picture
        return [
            'id'          => (string) ($identity['sub'] ?? ''),
            'provider'    => 'oidc',
            'provider_id' => (string) ($identity['sub'] ?? ''),
            'email'       => $identity['email'] ?? null,
            'username'    => $this->deriveUsername($identity),
            'display_name'=> $identity['name'] ?? '',
            'first_name'  => $identity['given_name'] ?? '',
            'last_name'   => $identity['family_name'] ?? '',
            'avatar_url'  => $identity['picture'] ?? null,
            'raw_payload' => $identity,
        ];
    }

    private function deriveUsername(array $identity): string
    {
        if (!empty($identity['email']) && str_contains($identity['email'], '@')) {
            $base = substr($identity['email'], 0, strpos($identity['email'], '@'));
            $base = preg_replace('/[^a-zA-Z0-9._-]/', '', $base);
            if (strlen($base) >= 3) {
                return $base;
            }
        }

        $name = '';
        if (!empty($identity['given_name'])) $name .= $identity['given_name'];
        if (!empty($identity['family_name'])) $name .= $identity['family_name'];
        $name = preg_replace('/[^a-zA-Z0-9]/', '', $name);
        if (strlen($name) >= 3) {
            return strtolower($name);
        }

        return 'oidc_' . substr($identity['sub'] ?? 'user', 0, 8);
    }

    /**
     * Expose the issuer for debugging.
     */
    public function getIssuer(): ?string
    {
        return $this->issuer;
    }

    /**
     * Expose whether discovery succeeded.
     */
    public function isDiscovered(): bool
    {
        return $this->discovered;
    }

    public function getConfigSummary(): array
    {
        $base = parent::getConfigSummary();
        $base['provider']   = 'Generic OIDC';
        $base['issuer']     = $this->issuer;
        $base['discovered'] = $this->discovered;
        return $base;
    }
}
