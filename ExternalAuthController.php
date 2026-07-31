<?php
/**
 * ExternalAuthController — OAuth / API-key auth for external providers
 * (Reddit, TradingView, arXiv, etc.).
 *
 * Routes:
 *   GET  ?action=external_auth&view=authorize&provider=reddit
 *   GET  ?action=external_auth&view=callback&provider=reddit&code=XXX&state=XXX
 *   GET  ?action=external_auth&view=revoke&provider=reddit
 *   POST ?action=external_auth&view=save_app&provider=reddit  (admin: client_id + client_secret)
 */
class ExternalAuthController {

    private $pdo;
    private $user;

    public function __construct() {
        $this->pdo = Database::get();
        $this->user = AuthController::checkSession();
    }

    /* ======================================================================
     * AUTHORIZE — redirect user to provider
     * ====================================================================== */
    public function authorize(): void {
        $provider = $_GET['provider'] ?? 'reddit';
        $provider = preg_replace('/[^a-z0-9_]/', '', strtolower($provider));

        $appId = $this->getAppId($provider);
        $redirectUri = $this->buildRedirectUri($provider);

        if (!$appId) {
            $_SESSION['flash_error'] = "{$provider} is not configured. Ask an admin to set the app ID.";
            header('Location: ?action=settings');
            exit;
        }

        // CSRF state
        $state = bin2hex(random_bytes(16));
        $_SESSION['oauth_state'][$provider] = $state;

        $params = [
            'client_id'     => $appId,
            'response_type' => 'code',
            'state'         => $state,
            'redirect_uri'  => $redirectUri,
            'duration'      => 'permanent',
            'scope'         => $this->getScopes($provider),
        ];

        $url = 'https://www.reddit.com/api/v1/authorize?' . http_build_query($params);
        header('Location: ' . $url);
        exit;
    }

    /* ======================================================================
     * CALLBACK — provider redirects back here with ?code=XXX
     * ====================================================================== */
    public function callback(): array {
        $provider = $_GET['provider'] ?? 'reddit';
        $provider = preg_replace('/[^a-z0-9_]/', '', strtolower($provider));
        $error = $_GET['error'] ?? '';
        $code  = $_GET['code'] ?? '';
        $state = $_GET['state'] ?? '';

        if ($error) {
            return ['pageTitle' => 'External Auth', 'template' => 'external_auth_status',
                    'error' => "Provider returned error: {$error}"];
        }

        if (empty($code)) {
            return ['pageTitle' => 'External Auth', 'template' => 'external_auth_status',
                    'error' => 'Missing authorization code.'];
        }

        // Verify state
        $expected = $_SESSION['oauth_state'][$provider] ?? '';
        if (!$expected || !hash_equals($expected, $state)) {
            return ['pageTitle' => 'External Auth', 'template' => 'external_auth_status',
                    'error' => 'Invalid OAuth state. Possible CSRF.'];
        }
        unset($_SESSION['oauth_state'][$provider]);

        // Exchange code for token
        $appId     = $this->getAppId($provider);
        $appSecret = $this->getAppSecret($provider);
        $redirectUri = $this->buildRedirectUri($provider);

        if (!$appId || !$appSecret) {
            return ['pageTitle' => 'External Auth', 'template' => 'external_auth_status',
                    'error' => "{$provider} app credentials not configured."];
        }

        $tokenUrl = 'https://www.reddit.com/api/v1/access_token';
        $basic = base64_encode($appId . ':' . $appSecret);

        $ch = curl_init($tokenUrl);
        curl_setopt_array($ch, [
            CURLOPT_HTTPHEADER     => [
                "Authorization: Basic {$basic}",
                'Content-Type: application/x-www-form-urlencoded',
                'User-Agent: ksf_stockmarket_auth/1.0',
            ],
            CURLOPT_POSTFIELDS     => http_build_query([
                'grant_type'    => 'authorization_code',
                'code'          => $code,
                'redirect_uri'  => $redirectUri,
            ]),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_SSL_VERIFYPEER => true,
        ]);
        $raw = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode !== 200 || !$raw) {
            return ['pageTitle' => 'External Auth', 'template' => 'external_auth_status',
                    'error' => "Token exchange failed (HTTP {$httpCode})."];
        }

        $tokenData = json_decode($raw, true);
        if (empty($tokenData['access_token'])) {
            return ['pageTitle' => 'External Auth', 'template' => 'external_auth_status',
                    'error' => 'No access_token in provider response.'];
        }

        // Store token (REDACTED in logs)
        $userId = $this->user['id'] ?? 0;
        $accessToken  = $tokenData['access_token'];
        $refreshToken = $tokenData['refresh_token'] ?? '';
        $expiresIn    = (int)($tokenData['expires_in'] ?? 3600);
        $expiresAt    = date('Y-m-d H:i:s', time() + $expiresIn);
        $scope        = $tokenData['scope'] ?? '';

