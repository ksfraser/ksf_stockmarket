<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Model;

use PDO;
use RuntimeException;

/**
 * User model — modern user accounts with RBAC.
 *
 * Maps to the `users` table in the modernized schema.
 */
class User
{
    private PDO $db;

    public function __construct()
    {
        $this->db = Database::getConnection();
    }

    /**
     * Find a user by ID.
     */
    public function findById(int $id): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM users WHERE id = :id AND is_active = 1');
        $stmt->execute(['id' => $id]);
        return $stmt->fetch() ?: null;
    }

    /**
     * Find a user by username.
     */
    public function findByUsername(string $username): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM users WHERE username = :u AND is_active = 1');
        $stmt->execute(['u' => $username]);
        return $stmt->fetch() ?: null;
    }

    /**
     * Create a new user.
     */
    public function create(string $username, string $email, string $password,
                           string $role = 'viewer', string $firstName = '',
                           string $lastName = ''): int
    {
        $hash = password_hash($password, PASSWORD_ARGON2ID);
        $stmt = $this->db->prepare(
            'INSERT INTO users (username, email, password_hash, role, first_name, last_name)
             VALUES (:u, :e, :p, :r, :fn, :ln)'
        );
        $stmt->execute([
            'u' => $username, 'e' => $email, 'p' => $hash,
            'r' => $role, 'fn' => $firstName, 'ln' => $lastName,
        ]);
        return (int) $this->db->lastInsertId();
    }

    /**
     * Verify a password.
     */
    public function verifyPassword(string $username, string $password): ?array
    {
        $user = $this->findByUsername($username);
        if ($user && password_verify($password, $user['password_hash'])) {
            // Rehash if needed
            if (password_needs_rehash($user['password_hash'], PASSWORD_ARGON2ID)) {
                $newHash = password_hash($password, PASSWORD_ARGON2ID);
                $stmt = $this->db->prepare('UPDATE users SET password_hash = :h WHERE id = :id');
                $stmt->execute(['h' => $newHash, 'id' => $user['id']]);
            }
            return $user;
        }
        return null;
    }

    /**
     * Get all users.
     */
    public function getAll(): array
    {
        return $this->db->query('SELECT id, username, email, role, first_name, last_name, is_active, created_at FROM users ORDER BY username')->fetchAll();
    }
}
