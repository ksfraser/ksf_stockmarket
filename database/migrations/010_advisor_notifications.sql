-- 010_advisor_notifications.sql
-- Per-user notification preferences and advisor recommendation queue.
-- Preferences stored in user_settings to match existing pattern:
--   setting_key='advisor_notify_email', setting_value='1'
--   setting_key='advisor_notify_discord_dm', setting_value='1'
--   setting_key='advisor_discord_channel_id', setting_value='123456789'
--   setting_key='advisor_notify_whatsapp', setting_value='1'
--   setting_key='advisor_whatsapp_number', setting_value='+15551234567'

-- Recommendation queue: one row per user per advisor per symbol per run
CREATE TABLE IF NOT EXISTS advisor_recommendations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    advisor_id INT UNSIGNED NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    action ENUM('BUY','SELL','HOLD') NOT NULL DEFAULT 'BUY',
    price DECIMAL(15,4) NOT NULL,
    max_price DECIMAL(15,4) NULL DEFAULT NULL,
    stop_limit DECIMAL(15,4) NULL DEFAULT NULL,
    notes TEXT NULL,
    signal_reasons TEXT NULL,
    recommended_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_email TINYINT(1) NOT NULL DEFAULT 0,
    sent_discord_dm TINYINT(1) NOT NULL DEFAULT 0,
    sent_discord_channel TINYINT(1) NOT NULL DEFAULT 0,
    sent_whatsapp TINYINT(1) NOT NULL DEFAULT 0,
    sent_at DATETIME NULL DEFAULT NULL,
    INDEX idx_user_pending (user_id, sent_email, sent_discord_dm, recommended_at),
    INDEX idx_advisor (advisor_id, recommended_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
