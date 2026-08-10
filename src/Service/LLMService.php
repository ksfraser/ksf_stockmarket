<?php
/**
 * LLMService - Centralized LLM API calls with rate limit handling.
 *
 * Provides single point of truth for all LLM interactions.
 * Uses admin-configured settings from system_settings table or .env fallback.
 */

declare(strict_types=1);

class LLMService
{
    private static ?LLMService $instance = null;
    private string $provider = 'openrouter';
    private string $model = 'gpt-4o-mini';
    private string $apiKey = '';
    private string $baseUrl = 'https://api.openai.com/v1';

    private function __construct()
    {
        // Load from system_settings or environment
        $this->loadSettings();
    }

    public static function getInstance(): LLMService
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    /**
     * Load LLM settings from database or .env file.
     */
    private function loadSettings(): void
    {
        try {
            $pdo = Database::get();
            $stmt = $pdo->prepare(
                "SELECT setting_key, setting_value FROM system_settings 
                 WHERE setting_key IN ('llm_provider', 'llm_model', 'llm_api_key', 'llm_base_url')"
            );
            $stmt->execute();
            $settings = $stmt->fetchAll();

            foreach ($settings as $row) {
                $key = $row['setting_key'];
                $val = $row['setting_value'];
                match ($key) {
                    'llm_provider' => $this->provider = $val ?: 'openrouter',
                    'llm_model' => $this->model = $val ?: 'gpt-4o-mini',
                    'llm_api_key' => $this->apiKey = $val,
                    'llm_base_url' => $this->baseUrl = $val ?: 'https://api.openai.com/v1',
                    default => null,
                };
            }
        } catch (Exception $e) {
            // Fall back to environment
            $this->provider = $_ENV['LLM_PROVIDER'] ?? 'openrouter';
            $this->model = $_ENV['LLM_MODEL'] ?? 'gpt-4o-mini';
            $this->apiKey = $_ENV['OPENAI_API_KEY'] ?? $_ENV['OPENROUTER_API_KEY'] ?? '';
            $this->baseUrl = $_ENV['LLM_BASE_URL'] ?? '';
        }
    }

    /**
     * Check if LLM is available (has API key).
     */
    public function isAvailable(): bool
    {
        return !empty($this->apiKey);
    }

    /**
     * Generate a completion - minimal overhead for simple responses.
     */
    public function complete(string $prompt, string $systemPrompt = '', int $maxTokens = 300): ?string
    {
        if (!$this->isAvailable()) {
            return null;
        }

        $this->loadSettings(); // Refresh in case admin changed settings

        try {
            $payload = [
                'model' => $this->model,
                'messages' => [
                    ['role' => 'system', 'content' => $systemPrompt ?: 'You are a helpful assistant.'],
                    ['role' => 'user', 'content' => $prompt],
                ],
                'temperature' => 0.2,
                'max_tokens' => $maxTokens,
            ];

            $ch = curl_init();
            curl_setopt_array($ch, [
                CURLOPT_URL => $this->baseUrl . '/chat/completions',
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => json_encode($payload),
                CURLOPT_HTTPHEADER => [
                    'Content-Type: application/json',
                    'Authorization: Bearer ' . $this->apiKey,
                ],
                CURLOPT_TIMEOUT => 30,
            ]);

            $response = curl_exec($ch);
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $error = curl_error($ch);
            curl_close($ch);

            if ($httpCode === 429) {
                error_log("LLM rate limit hit - falling back to template");
                return null; // Signal to use template instead
            }

            if ($response === false) {
                error_log("LLM curl error: " . $error);
                return null;
            }

            $data = json_decode($response, true);
            return $data['choices'][0]['message']['content'] ?? null;

        } catch (Exception $e) {
            error_log("LLM call failed: " . $e->getMessage());
            return null;
        }
    }

    /**
     * Get settings for display in admin panel.
     */
    public static function getSettings(): array
    {
        $instance = self::getInstance();
        return [
            'provider' => $instance->provider,
            'model' => $instance->model,
            'base_url' => $instance->baseUrl,
            'has_key' => !empty($instance->apiKey),
        ];
    }

    /**
     * Reload settings (call after admin saves new config).
     */
    public static function reload(): void
    {
        self::$instance = null;
    }
}