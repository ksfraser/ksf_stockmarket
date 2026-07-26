-- 014_extra_transaction_types.sql
-- Extend transactions.type enum to cover deposits, withdrawals, delivery,
-- tax, and interest charge so we can model the full portfolio lifecycle.

SET @col_exists := (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'transactions'
    AND COLUMN_NAME = 'type'
    AND DATA_TYPE = 'enum'
);
SET @current := (
  SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'transactions'
    AND COLUMN_NAME = 'type'
);
SET @desired := 'enum(''BUY'',''SELL'',''DIVIDEND'',''SPLIT'',''TRANSFER'',''INTEREST'',''FEE'',''DIV-RECV'',''DEPOSIT'',''WITHDRAWAL'',''DELIVERY'',''TAX'',''INTEREST_CHARGE'')';
SET @sql := IF(@col_exists = 0,
  CONCAT('ALTER TABLE transactions ADD COLUMN type ', @desired, ' NOT NULL DEFAULT ''BUY'''),
  CONCAT('ALTER TABLE transactions MODIFY COLUMN type ', @desired)
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
