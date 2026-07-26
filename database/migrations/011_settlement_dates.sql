-- 011_settlement_dates.sql
-- Add settlement_date for T+2 trade settlement tracking.

ALTER TABLE transactions ADD COLUMN settlement_date DATE NULL AFTER trade_date;
ALTER TABLE transactions ADD INDEX idx_settlement_date (settlement_date);
