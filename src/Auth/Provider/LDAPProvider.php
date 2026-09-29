<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth\Provider;

use Ksf\StockMarket\Auth\AuthProviderInterface;
use Ksf\StockMarket\Auth\AuthProviderException;

/**
 * LDAP / Kerberos / GSSAPI authentication provider.
 *
 * Supports:
 *  - LDAP simple bind (uid=%s, dn pattern, or search-based)
 *  - Kerberos GSSAPI (SPNEGO) via PHP's ldap_sasl_bind
 *  - Active Directory (SASL or simple bind with domain\username)
 *
 * Configuration (env vars):
 *   LDAP_HOST             - LDAP server hostname (e.g. ldap.example.com)
 *   LDAP_PORT             - Default 389, or 636 for LDAPS
 *   LDAP_USE_SSL          - "1" for LDAPS, "0" for plain (default 0)
 *   LDAP_SASL             - "1" for SASL/GSSAPI, "0" for simple bind (default 0)
 *   LDAP_BASE_DN          - Search base (e.g. dc=example,dc=com)
 *   LDAP_BIND_DN          - Service account DN for search (or empty for anonymous)
 *   LDAP_BIND_PASSWORD    - Service account password
 *   LDAP_SEARCH_FILTER    - User search filter (default: (uid=%s))
 *   LDAP_SEARCH_SCOPE     - sub, one, or base (default: sub)
 *   LDAP_USERNAME_ATTR    - Attribute to map to our username (default: uid)
 *   LDAP_EMAIL_ATTR       - Attribute for email (default: mail)
 *   LDAP_DISPLAY_NAME_ATTR- Attribute for display name (default: cn)
 *   LDAP_SASL_REALM       - SASL realm (for Kerberos)
 *   LDAP_SASL_AUTHZID     - SASL authorization ID
 *
 * Usage in login form:
 *   The login template renders a "LDAP/Kerberos" button that POSTs to
 *   ?action=login with provider=ldap and credentials {ldap_username, ldap_password}.
 *   The provider validates against the LDAP server and returns a normalized user
 *   record.  If the user doesn't exist locally, a local account is auto-created
 *   (same upsert logic as OAuth providers).
 *
 * Future extensions:
 *   - Add GSSAPI/Kerberos ticket cache support (KRB5CCNAME)
 *   - Add SPNEGO negotiation for browser-based Kerberos (negotiate auth)
 *   - Add LDAP group membership mapping for role assignment
 */
class LDAPProvider implements AuthProviderInterface
{
    private string $host = '';
    private int $port = 389;
    private bool $useSsl = false;
    private bool $sasl = false;
    private string $baseDn = '';
    private string $bindDn = '';
    private string $bindPassword = '';
    private string $searchFilter = '(uid=%s)';
    private string $searchScope = 'sub';
    private string $usernameAttr = 'uid';
    private string $emailAttr = 'mail';
    private string $displayNameAttr = 'cn';
    private string $saslRealm = '';
    private string $saslAuthzId = '';

    public function __construct()
    {
        $this->loadFromEnv();
    }

    private function loadFromEnv(): void
    {
        $this->host     = getenv('LDAP_HOST')     ?: '';
        $this->port     = (int) (getenv('LDAP_PORT') ?: 389);
        $this->useSsl   = (getenv('LDAP_USE_SSL') ?: '0') === '1';
        $this->sasl     = (getenv('LDAP_SASL') ?: '0') === '1';
        $this->baseDn   = getenv('LDAP_BASE_DN')   ?: '';
        $this->bindDn   = getenv('LDAP_BIND_DN')   ?: '';
        $this->bindPassword = getenv('LDAP_BIND_PASSWORD') ?: '';
        $this->searchFilter  = getenv('LDAP_SEARCH_FILTER')  ?: '(uid=%s)';
        $this->searchScope   = getenv('LDAP_SEARCH_SCOPE')   ?: 'sub';
        $this->usernameAttr  = getenv('LDAP_USERNAME_ATTR')  ?: 'uid';
        $this->emailAttr     = getenv('LDAP_EMAIL_ATTR')     ?: 'mail';
        $this->displayNameAttr = getenv('LDAP_DISPLAY_NAME_ATTR') ?: 'cn';
        $this->saslRealm     = getenv('LDAP_SASL_REALM')     ?: '';
        $this->saslAuthzId  = getenv('LDAP_SASL_AUTHZID')    ?: '';
    }

