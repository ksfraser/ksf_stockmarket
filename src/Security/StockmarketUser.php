<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Security;

use Symfony\Component\Security\Core\User\EquatableInterface;
use Symfony\Component\Security\Core\User\PasswordAuthenticatedUserInterface;
use Symfony\Component\Security\Core\User\UserInterface;

/**
 * StockmarketUser - Symfony UserInterface wrapper around a raw `users` table row.
 *
 * Used by UserRepository to present app users to the Symfony Security firewall.
 * Keeps a copy of the full DB row so controllers can read display_name, role,
 * is_active, etc. without an extra query.
 */
class StockmarketUser implements UserInterface, PasswordAuthenticatedUserInterface, EquatableInterface
{
    public function __construct(
        private readonly string $identifier,
        private readonly string $email,
        private readonly string $passwordHash,
        private readonly array $roles,
        private readonly array $row,
    ) {
    }

    public function getRoles(): array
    {
        if (empty($this->roles)) {
            return ['ROLE_USER'];
        }
        return array_values(array_unique($this->roles));
    }

    public function eraseCredentials(): void
    {
        // No plaintext credentials held - password_hash is already hashed.
    }

    public function getUserIdentifier(): string
    {
        return $this->identifier;
    }

    public function getPassword(): ?string
    {
        return $this->passwordHash !== '' ? $this->passwordHash : null;
    }

    public function isEqualTo(UserInterface $user): bool
    {
        if (!($user instanceof self)) {
            return false;
        }
        return $this->identifier === $user->getUserIdentifier()
            && $this->passwordHash === $user->getPassword()
            && $this->getRoles() === $user->getRoles();
    }

    // Convenience accessors for controllers

    public function getId(): ?int
    {
        $id = $this->row['id'] ?? null;
        return $id !== null ? (int) $id : null;
    }

    public function getRow(): array
    {
        return $this->row;
    }

    public function getDisplayName(): string
    {
        return $this->row['display_name']
            ?? ($this->row['first_name'] ?? '') . ' ' . ($this->row['last_name'] ?? '');
    }

    public function getRole(): string
    {
        return $this->row['role'] ?? 'user';
    }

    public function getEmail(): string
    {
        return $this->email;
    }
}
