-- Intraday 15-minute OHLCV data table
CREATE TABLE IF NOT EXISTS intraday_15min (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    datetime DATETIME NOT NULL,
    open_price DECIMAL(12,4),
    high_price DECIMAL(12,4),
    low_price DECIMAL(12,4),
    close_price DECIMAL(12,4),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_bar (symbol, datetime),
    KEY idx_symbol_date (symbol, datetime),
    KEY idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Optimized for intraday queries
ALTER TABLE intraday_15min 
    ADD INDEX idx_datetime (datetime),
    ADD INDEX idx_symbol_volume (symbol, volume);

-- Partition by month for performance
ALTER TABLE intraday_15min 
    PARTITION BY RANGE (YEAR(datetime) * 100 + MONTH(datetime)) (
        PARTITION p202401 VALUES LESS THAN (202402),
        PARTITION p202402 VALUES LESS THAN (202403),
        PARTITION p202403 VALUES LESS THAN (202404),
        PARTITION p202404 VALUES LESS THAN (202405),
        PARTITION p202405 VALUES LESS THAN (202406),
        PARTITION p202406 VALUES LESS THAN (202407),
        PARTITION p202407 VALUES LESS THAN (202408),
        PARTITION p202408 VALUES LESS THAN (202409),
        PARTITION p202409 VALUES LESS THAN (202410),
        PARTITION p202410 VALUES LESS THAN (202411),
        PARTITION p202411 VALUES LESS THAN (202412),
        PARTITION p202412 VALUES LESS THAN (202413),
        PARTITION p202501 VALUES LESS THAN (202502),
        PARTITION p_future VALUES LESS THAN MAXVALUE
    );