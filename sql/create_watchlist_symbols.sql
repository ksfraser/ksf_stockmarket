-- Create watchlist_symbols table for DB-driven volume spike monitoring
CREATE TABLE IF NOT EXISTS watchlist_symbols (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    list_type ENUM('portfolio', 'watchlist', 'blacklist') NOT NULL DEFAULT 'watchlist',
    monitor_volume TINYINT(1) NOT NULL DEFAULT 1,
    monitor_price TINYINT(1) NOT NULL DEFAULT 0,
    alert_threshold_pct DECIMAL(5,2) DEFAULT NULL,
    volume_spike_threshold DECIMAL(4,1) NOT NULL DEFAULT 2.0,
    notes VARCHAR(200) DEFAULT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_list (symbol, list_type),
    INDEX idx_list_type (list_type),
    INDEX idx_monitor (monitor_volume, is_active)
);