    // ── AuthProviderInterface ────────────────────────────────────────────────

    public function getName(): string
    {
        return 'ldap';
    }

    public function getBrandClass(): string
    {
        return 'fa-shield-halved';
    }

    public function isAvailable(): bool
    {
        if ($this->host === '') {
            return false;
        }

        if (!extension_loaded('ldap')) {
            return false;
        }

        return true;
    }

    public function getLoginUrl(): ?string
    {
        return null; // Form-based, not redirect.
    }

    public function isRedirectBased(): bool
    {
        return false;
    }

    /**
     * Validate LDAP credentials.
     *
     * Flow:
     *   1. Connect to LDAP server
     *   2. Search for the user by filter
     *   3. Attempt bind as the user (simple bind or SASL)
     *   4. If successful, fetch user attributes
     *   5. Normalize and return
     */
    public function validateCredentials(array $credentials): ?array
    {
        $username = $credentials['ldap_username'] ?? '';
        $password = $credentials['ldap_password'] ?? '';

        if ($username === '' || $password === '') {
            return null;
        }

        $conn = $this->connect();
        if ($conn === null) {
            throw new AuthProviderException('Could not connect to LDAP server.');
        }

        // Search for the user's DN.
        $userDn = $this->searchUserDn($conn, $username);
        if ($userDn === null) {
            ldap_unbind($conn);
            return null;
        }

        // Attempt to bind as the user.
        $bound = $this->bindAsUser($conn, $userDn, $password);
        if (!$bound) {
            ldap_unbind($conn);
            return null;
        }

        // Fetch attributes.
        $attributes = $this->fetchAttributes($conn, $userDn);
        ldap_unbind($conn);

        if ($attributes === null) {
            return null;
        }

        return $this->normalizeUser(array_merge($attributes, [
            'dn' => $userDn,
            'username' => $username,
        ]));
    }

    public function handleCallback(array $callbackData): array
    {
        throw new \LogicException('LDAPProvider does not use OAuth callbacks.');
    }

    /**
     * Normalize LDAP attributes into our canonical user shape.
     */
    public function normalizeUser(array $identity): array
    {
        return [
            'id'          => (string) ($identity['dn'] ?? ''),
            'provider'    => 'ldap',
            'provider_id' => (string) ($identity['dn'] ?? ''),
            'email'       => $identity[$this->emailAttr] ?? null,
            'username'    => $identity[$this->usernameAttr] ?? $identity['username'] ?? '',
            'display_name'=> $identity[$this->displayNameAttr] ?? '',
            'first_name'  => $identity['givenName'] ?? '',
            'last_name'   => $identity['sn'] ?? '',
            'avatar_url'  => null,
            'raw_payload' => $identity,
        ];
    }

    public function getConfigSummary(): array
    {
        return [
            'type'        => $this->sasl ? 'LDAP+SASL(Kerberos/GSSAPI)' : 'LDAP Simple Bind',
            'host'        => $this->host,
            'port'        => $this->port,
            'use_ssl'     => $this->useSsl,
            'sasl'        => $this->sasl,
            'base_dn'     => $this->baseDn,
            'search_filter' => $this->searchFilter,
            'ldap_ext'    => extension_loaded('ldap'),
        ];
    }

    // ── Internal LDAP operations ─────────────────────────────────────────────

