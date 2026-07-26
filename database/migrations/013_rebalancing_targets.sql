-- 013_rebalancing_targets.sql
-- Target allocations for portfolio rebalancing views.

CREATE TABLE IF NOT EXISTS rebalancing_targets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    strategy_name VARCHAR(60),
    target_type ENUM('geographic','sector','taxonomy','custom') NOT NULL DEFAULT 'taxonomy',
    target_allocations JSON NOT NULL,
    tolerance_pct DECIMAL(5,2) DEFAULT 5.00,
    rebalance_frequency VARCHAR(20) DEFAULT 'monthly',
    active TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_active (user_id, active)
) ENGINE=InnoDB;
