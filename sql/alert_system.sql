-- Alert queue and notification system
-- Run this on ksfraser_stockmarket database

CREATE TABLE IF NOT EXISTS alert_queue (
    id VARCHAR(64) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    payload JSON,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    llm_analysis TEXT,
    llm_model VARCHAR(50),
    completed_at TIMESTAMP NULL,
    INDEX idx_status (status),
    INDEX idx_symbol (symbol),
    INDEX idx_type (alert_type)
);

-- Alert responses that Hermes/LLM can write
CREATE TABLE IF NOT EXISTS alert_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id VARCHAR(64),
    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_type ENUM('discord', 'email', 'direct') DEFAULT 'direct',
    responder VARCHAR(100), -- 'hermes', 'discord_bot', etc.
    response_text TEXT,
    action_taken VARCHAR(255), -- 'buy', 'sell', 'hold', 'review_requested'
    FOREIGN KEY (alert_id) REFERENCES alert_queue(id)
);

-- Status updates for alerts
CREATE TABLE IF NOT EXISTS alert_status_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id VARCHAR(64),
    status_change TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    from_status ENUM('pending', 'processing', 'completed', 'failed'),
    to_status ENUM('pending', 'processing', 'completed', 'failed'),
    notes TEXT,
    FOREIGN KEY (alert_id) REFERENCES alert_queue(id)
);