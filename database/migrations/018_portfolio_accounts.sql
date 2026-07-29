-- portfolio_accounts: institution/account lookup for portfolio + transactions
CREATE TABLE IF NOT EXISTS portfolio_accounts (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL DEFAULT 1,
    institution VARCHAR(100) NOT NULL,
    account_nickname VARCHAR(100) NOT NULL,
    account_number_masked VARCHAR(32) NULL,
    registration_type ENUM('RRSP','TFSA','RESP','LIRA','LIF','FHSA','MARGIN','NON-REGISTERED','SPOUSAL-RRSP','SPOUSAL-RESP','OTHER') NOT NULL DEFAULT 'NON-REGISTERED',
    currency CHAR(3) NOT NULL DEFAULT 'CAD',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_registration (registration_type),
    UNIQUE KEY uq_user_account (user_id, institution, account_nickname, account_number_masked)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
