-- Add account_id to portfolio and transactions for institution/registration type tracking
ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS account_id INT UNSIGNED NULL AFTER user_id,
    ADD CONSTRAINT fk_portfolio_account FOREIGN KEY (account_id) REFERENCES portfolio_accounts(id) ON DELETE SET NULL;

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_id INT UNSIGNED NULL AFTER user_id,
    ADD CONSTRAINT fk_transactions_account FOREIGN KEY (account_id) REFERENCES portfolio_accounts(id) ON DELETE SET NULL;

-- Backfill registration_type from portfolio.account_type for existing rows
UPDATE portfolio p
JOIN portfolio_accounts pa ON pa.user_id = p.user_id
    AND pa.institution = 'Unknown'
    AND pa.account_nickname = CONCAT('Legacy ', p.account_type)
    AND pa.registration_type = p.account_type
SET p.account_id = pa.id
WHERE p.account_id IS NULL;
