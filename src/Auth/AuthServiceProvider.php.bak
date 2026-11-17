<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth;

use Ksf\StockMarket\Auth\Provider\LocalAuthProvider;
use Ksf\StockMarket\Auth\Provider\GoogleProvider;
use Ksf\StockMarket\Auth\Provider\FacebookProvider;
use Ksf\StockMarket\Auth\Provider\GenericOIDCProvider;

/**
 * AuthServiceProvider — registers and configures auth providers.
 *
 * This is the extension point where new auth backends are wired in.
 * To add Kerberos, LDAP, GSSAPI, SAML, etc.:
 *   1. Create a class in src/Auth/Provider/ that implements AuthProviderInterface
 *      (or extends AbstractOAuth2Provider for OIDC-style).
 *   2. Add a register*() call here.
 *   3. Add env var documentation (see README section below).
 *
 * Future: this class can be replaced by a WP admin panel configuration screen
 * that stores provider settings in the DB and instantiates providers dynamically.
 * For now it reads from environment variables via getenv() (loaded by vlucas/phpdotenv
 * from .env in index.php).
 */
class AuthServiceProvider
{
    /**
     * Build and return a fully-configured AuthManager with all available providers.
     */
    public static function createManager(): AuthManager
    {
        $manager = new AuthManager();

        // ── Local username/password (always registered) ──────────────────────
        $manager->register(new LocalAuthProvider(), [
            'label' => 'Email & Password',
            'icon'  => 'fa-user',
        ]);

        // ── Google OAuth2 / OIDC ─────────────────────────────────────────────
        // Required env vars:
        //   GOOGLE_CLIENT_ID
        //   GOOGLE_CLIENT_SECRET
        //   GOOGLE_REDIRECT_URI  (e.g. https://owl.ksfraser.ca/?action=oauth-callback&provider=google)
        $google = new GoogleProvider();
        if ($google->isAvailable()) {
            $manager->register($google, [
                'label' => 'Google',
                'icon'  => 'fa-google',
                'help'  => 'Sign in with your Google account.',
            ]);
        }

        // ── Facebook OAuth2 ──────────────────────────────────────────────────
        // Required env vars:
        //   FB_CLIENT_ID
        //   FB_CLIENT_SECRET
        //   FB_REDIRECT_URI      (e.g. https://owl.ksfraser.ca/?action=oauth-callback&provider=facebook)
        $facebook = new FacebookProvider();
        if ($facebook->isAvailable()) {
            $manager->register($facebook, [
                'label' => 'Facebook',
                'icon'  => 'fa-facebook-f',
                'help'  => 'Sign in with your Facebook account.',
            ]);
        }

        // ── Generic OpenID Connect (Keycloak, Okta, Auth0, Azure AD, etc.) ──
        // Required env vars:
        //   OIDC_ISSUER          (e.g. https://id.example.com/realms/myrealm)
        //   OIDC_CLIENT_ID
        //   OIDC_CLIENT_SECRET
        //   OIDC_REDIRECT_URI
        // Optional:
        //   OIDC_DISCOVERY       (default 1 — set to 0 to disable .well-known discovery)
        //   OIDC_AUTH_ENDPOINT   (manual, if discovery is off)
        //   OIDC_TOKEN_ENDPOINT
        //   OIDC_USERINFO_ENDPOINT
        //   OIDC_SCOPES          (space-separated, default: openid email profile)
        $oidc = new GenericOIDCProvider();
        if ($oidc->isAvailable()) {
            $manager->register($oidc, [
                'label' => 'Single Sign-On',
                'icon'  => 'fa-openid',
                'help'  => 'Sign in with your organization\'s SSO.',
            ]);
        }

        return $manager;
    }

    /**
     * List of provider names that should appear as redirect buttons on the login page.
     *
     * @param AuthManager $manager
     * @return array<string, array{label: string, icon: string, help: string}>
     */
    public static function getRedirectProviderMeta(AuthManager $manager): array
    {
        $out = [];
        foreach ($manager->getRedirectProviders() as $name => $provider) {
            $config = $manager->getProviderConfig($name);
            $out[$name] = [
                'label' => $config['label'] ?? $provider->getName(),
                'icon'  => $config['icon']  ?? $provider->getBrandClass(),
                'help'  => $config['help']  ?? '',
            ];
        }
        return $out;
    }
}