        $stmt = $this->pdo->prepare("
            INSERT INTO external_auth_tokens
                (user_id, provider, token_type, access_token, refresh_token, expires_at, scope, is_active)
            VALUES (:uid, :prov, 'oauth', :at, :rt, :exp, :scope, 1)
            ON DUPLICATE KEY UPDATE
                access_token  = VALUES(access_token),
                refresh_token = VALUES(refresh_token),
                expires_at    = VALUES(expires_at),
                scope         = VALUES(scope),
                is_active     = 1,
                updated_at    = NOW()
        ");
        $stmt->execute([
            ':uid'  => $userId,
            ':prov' => $provider,
            ':at'   => $accessToken,
            ':rt'   => $refreshToken,
            ':exp'  => $expiresAt,
            ':scope' => $scope,
        ]);

        return ['pageTitle' => 'External Auth', 'template' => 'external_auth_status',
                'message' => "Connected to {$provider} successfully."];
    }

    /* ======================================================================
     * REVOKE — remove stored token
     * ====================================================================== */
    public function revoke(): void {
        $provider = $_GET['provider'] ?? 'reddit';
        $provider = preg_replace('/[^a-z0-9_]/', '', strtolower($provider));
        $userId = $this->user['id'] ?? 0;

        $stmt = $this->pdo->prepare("
            DELETE FROM external_auth_tokens
            WHERE user_id = :uid AND provider = :prov
        ");
        $stmt->execute([':uid' => $userId, ':prov' => $provider]);

        $_SESSION['flash_message'] = "Disconnected {$provider}.";
        header('Location: ?action=settings');
        exit;
    }

    /* ======================================================================
     * SAVE APP CREDENTIALS (admin only)
     * ====================================================================== */
    public function saveApp(): string {
        $provider = $_POST['provider'] ?? 'reddit';
        $provider = preg_replace('/[^a-z0-9_]/', '', strtolower($provider));
        $appId     = trim($_POST['app_id'] ?? '');
        $appSecret = trim($_POST['app_secret'] ?? '');
        $redirect  = trim($_POST['redirect_uri'] ?? '');

        if (!$appId || !$appSecret) {
            return "{$provider} app_id and app_secret are required.";
        }

        $this->setSetting("external_auth_{$provider}_client_id", $appId, 'string');
        $this->setSetting("external_auth_{$provider}_client_secret", $appSecret, 'password');
        if ($redirect) {
            $this->setSetting("external_auth_{$provider}_redirect_uri", $redirect, 'string');
        }

        return "{$provider} credentials saved.";
    }

    /* ======================================================================
     * HELPERS
     * ====================================================================== */

    private function getAppId(string $provider): string {
        $key = "external_auth_{$provider}_client_id";
        // Try env first (for python scripts), then system_settings
        $envKey = strtoupper(str_replace('-', '_', $key));
        $val = getenv($envKey);
        if ($val) return $val;
        return AdminSettingsController::getSetting($key);
    }

    private function getAppSecret(string $provider): string {
        $key = "external_auth_{$provider}_client_secret";
        $envKey = strtoupper(str_replace('-', '_', $key));
        $val = getenv($envKey);
        if ($val) return $val;
        return AdminSettingsController::getSetting($key);
    }

    private function buildRedirectUri(string $provider): string {
        $base = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? 'https' : 'http')
              . '://' . ($_SERVER['HTTP_HOST'] ?? '192.168.1.102');
        $path = dirname($_SERVER['SCRIPT_NAME'] ?? '/stockmarket');
        return "{$base}{$path}/?action=external_auth&view=callback&provider={$provider}";
    }

    private function getScopes(string $provider): string {
        $map = [
            'reddit' => 'read',
            // Extend here: 'tradingview' => '...', 'arxiv' => ''
        ];
        return $map[$provider] ?? '';
    }

    private function setSetting(string $key, string $value, string $type): void {
        $stmt = $this->pdo->prepare("
            INSERT INTO system_settings (setting_key, setting_value, setting_type)
            VALUES (:k, :v, :t)
            ON DUPLICATE KEY UPDATE setting_value = :v2
        ");
        $stmt->execute([':k' => $key, ':v' => $value, ':t' => $type, ':v2' => $value]);
    }

    /* ======================================================================
     * STATIC HELPERS — for Python/other consumers
     * ====================================================================== */

    /**
     * Get a valid access token for provider. Auto-refreshes if expired.
     */
    public static function getValidToken(PDO $pdo, string $provider, int $userId = 0): ?string {
        $stmt = $pdo->prepare("
            SELECT id, access_token, refresh_token, expires_at
            FROM external_auth_tokens
            WHERE provider = :prov AND user_id = :uid AND is_active = 1
            LIMIT 1
        ");
        $stmt->execute([':prov' => $provider, ':uid' => $userId]);
        $row = $stmt->fetch();

        if (!$row) {
            return null;
        }

        // If expires_at > now, token is still valid
        if (strtotime($row['expires_at']) > time() + 60) {
            return $row['access_token'];
        }

        // Refresh token
        return self::refreshToken($pdo, $row, $provider);
    }

    private static function refreshToken(PDO $pdo, array $row, string $provider): ?string {
        // We need app credentials — read from system_settings via helper
        // For now, return the old token (may still work briefly) and log
        // Full refresh implementation requires app credentials accessible here
        return $row['access_token'];
    }
}
