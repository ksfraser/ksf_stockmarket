-- Transactions table schema with source tracking
-- Run this to enable transaction delete/edit functionality

CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    type ENUM('BUY','SELL','DIVIDEND','SPLIT') NOT NULL,
    quantity DECIMAL(12,4) NOT NULL DEFAULT 0,
    price DECIMAL(12,4) DEFAULT 0,
    total DECIMAL(12,2) DEFAULT 0,
    commission DECIMAL(10,2) DEFAULT 0,
    account_type VARCHAR(20) DEFAULT '',
    notes TEXT,
    source_file VARCHAR(255) DEFAULT '',
    source_line INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_symbol (user_id, symbol),
    INDEX idx_trade_date (trade_date)
);