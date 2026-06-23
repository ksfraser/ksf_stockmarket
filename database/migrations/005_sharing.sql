-- Sharing model: users can share portfolios/transactions globally or with designated users.
-- Advisor accounts are globally shared by default.
-- Regular users can opt-in to global or per-user sharing.

CREATE TABLE IF NOT EXISTS portfolio_visibilities (
    user_id INT UNSIGNED NOT NULL PRIMARY KEY,
    is_public TINYINT(1) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pv_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS portfolio_share_users (
    user_id INT UNSIGNED NOT NULL,
    shared_with_user_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, shared_with_user_id),
    CONSTRAINT fk_psu_owner FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_psu_viewer FOREIGN KEY (shared_with_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO portfolio_visibilities (user_id, is_public)
    SELECT id, 1 FROM users WHERE role = 'advisor' AND id NOT IN (SELECT user_id FROM portfolio_visibilities)
    ON DUPLICATE KEY UPDATE is_public = is_public;
