-- Password reset token columns (applied 2026-09-25 to ksfraser.ca live DB)
ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(128) DEFAULT NULL,
ADD COLUMN password_reset_expires_at TIMESTAMP NULL DEFAULT NULL,
ADD INDEX idx_token (password_reset_token);