    /**
     * Connect to the LDAP server.
     */
    private function connect(): ?\LDAP\Connection
    {
        $protocol = $this->useSsl ? 'ldaps://' : 'ldap://';
        $url = $protocol . $this->host . ':' . $this->port;

        $conn = ldap_connect($url);
        if ($conn === false) {
            return null;
        }

        ldap_set_option($conn, LDAP_OPT_PROTOCOL_VERSION, 3);
        ldap_set_option($conn, LDAP_OPT_REFERRALS, 0);

        if ($this->useSsl) {
            if (getenv('LDAP_SSL_NO_VERIFY') !== '1') {
                ldap_set_option($conn, LDAP_OPT_X_TLS_REQUIRE_CERT, LDAP_OPT_X_TLS_HARD);
            } else {
                ldap_set_option($conn, LDAP_OPT_X_TLS_REQUIRE_CERT, LDAP_OPT_X_TLS_NEVER);
            }
            ldap_start_tls($conn);
        }

        return $conn;
    }

    /**
     * Search for the user's DN by username.
     */
    private function searchUserDn(\LDAP\Connection $conn, string $username): ?string
    {
        $filter = sprintf($this->searchFilter, ldap_escape($username, '', LDAP_ESCAPE_FILTER));

        $base = $this->baseDn;
        $attrs = [$this->usernameAttr, $this->emailAttr, $this->displayNameAttr, 'dn', 'givenName', 'sn'];

        $bindRequired = $this->bindDn !== '' && $this->bindPassword !== '';

        if ($bindRequired) {
            $bound = @ldap_bind($conn, $this->bindDn, $this->bindPassword);
            if (!$bound) {
                return null;
            }
        }

        $result = @ldap_search($conn, $base, $filter, $attrs, 0, 1);
        if ($result === false) {
            return null;
        }

        $entries = ldap_get_entries($conn, $result);
        ldap_free_result($result);

        if ($entries['count'] === 0) {
            return null;
        }

        return $entries[0]['dn'] ?? null;
    }

    /**
     * Bind as the user (simple bind or SASL).
     */
    private function bindAsUser(\LDAP\Connection $conn, string $userDn, string $password): bool
    {
        if ($this->sasl) {
            return $this->saslBind($conn, $userDn, $password);
        }

        $result = @ldap_bind($conn, $userDn, $password);
        return $result !== false;
    }

    /**
     * SASL bind (Kerberos GSSAPI).
     */
    private function saslBind(\LDAP\Connection $conn, string $userDn, string $password): bool
    {
        $saslMech = 'GSSAPI';

        $result = @ldap_sasl_bind($conn, $userDn, $password, $saslMech, $this->saslRealm, $this->saslAuthzId);

        if ($result === false && function_exists('ldap_sasl_bind')) {
            $result = @ldap_sasl_bind($conn, null, $password, $saslMech, $this->saslRealm);
        }

        return $result !== false;
    }

    /**
     * Fetch user attributes after successful bind.
     */
    private function fetchAttributes(\LDAP\Connection $conn, string $userDn): ?array
    {
        $attrs = [
            $this->usernameAttr,
            $this->emailAttr,
            $this->displayNameAttr,
            'givenName',
            'sn',
            'dn',
        ];

        $result = @ldap_read($conn, $userDn, '(objectClass=*)', $attrs);
        if ($result === false) {
            return null;
        }

        $entries = ldap_get_entries($conn, $result);
        ldap_free_result($result);

        if ($entries['count'] === 0) {
            return null;
        }

        $entry = $entries[0];
        $out = [];

        foreach ($attrs as $attr) {
            if (isset($entry[$attr]) && is_array($entry[$attr]) && $entry[$attr]['count'] > 0) {
                $out[$attr] = $entry[$attr][0];
            } elseif (isset($entry[$attr]) && is_string($entry[$attr])) {
                $out[$attr] = $entry[$attr];
            }
        }

        return $out;
    }
}
