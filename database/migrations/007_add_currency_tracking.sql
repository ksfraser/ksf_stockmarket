-- Migration 007: Currency tracking + CASH symbols + DIV-RECV support
-- Safe to re-run: uses IF NOT EXISTS / IGNORE guards

-- 1. Currency column to portfolio (safe if already present)
SET @col_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'portfolio'
    AND COLUMN_NAME = 'currency'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE portfolio ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT ''CAD'' AFTER account_type, ADD INDEX idx_currency (currency)',
  'SELECT ''portfolio.currency already exists'' AS msg'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. DIV-RECV to transactions.type enum
SET @sql2 = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'transactions'
     AND COLUMN_NAME = 'type'
     AND DATA_TYPE = 'enum'
     AND COLUMN_TYPE LIKE '%DIV-RECV%') = 0,
  'ALTER TABLE transactions MODIFY COLUMN type ENUM(''BUY'',''SELL'',''DIVIDEND'',''SPLIT'',''TRANSFER'',''INTEREST'',''FEE'',''DIV-RECV'') NOT NULL DEFAULT ''BUY''',
  'SELECT ''type enum already includes DIV-RECV'' AS msg'
);
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

-- 3. CASH pseudo-symbols
INSERT IGNORE INTO symbol_master (symbol, name, exchange, geography, sector, currency, is_active, pipeline_state)
VALUES
  ('CASH-CAD', 'Cash (CAD)', 'CAD', 'CA', 'Cash', 'CAD', 1, 'active'),
  ('CASH-USD', 'Cash (USD)', 'USD', 'US', 'Cash', 'USD', 1, 'active'),
  ('CASH-EUR', 'Cash (EUR)', 'EUR', 'EU', 'Cash', 'EUR', 1, 'active'),
  ('CASH-GBP', 'Cash (GBP)', 'GBP', 'GB', 'Cash', 'GBP', 1, 'active'),
  ('CASH-CNY', 'Cash (CNY)', 'CNY', 'CN', 'Cash', 'CNY', 1, 'active');
