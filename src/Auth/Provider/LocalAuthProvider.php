<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth\Provider;

use Ksf\StockMarket\Auth\AuthProviderInterface;
use Ksf\StockMarket\Model\User as UserModel;

/**
 * Local username/password authentication against the users table.
 *
 * This is the default provider that validates credentials directly — no redirect.
 */
class LocalAuthProvider implements AuthProviderInterface
{
    private UserModel $userModel;

    public function __construct()
    {
        $this->userModel = new UserModel();
    }

    public function getName(): string
    {
        return 'local';
    }

    public function getBrandClass(): string
    {
        return 'fa-user';
    }

    public function isAvailable(): bool
    {
        return true;
    }

    public function getLoginUrl(): ?string
    {
        return null;
    }

    public function isRedirectBased(): bool
    {
        return false;
    }

    public function validateCredentials(array $credentials): ?array
    {
        $username = $credentials['username'] ?? '';
        $password = $credentials['password'] ?? '';

        if ($username === '' || $password === '') {
            return null;
        }

        $user = $this->userModel->verifyPassword($username, $password);
        if ($user === null) {
            return null;
        }

        return $this->normalizeUser($user);
    }

    public function handleCallback(array $callbackData): array
    {
        throw new \LogicException('LocalAuthProvider does not use OAuth callbacks.');
    }

    public function normalizeUser(array $identity): array
    {
        return [
            'id'          => (string) ($identity['id'] ?? ''),
            'provider'    => 'local',
            'provider_id' => (string) ($identity['id'] ?? ''),
            'email'       => $identity['email'] ?? '',
            'username'    => $identity['username'] ?? '',
            'display_name'=> $identity['display_name'] ?? ($identity['first_name'] ?? '') . ' ' . ($identity['last_name'] ?? ''),
            'first_name'  => $identity['first_name'] ?? '',
            'last_name'   => $identity['last_name'] ?? '',
            'role'        => $identity['role'] ?? 'viewer',
            'avatar_url'  => $identity['avatar_url'] ?? null,
            'raw_payload' => $identity,
        ];
    }

    public function getConfigSummary(): array
    {
        return ['type' => 'local'];
    }
}
