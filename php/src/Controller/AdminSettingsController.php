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
            'ta_run_frequency' => 'string',
            'alert_check_frequency' => 'string',
            'max_symbols_per_run' => 'integer',
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
            'ta_run_frequency' => 'daily',
            'alert_check_frequency' => '15min',
            'max_symbols_per_run' => '100',
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
}