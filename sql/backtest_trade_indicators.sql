CREATE TABLE IF NOT EXISTS backtest_trade_indicators (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id INT NOT NULL,
  trade_id BIGINT NULL,
  symbol VARCHAR(50) NOT NULL,
  trade_date DATE NOT NULL,
  indicators JSON NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_run (run_id),
  INDEX idx_symbol_date (symbol, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
