<?php
/**
 * Database — MySQL connection singleton.
 */
class Database {
    private static $pdo = null;

    public static function get(): PDO {
        if (self::$pdo === null) {
            $cfg = require __DIR__ . '/../../config/database.php';
            $dsn = "mysql:host={$cfg['host']};dbname={$cfg['database']};charset={$cfg['charset']}";
            self::$pdo = new PDO($dsn, $cfg['username'], $cfg['password'], [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ]);
        }
        return self::$pdo;
    }
}
