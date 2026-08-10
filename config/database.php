<?php
/**
 * Database config — reads from environment variables.
 *
 * Required env vars (set in Apache vhost or .env file):
 *   DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_CHARSET
 *
 * Credentials are stored in ansible-vault (group_vars/vault.yml).
 * Deploy script populates .env from vault.
 * NEVER commit plaintext credentials.
 */
return [
    'host'     => getenv('DB_HOST')     ?: 'ksfraser.ca',
    'database'  => getenv('DB_NAME')     ?: 'ksfraser_stock_market',
    'username'  => getenv('DB_USER')     ?: '',
    'password'  => getenv('DB_PASS')     ?: '',
    'charset'  => getenv('DB_CHARSET')   ?: 'utf8mb4',
];
