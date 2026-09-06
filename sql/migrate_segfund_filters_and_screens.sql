-- Migration: seg-fund filters (BR-11) + personal screens (BR-12)
-- Adds: risk_rating, death_benefit_pct, maturity_benefit_pct on seg_funds
-- New tables: user_screens, screen_shares

-- 1) seg_funds enrichment
ALTER TABLE seg_funds
    ADD COLUMN `risk_rating`           ENUM('Low','Low-Med','Medium','Med-High','High') NULL DEFAULT 'Medium' AFTER `category`,
    ADD COLUMN `death_benefit_pct`     TINYINT UNSIGNED NULL AFTER `risk_rating`,
    ADD COLUMN `maturity_benefit_pct`  TINYINT UNSIGNED NULL AFTER `death_benefit_pct`,
    ADD INDEX `idx_segfunds_risk`        (`risk_rating`),
    ADD INDEX `idx_segfunds_death_pct`   (`death_benefit_pct`),
    ADD INDEX `idx_segfunds_maturity_pct`(`maturity_benefit_pct`);

-- 2) user_screens
CREATE TABLE IF NOT EXISTS `user_screens` (
    `id`           INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`      INT NOT NULL,
    `name`         VARCHAR(120) NOT NULL,
    `description`  VARCHAR(500) NULL,
    `universe`     ENUM('stocks','segfunds') NOT NULL,
    `filters_json` JSON NOT NULL,
    `is_public`    TINYINT(1) NOT NULL DEFAULT 0,
    `is_deleted`   TINYINT(1) NOT NULL DEFAULT 0,
    `created_at`   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at`   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY `idx_user_screens_user`      (`user_id`, `is_deleted`),
    KEY `idx_user_screens_public`    (`is_public`, `is_deleted`),
    KEY `idx_user_screens_universe`  (`universe`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3) screen_shares (explicit per-user shares; public screens don't need a row)
CREATE TABLE IF NOT EXISTS `screen_shares` (
    `screen_id`           INT NOT NULL,
    `shared_with_user_id` INT NOT NULL,
    `permission`          ENUM('view','edit') NOT NULL DEFAULT 'view',
    `created_at`          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`screen_id`, `shared_with_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
