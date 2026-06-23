-- 006_add_transactions_user_id.sql
-- Ownership checks and per-user transaction filtering.
ALTER TABLE transactions
  ADD COLUMN user_id INT UNSIGNED NOT NULL DEFAULT 1 AFTER id,
  ADD INDEX idx_user_id (user_id),
  ADD INDEX idx_user_symbol_date (user_id, symbol, trade_date);

-- Backfill: map source_file='upload' transactions to their implied owner
-- via portfolio share rules when possible; otherwise leave as default 1.
UPDATE transactions t
JOIN portfolio p
  ON p.symbol = t.symbol
 AND p.account_type = t.account_type
 AND t.price_date BETWEEN DATE_SUB(p.entry_date, INTERVAL 7 DAY) AND DATE_ADD(p.entry_date, INTERVAL 7 DAY)
SET t.user_id = p.user_id
WHERE t.user_id = 1
  AND p.user_id != 1
  AND EXISTS (
    SELECT 1 FROM users u WHERE u.id = p.user_id AND u.role = 'advisor'
  );
