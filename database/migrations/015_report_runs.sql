-- 015_report_runs.sql
-- Cache expensive report generation so we don't hammer the DB on every page load.

CREATE TABLE IF NOT EXISTS report_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    parameters JSON,
    result JSON,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    INDEX idx_user_type (user_id, report_type, generated_at)
) ENGINE=InnoDB;
