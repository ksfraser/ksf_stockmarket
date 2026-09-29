<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Security;

use PDO;
use RuntimeException;
use Symfony\Component\Security\Core\Exception\UnsupportedUserException;
use Symfony\Component\Security\Core\Exception\UsernameNotFoundException;
use Symfony\Component\Security\Core\User\UserInterface;
use Symfony\Component\Security\Core\User\UserProviderInterface;

/**
 * UserRepository — Symfony UserProviderInterface adapter for the stockmarket-app
 * `users` table.
 *
 * Bridges the existing Ksf\StockMarket\Model\User query methods into Symfony
 * Security's user-provider contract so the firewall can load, refresh, and
 * support-forget users during authentication and session reloads.
 *
 * Keeps the existing `users` table schema unchanged (id, username, email,
 * password_hash, display_name, role, is_active, created_at, last_login,
 * password_reset_token, password_reset_expires_at).
 */
class UserRepository implements UserProviderInterface
{
    private ?PDO $pdo = null;

    private function getPdo(): PDO
    {
        if ($this->pdo === null) {
            $this->pdo = \Ksf\StockMarket\Model\Database::get();
        }
        return $this->pdo;
    }

    /**
     * {@inheritdoc}
     */
    public function refreshUser(UserInterface $user): UserInterface
    {
        if (!($user instanceof StockmarketUser)) {
            throw new UnsupportedUserException(sprintf(
                'Instances of "%s" are not supported.',
                get_class($user),
            ));
        }

        $id = $user->getId();
        if ($id === null || $id === '') {
            throw new UnsupportedUserException('User has no id.');
        }

        $row = $this->findById((int) $id);
        if ($row === null) {
            throw new UsernameNotFoundException(sprintf(
                'User with id "%s" no longer exists.',
                $id,
            ));
        }

        return $this->mapRowToUser($row);
    }

    /**
     * {@inheritdoc}
     *
     * Called during session reload to re-fetch the user from the DB each
     * request (supports is_active changes, role changes, etc.).
     */
    public function loadUserByIdentifier(string $identifier): UserInterface
    {
        $row = $this->findByUsernameOrEmail($identifier);

        if ($row === null) {
            throw new UsernameNotFoundException(sprintf(
                'User "%s" not found.',
                $identifier,
            ));
        }

        return $this->mapRowToUser($row);
    }

    private function mapRowToUser(array $row): StockmarketUser
    {
        return new StockmarketUser(
            $row['username'],
            $row['email'] ?? '',
            $row['password_hash'] ?? '',
            $this->rolesFromRow($row),
            $row,
        );
    }

    /**
     * {@inheritdoc}
     *
     * Supports only StockmarketUser. Symfony's RememberMe / session storage
     * may call this with deserialized user objects.
     */
    public function supportsClass(string $class): bool
    {
        return $class === StockmarketUser::class
            || is_subclass_of($class, StockmarketUser::class);
    }

    // ── Raw DB access (keeps the adapter thin) ───────────────────────────────

    /**
     * Find a user row by numeric id (active only).
     */
    private function findById(int $id): ?array
    {
        $stmt = $this->getPdo()->prepare(
            'SELECT * FROM users WHERE id = :id AND is_active = 1'
        );
        $stmt->execute(['id' => $id]);
        return $stmt->fetch() ?: null;
    }

    /**
     * Find a user row by username OR email (active only).
     *
     * The identifier passed by Symfony is the "username" — but our app
     * historically allows login by email too, so we search both.
     */
    private function findByUsernameOrEmail(string $identifier): ?array
    {
        // Fast path: try username first (exact match, indexed).
        $stmt = $this->getPdo()->prepare(
            'SELECT * FROM users
             WHERE username = :u AND is_active = 1'
        );
        $stmt->execute(['u' => $identifier]);
        $row = $stmt->fetch();
        if ($row !== false) {
            return $row;
        }

        // Fallback: email (case-insensitive).
        $stmt = $this->getPdo()->prepare(
            'SELECT * FROM users
             WHERE email = :e AND is_active = 1'
        );
        $stmt->execute(['e' => strtolower($identifier)]);
        $row = $stmt->fetch();
        if ($row !== false) {
            return $row;
        }

        return null;
    }

    /**
     * Map the DB `role` column to Symfony roles.
     *
     * DB values: admin, user, viewer, advisor (nullable on some rows).
     *
     * Symfony convention: ROLE_<UPPER>. Map:
     *   admin  -> ROLE_ADMIN, ROLE_USER
     *   advisor-> ROLE_ADVISOR, ROLE_USER
     *   user   -> ROLE_USER
     *   viewer -> ROLE_VIEWER, ROLE_USER
     */
    private function rolesFromRow(array $row): array
    {
        $raw = $row['role'] ?? 'user';
        $raw = strtolower(trim((string) $raw));

        $roles = [];

        // Every non-admin gets at least ROLE_USER so protected routes work.
        $roles[] = 'ROLE_USER';

        return match ($raw) {
            'admin'   => array_merge($roles, ['ROLE_ADMIN']),
            'advisor' => array_merge($roles, ['ROLE_ADVISOR']),
            'viewer'  => array_merge($roles, ['ROLE_VIEWER']),
            default   => $roles,
        };
    }
}
