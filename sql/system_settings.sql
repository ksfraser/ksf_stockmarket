-- System-level settings editable via admin interface
-- Stores webhook URLs and LLM configuration
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_type ENUM('string', 'text', 'password', 'integer', 'float') DEFAULT 'string',
    description VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX KEY_IDX (setting_key)
);

-- Insert default settings if not exist
INSERT IGNORE INTO system_settings (setting_key, setting_value, setting_type, description) VALUES
('discord_webhook_url', '', 'text', 'Discord webhook URL for #stock-sell-alerts channel'),
('discord_alert_webhook', '', 'text', 'Discord webhook for alert messages (specific channel)'),
('discord_bot_token', '', 'password', 'Discord bot token for sending messages'),
('llm_provider', 'openrouter', 'string', 'LLM provider: openrouter, ollama, google, openai'),
('llm_model', 'anthropic/claude-sonnet-4', 'string', 'Default LLM model identifier'),
('llm_api_key', '', 'password', 'API key for LLM provider (if not using OpenRouter)'),
('llm_base_url', '', 'string', 'Custom base URL for LLM provider'),
('ta_run_frequency', 'daily', 'string', 'TA indicator run frequency: daily, twice_daily, intraday'),
('alert_check_frequency', '15min', 'string', 'Price/volume alert check frequency'),
('max_symbols_per_run', '100', 'integer', 'Maximum symbols to process per cron run');