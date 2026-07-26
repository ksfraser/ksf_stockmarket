-- 009_user_advisors.sql
-- Adds user-hirable advisors and advisor transaction linking.
-- Advisors are stored in advisor_accounts; users hire via user_advisors.

-- Advisor id on transactions so we can trace which advisor caused a trade
ALTER TABLE transactions
  ADD COLUMN advisor_id INT UNSIGNED NULL DEFAULT NULL AFTER user_id,
  ADD INDEX idx_advisor_id (advisor_id),
  ADD INDEX idx_user_advisor (user_id, advisor_id);

-- User hiring table
CREATE TABLE IF NOT EXISTS user_advisors (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    advisor_id INT UNSIGNED NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    hired_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paused_at DATETIME NULL DEFAULT NULL,
    notes TEXT NULL,
    UNIQUE KEY uq_user_advisor (user_id, advisor_id),
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_advisor (advisor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Backfill: attach existing advisor-generated transactions to advisor accounts
-- Best-effort. If the notes parser collides, skip backfill; advisor_id can be
-- filled manually or via a later cleanup script.
UPDATE transactions t
JOIN advisor_accounts aa ON aa.slug COLLATE utf8mb4_unicode_ci = CONVERT(
  SUBSTRING_INDEX(SUBSTRING_INDEX(t.notes, 'advisor ', -1), ' ', 1)
  USING utf8mb4
) COLLATE utf8mb4_unicode_ci
SET t.advisor_id = aa.id
WHERE t.advisor_id IS NULL
  AND t.source_file = 'advisor'
  AND t.notes LIKE '%advisor%';
