-- Create admin user ksfraser
INSERT INTO users (username, email, password_hash, display_name, role, is_active)
VALUES (
    'ksfraser',
    'kevin@ksfraser.ca',
    -- Password: Letmein1 (bcrypt hash — regenerate with PHP)
    '$2y$10$placeholder_regenerate_with_php',
    'Kevin',
    'admin',
    1
)
ON DUPLICATE KEY UPDATE display_name = 'Kevin', role = 'admin', is_active = 1;
