-- Track actual stop orders placed with brokerage
CREATE TABLE IF NOT EXISTS broker_stop_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    account_type ENUM('TFSA','RRSP','MARGIN') NOT NULL,
    stop_type ENUM('trailing_pct','trailing_price','stop_loss','stop_limit','atr') NOT NULL,
    stop_value DECIMAL(12,4), -- percentage or price depending on stop_type
    shares DECIMAL(12,2), -- shares covered by this stop (0 = all shares)
    status ENUM('active','triggered','cancelled','expired') DEFAULT 'active',
    placed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    triggered_at DATETIME NULL,
    notes VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX symbol_idx (symbol),
    INDEX status_idx (status),
    INDEX account_idx (account_type)
);