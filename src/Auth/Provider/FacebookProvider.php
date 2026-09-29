<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth\Provider;

use Ksf\StockMarket\Auth\AuthProviderException;

/**
 * Facebook OAuth2 provider.
 *
 * Requires:
 *   - FB_CLIENT_ID  (Facebook App ID)
 *   - FB_CLIENT_SECRET  (Facebook App Secret)
 *   - FB_REDIRECT_URI  (must match what's registered in Facebook Developer Console)
 *
 * Facebook's OAuth2 flow is slightly different from pure OIDC:
 *   - Graph API endpoint for user info: https://graph.facebook.com/v18.0/me?fields=...
 *   - Token endpoint: https://graph.facebook.com/v18.0/oauth/access_token
 */
class FacebookProvider extends AbstractOAuth2Provider
{
    public function __construct()
    {
        parent::__construct('facebook', 'fa-facebook-f');

        $this->configureFromEnv();
    }

    private function configureFromEnv(): void
    {
        $clientId     = getenv('FB_CLIENT_ID');
        $clientSecret = getenv('FB_CLIENT_SECRET');
        $redirectUri  = getenv('FB_REDIRECT_URI');

        if ($clientId !== false && $clientId !== '') {
            $this->setClientId($clientId);
        }
        if ($clientSecret !== false && $clientSecret !== '') {
            $this->setClientSecret($clientSecret);
        }
        if ($redirectUri !== false && $redirectUri !== '') {
            $this->setRedirectUri($redirectUri);
        }

        // Facebook Graph API v18.0 endpoints.
        $version = 'v18.0';
        $this->setAuthEndpoint("https://www.facebook.com/$version/dialog/oauth");
        $this->setTokenEndpoint("https://graph.facebook.com/$version/oauth/access_token");
        $this->setUserInfoEndpoint("https://graph.facebook.com/$version/me");
        $this->setScopes(['email', 'public_profile']);
    }

    /**
     * {@inheritdoc}
     */
    public function normalizeUser(array $identity): array
    {
        // Facebook Graph API /me response:
        //   id, name, first_name, last_name, picture (object with data.url), email
        return [
            'id'          => (string) ($identity['id'] ?? ''),
            'provider'    => 'facebook',
            'provider_id' => (string) ($identity['id'] ?? ''),
            'email'       => $identity['email'] ?? null,
            'username'    => $this->deriveUsername($identity),
            'display_name'=> $identity['name'] ?? '',
            'first_name'  => $identity['first_name'] ?? '',
            'last_name'   => $identity['last_name'] ?? '',
            'avatar_url'  => $this->extractAvatar($identity),
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
        if (!empty($identity['first_name'])) $name .= $identity['first_name'];
        if (!empty($identity['last_name'])) $name .= $identity['last_name'];
        $name = preg_replace('/[^a-zA-Z0-9]/', '', $name);
        if (strlen($name) >= 3) {
            return strtolower($name);
        }

        return 'fb_' . substr($identity['id'] ?? 'user', 0, 8);
    }

    private function extractAvatar(array $identity): ?string
    {
        if (isset($identity['picture']['data']['url'])) {
            return $identity['picture']['data']['url'];
        }
        if (isset($identity['picture']['url'])) {
            return $identity['picture']['url'];
        }
        return null;
    }

    /**
     * Facebook requires the fields parameter on the user info request.
     * Override fetchUserInfo to include it.
     */
    protected function fetchUserInfo(string $accessToken, ?string $idToken): ?array
    {
        // We need to request specific fields — override the base one-shot GET.
        $fields = 'id,name,first_name,last_name,email,picture.type(large)';
        $url = $this->userInfoEndpoint . '?fields=' . urlencode($fields) . '&access_token=' . urlencode($accessToken);

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
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

    public function getConfigSummary(): array
    {
        $base = parent::getConfigSummary();
        $base['provider'] = 'Facebook Graph API';
        return $base;
    }
}
