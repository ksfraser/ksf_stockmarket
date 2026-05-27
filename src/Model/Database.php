<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Model;

use PDO;
use PDOException;
use RuntimeException;

/**
 * Database connection factory.
 *
 * Provides PDO connections using configured credentials.
 * Uses MariaDB via PDO for all database access.
 */
class Database
{
    private static ?PDO $connection = null;

    /**
     * Get the singleton PDO connection.
     */
    public static function getConnection(): PDO
    {
        if (self::$connection === null) {
            self::$connection = self::createConnection();
        }

        return self::$connection;
    }

    /**
     * Create a new PDO connection from environment config.
     */
    private static function createConnection(): PDO
    {
        $host = $_ENV['DB_HOST'] ?? 'localhost';
        $port = $_ENV['DB_PORT'] ?? '3306';
        $dbname = $_ENV['DB_NAME'] ?? 'ksf_stockmarket';
        $user = $_ENV['DB_USER'] ?? 'ksf_stockmarket';
        $pass = $_ENV['DB_PASS'] ?? '';
        $charset = 'utf8mb4';

        $dsn = "mysql:host={$host};port={$port};dbname={$dbname};charset={$charset}";

        try {
            $pdo = new PDO($dsn, $user, $pass, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::ATTR_STRINGIFY_FETCHES => false,
            ]);

            return $pdo;
        } catch (PDOException $e) {
            throw new RuntimeException(
                'Database connection failed: ' . $e->getMessage(),
                (int) $e->getCode(),
                $e
            );
        }
    }

    /**
     * Close the database connection.
     */
    public static function disconnect(): void
    {
        self::$connection = null;
    }

    /**
     * Check if the connection is alive.
     */
    public static function isConnected(): bool
    {
        if (self::$connection === null) {
            return false;
        }

        try {
            self::$connection->query('SELECT 1');

            return true;
        } catch (PDOException) {
            return false;
        }
    }
}
