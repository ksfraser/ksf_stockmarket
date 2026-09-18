<?php
/**
 * AdminSettingsController - System-level configuration (webhooks, LLM settings).
 * Requires admin role - for settings that affect all users.
 */
class AdminSettingsController {

    private $currentUser;

    public function __construct() {
        $this->currentUser = AuthController::requireAuth();
        if (($this->currentUser['role'] ?? 'user') !== 'admin') {
            $_SESSION['flash_error'] = 'Admin access required.';
            header('Location: ?action=overview');
            exit;
        }
    }

    /**
     * GET /?action=admin_settings - Admin configuration page.
     */
    public function index(): array {
        $pdo = Database::get();
        $message = '';
        $error = '';

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $message = $this->saveSettings($pdo);
        }

        $settings = $this->getSettings($pdo);

        return [
            'pageTitle' => 'Admin Settings',
            'template' => 'admin_settings',
            'settings' => $settings,
            'message' => $message,
            'error' => $error,
            'user' => $this->currentUser,
        ];
    }

    /**
     * Save submitted settings to database.
     */
    private function saveSettings(PDO $pdo): string {
        $allowedKeys = [
            'discord_webhook_url' => 'text',
            'discord_alert_webhook' => 'text',
            'discord_bot_token' => 'password',
            'llm_provider' => 'string',
            'llm_model' => 'string',
            'llm_api_key' => 'password',
            'llm_base_url' => 'string',
            'llm_primary_url' => 'string',
            'llm_primary_model' => 'string',
            'llm_primary_token' => 'password',
            'llm_secondary_url' => 'string',
            'llm_secondary_model' => 'string',
            'llm_secondary_token' => 'password',
            'llm_fallback_url' => 'string',
            'llm_fallback_model' => 'string',
            'llm_fallback_token' => 'password',
            'ta_run_frequency' => 'string',
            'alert_check_frequency' => 'string',
            'max_symbols_per_run' => 'integer',
            'external_auth_reddit_client_id' => 'string',
            'external_auth_reddit_client_secret' => 'password',
            'external_auth_tradingview_api_key' => 'password',
            'external_auth_arxiv_api_key' => 'password',
            'youtube_api_key' => 'password',
            'apify_token' => 'password',
            'youtube_watch_channels' => 'text',
        ];

        foreach ($allowedKeys as $key => $type) {
            $val = $_POST[$key] ?? '';
            
            // Validate based on type
            if ($type === 'integer') {
                $val = (int)$val;
            }
            
            $stmt = $pdo->prepare("
                INSERT INTO system_settings (setting_key, setting_value)
                VALUES (:key, :val)
                ON DUPLICATE KEY UPDATE setting_value = :val2
            ");
            $stmt->execute([':key' => $key, ':val' => $val, ':val2' => $val]);
        }

        // Also write to .env file for PHP scripts
        $this->updateEnvFile($pdo);

        return 'Settings saved successfully.';
    }

    /**
     * Update .env file with current settings.
     */
    private function updateEnvFile(PDO $pdo): void {
        $settings = $this->getSettings($pdo);
        $envPath = '/root/.hermes/.env';
        
        if (!file_exists($envPath)) {
            return;
        }

        $envContent = file_get_contents($envPath);
        
        // Update DISCORD_ALERT_WEBHOOK
        if (isset($settings['discord_alert_webhook'])) {
            $pattern = '/^(DISCORD_ALERT_WEBHOOK=.*)$/m';
            $replacement = 'DISCORD_ALERT_WEBHOOK=' . $settings['discord_alert_webhook'];
            if (preg_match($pattern, $envContent)) {
                $envContent = preg_replace($pattern, $replacement, $envContent);
            } else {
                $envContent .= "\nDISCORD_ALERT_WEBHOOK=" . $settings['discord_alert_webhook'];
            }
        }

        file_put_contents($envPath, $envContent);
    }

    /**
     * Get all settings with defaults.
     */
    private function getSettings(PDO $pdo): array {
        $defaults = [
            'discord_webhook_url' => '',
            'discord_alert_webhook' => '',
            'discord_bot_token' => '',
            'llm_provider' => 'openrouter',
            'llm_model' => 'anthropic/claude-sonnet-4',
            'llm_api_key' => '',
            'llm_base_url' => '',
            'llm_primary_url' => '',
            'llm_primary_model' => '',
            'llm_primary_token' => '',
            'llm_secondary_url' => '',
            'llm_secondary_model' => '',
            'llm_secondary_token' => '',
            'llm_fallback_url' => '',
            'llm_fallback_model' => '',
            'llm_fallback_token' => '',
            'ta_run_frequency' => 'daily',
            'alert_check_frequency' => '15min',
            'max_symbols_per_run' => '100',
            'youtube_api_key' => '',
            'apify_token' => '',
            'youtube_watch_channels' => '',
        ];

        // First, seed from .env if available
        $envFile = '/root/.hermes/.env';
        if (file_exists($envFile)) {
            $envContent = file_get_contents($envFile);
            if (preg_match('/DISCORD_ALERT_WEBHOOK=(.+)/', $envContent, $m)) {
                $defaults['discord_alert_webhook'] = trim($m[1]);
            }
            if (preg_match('/DISCORD_BOT_TOKEN=(.+)/', $envContent, $m)) {
                $defaults['discord_bot_token'] = trim($m[1]);
            }
        }

        try {
            $stmt = $pdo->query("SELECT setting_key, setting_value FROM system_settings");
            while ($row = $stmt->fetch()) {
                $defaults[$row['setting_key']] = $row['setting_value'];
            }
        } catch (Exception $e) {}

        return $defaults;
    }

    /**
     * Get a single setting value (static helper for other controllers).
     */
    public static function getSetting(string $key): string {
        try {
            $pdo = Database::get();
            $stmt = $pdo->prepare("SELECT setting_value FROM system_settings WHERE setting_key = :key");
            $stmt->execute([':key' => $key]);
            $row = $stmt->fetch();
            return $row['setting_value'] ?? '';
        } catch (Exception $e) {
            return '';
        }
    }

    /**
     * Get advisor-LLM profile assignments as JSON (for AJAX loading).
     */
    public function getLlmProfiles(): void {
        header('Content-Type: application/json');
        try {
            $pdo = Database::get();
            $stmt = $pdo->query("SELECT advisor_id, llm_profile FROM advisor_llm_profiles");
            $profiles = [];
            while ($row = $stmt->fetch()) {
                $profiles[$row['advisor_id']] = $row['llm_profile'];
            }
            echo json_encode($profiles);
        } catch (Exception $e) {
            echo json_encode(['error' => $e->getMessage()]);
        }
        exit;
    }

    /**
     * Test LLM endpoint connectivity (for AJAX health check).
     */
    public function testLlmEndpoint(): void {
        header('Content-Type: application/json');
        $profile = $_GET['llm_test'] ?? 'primary';
        $keys = [
            'primary' => ['llm_primary_url', 'llm_primary_model', 'llm_primary_token'],
            'secondary' => ['llm_secondary_url', 'llm_secondary_model', 'llm_secondary_token'],
            'fallback' => ['llm_fallback_url', 'llm_fallback_model', 'llm_fallback_token'],
        ];
        if (!isset($keys[$profile])) {
            echo json_encode(['available' => false, 'error' => 'Invalid profile']);
            exit;
        }
        list($url_key, $model_key, $token_key) = $keys[$profile];
        $url = self::getSetting($url_key);
        $model = self::getSetting($model_key);
        $token = self::getSetting($token_key);

        if (!$url || !$model || !$token) {
            echo json_encode(['available' => false, 'error' => 'Not configured']);
            exit;
        }

        $start = microtime(true);
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => rtrim($url, '/') . '/chat/completions',
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 10,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode([
                'model' => $model,
                'messages' => [['role' => 'user', 'content' => 'Respond with exactly one word: OK']],
                'max_tokens' => 5,
            ]),
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'Authorization: Bearer ' . $token,
            ],
        ]);
        $resp = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err = curl_error($ch);
        curl_close($ch);
        $latency = round((microtime(true) - $start) * 1000);

        if ($http_code === 200 && $resp) {
            echo json_encode(['available' => true, 'latency_ms' => $latency]);
        } else {
            echo json_encode(['available' => false, 'latency_ms' => $latency, 'error' => $err ?: "HTTP $http_code"]);
        }
        exit;
    }

    /**
     * Handle advisor-LLM profile assignment (AJAX POST).
     */
    public function setLlmProfile(): void {
        header('Content-Type: application/json');
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            echo json_encode(['error' => 'Method not allowed']);
            exit;
        }
        $advisor_id = $_POST['advisor_id'] ?? '';
        $profile = $_POST['profile'] ?? 'primary';
        if (!in_array($profile, ['primary', 'secondary', 'fallback'])) {
            echo json_encode(['error' => 'Invalid profile']);
            exit;
        }
        try {
            $pdo = Database::get();
            $stmt = $pdo->prepare(
                "INSERT INTO advisor_llm_profiles (advisor_id, llm_profile) VALUES (:aid, :prof)
                 ON DUPLICATE KEY UPDATE llm_profile = :prof2"
            );
            $stmt->execute([':aid' => $advisor_id, ':prof' => $profile, ':prof2' => $profile]);
            echo json_encode(['success' => true, 'advisor_id' => $advisor_id, 'profile' => $profile]);
        } catch (Exception $e) {
            echo json_encode(['error' => $e->getMessage()]);
        }
        exit;
    }

    /**
     * GET /?action=refresh_all_prices — Admin-triggered full price sync.
     */
    public function refreshAllPrices(): void {
        $script = __DIR__ . '/../../../python/fetch_prices.py';
        if (!file_exists($script)) {
            $_SESSION['flash_error'] = 'Price fetcher not found.';
            header('Location: ?action=admin_settings');
            exit;
        }

        $fullHistory = isset($_GET['full_history']) && $_GET['full_history'] == '1';

        $cmd = [
            PHP_BINARY,
            $script,
        ];

        if ($fullHistory) {
            $cmd[] = '--full-history';
        } else {
            $cmd[] = '--days';
            $cmd[] = '1';
        }

        $workerUrl = rtrim((string) ($_ENV['PYTHON_WORKER_URL'] ?? ''), '/');
        if ($workerUrl !== '') {
            try {
                $ch = curl_init();
                curl_setopt_array($ch, [
                    CURLOPT_URL => $workerUrl . '/worker/refresh_prices',
                    CURLOPT_RETURNTRANSFER => true,
                    CURLOPT_POST => true,
                    CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
                    CURLOPT_TIMEOUT => 30,
                ]);
                $workerPayload = ['full_history' => $fullHistory ? 1 : 0];
                if (!$fullHistory) {
                    $workerPayload['days'] = 1;
                }
                curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($workerPayload));
                $raw = curl_exec($ch);
                $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
                $err = curl_error($ch);
                curl_close($ch);
                if ($err || $code < 200 || $code >= 300) {
                    throw new RuntimeException('Python worker request failed: ' . ($err ?: ('HTTP ' . $code)));
                }
                $_SESSION['flash_message'] = $fullHistory ? 'Full history refresh queued via worker. This may take a while.' : 'Recent price refresh queued via worker.';
            } catch (Exception $ce) {
                $_SESSION['flash_error'] = 'Worker refresh failed, falling back to local run: ' . $ce->getMessage();
                $this->_runLocal($cmd, dirname($script), $fullHistory);
            }
        } else {
            $this->_runLocal($cmd, dirname($script), $fullHistory);
        }

        header('Location: ' . ($_GET['redirect'] ?? '?action=admin_settings'));
        exit;
    }

    private function _runLocal(array $cmd, string $cwd, bool $fullHistory): void {
        try {
            $proc = proc_open(
                $cmd,
                [['pipe', 'r'], ['pipe', 'w'], ['pipe', 'w']],
                $pipes,
                $cwd,
                null,
                ['bypass_shell' => true]
            );
            if (is_resource($proc)) {
                fclose($pipes[0]);
                stream_set_blocking($pipes[1], false);
                stream_set_blocking($pipes[2], false);
                $stdout = stream_get_contents($pipes[1]);
                $stderr = stream_get_contents($pipes[2]);
                fclose($pipes[1]);
                fclose($pipes[2]);
                $rc = proc_close($proc);
                if ($rc === 0) {
                    $_SESSION['flash_message'] = $fullHistory ? 'Full history refresh queued. This may take a while.' : 'Recent price refresh queued.';
                } else {
                    throw new RuntimeException('Price refresh failed: ' . substr($stderr ?: $stdout, 0, 300));
                }
            } else {
                $_SESSION['flash_error'] = 'Could not start price refresh process.';
            }
        } catch (Exception $e) {
            $_SESSION['flash_error'] = 'Full price refresh failed: ' . $e->getMessage();
        }
    }
}