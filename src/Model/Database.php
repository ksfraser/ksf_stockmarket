<?php
/**
 * Database — MySQL connection singleton.
 *
 * Supports both the legacy `getConnection()` API (pre-2026) and the
 * current `get()` API used by controllers.
 */
class Database {
    private static $pdo = null;

    /** Legacy alias — returns the same singleton PDO as get(). */
    public static function getConnection(): PDO {
        return self::get();
    }

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
