-- 004_add_advisor_tables.sql
-- Adds advisor account tracking and run orchestration tables.
-- Advisors are regular users; they share portfolio/transaction tables.
-- No separate cash tables.

CREATE TABLE IF NOT EXISTS advisor_accounts (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    slug VARCHAR(64) NOT NULL,
    strategy VARCHAR(64) NOT NULL DEFAULT 'buffett_quality',
    schedule ENUM('daily', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday') NOT NULL DEFAULT 'daily',
    max_positions INT UNSIGNED NOT NULL DEFAULT 20,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_slug (slug),
    UNIQUE KEY uk_user_id (user_id),
    CONSTRAINT fk_advisor_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS advisor_runs (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    advisor_id INT UNSIGNED NOT NULL,
    run_date DATE NOT NULL,
    status ENUM('running', 'completed', 'failed', 'skipped') NOT NULL DEFAULT 'running',
    universe_size INT UNSIGNED NULL,
    signals_generated INT UNSIGNED NULL,
    trades_executed INT UNSIGNED NULL,
    error_message TEXT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_advisor_date (advisor_id, run_date),
    INDEX idx_run_date (run_date),
    CONSTRAINT fk_run_advisor FOREIGN KEY (advisor_id) REFERENCES advisor_accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS portfolio_visibilities (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    account_type ENUM('RRSP','TFSA','MARGIN') NOT NULL DEFAULT 'MARGIN',
    is_public TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_symbol_account (user_id, symbol, account_type),
    CONSTRAINT fk_vis_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
