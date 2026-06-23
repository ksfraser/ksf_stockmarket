-- 004_add_advisor_tables.sql
-- Adds advisor run orchestration tracking.
-- Advisors are regular users (role='advisor'); they share portfolio/transaction tables.
-- No separate cash tables and no advisor_accounts table.

CREATE TABLE IF NOT EXISTS advisor_runs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    run_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    universe_size INT DEFAULT NULL,
    signals_generated INT DEFAULT NULL,
    trades_executed INT DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    finished_at TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_date (user_id, run_date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
