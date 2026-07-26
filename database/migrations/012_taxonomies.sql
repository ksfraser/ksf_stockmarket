-- 012_taxonomies.sql
-- Flexible taxonomy system for classifying securities.

CREATE TABLE IF NOT EXISTS taxonomies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    name VARCHAR(60) NOT NULL,
    type ENUM('region','sector','strategy','custom') NOT NULL DEFAULT 'custom',
    parent_id INT NULL,
    is_active TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_active (user_id, is_active)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS taxonomy_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    taxonomy_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    weight DECIMAL(5,4) DEFAULT 0,
    notes VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_taxonomy_symbol (user_id, taxonomy_id, symbol),
    INDEX idx_user_symbol (user_id, symbol),
    FOREIGN KEY (taxonomy_id) REFERENCES taxonomies(id) ON DELETE CASCADE
) ENGINE=InnoDB;
