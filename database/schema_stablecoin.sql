-- DeFi Stablecoin Tracking Tables
-- Run this to enable stablecoin yield tracking

CREATE TABLE IF NOT EXISTS stablecoin_positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    chain VARCHAR(32) NOT NULL,
    protocol VARCHAR(64) NOT NULL,
    pool VARCHAR(128) NOT NULL,
    symbol VARCHAR(20) DEFAULT 'USDC',
    shares DECIMAL(15,4) DEFAULT 0,
    entry_price DECIMAL(10,4) DEFAULT 1,
    entry_date DATE,
    apy DECIMAL(8,4),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_chain (user_id, chain),
    INDEX idx_protocol (protocol)
);

CREATE TABLE IF NOT EXISTS stablecoin_yield_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    position_id INT NOT NULL,
    date DATE NOT NULL,
    price DECIMAL(10,4),
    yield_apy DECIMAL(8,4),
    gas_cost_usd DECIMAL(8,4) DEFAULT 0,
    FOREIGN KEY (position_id) REFERENCES stablecoin_positions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_position_date (position_id, date)
);