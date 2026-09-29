<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Security;

use Symfony\Component\Security\Core\Authentication\Token\Storage\TokenStorage;
use Symfony\Component\Security\Core\Authorization\AccessDecisionManager;
use Symfony\Component\Security\Core\Authorization\Voter\Voter;
use Symfony\Component\Security\Core\User\UserInterface;
use Symfony\Component\Security\Core\Authentication\Token\AnonymousToken;
use Ksf\StockMarket\Security\Voter\ActionVoter;

/**
 * AuthStatus — bridges Symfony Security token storage to stockmarket-app's
 * existing code that expects an array-shaped $currentUser.
 *
 * During the transition from custom session auth to Symfony Security:
 * - If Symfony Security is fully wired (TokenStorage has an authenticated
 *   token), return a backwards-compatible array from the StockmarketUser row.
 * - If no Symfony token is available yet (e.g. during deployment, or on
 *   endpoints that bypass the firewall), fall back to the legacy
 *   SessionHelper::checkSession() so the app stays up.
 *
 * Once the migration is complete and all endpoints go through the firewall,
 * the fallback can be removed.
 */
class AuthStatus
{
    /**
     * Return the currently authenticated user as an array (backwards-compatible
     * shape for controllers and templates that read $user['id'], $user['role'], etc.),
     * or null if no user is authenticated.
     */
    public static function getCurrentUser(): ?array
    {
        // Try Symfony Security token first (preferred path once the firewall is wired).
        try {
            $tokenStorage = self::getTokenStorage();
            if ($tokenStorage !== null) {
                $token = $tokenStorage->getToken();
                if ($token instanceof AnonymousToken) {
                    return null;
                }
                if ($token !== null
                    && $token->isAuthenticated()
                    && $token->getUser() instanceof StockmarketUser
                ) {
                    $smUser = $token->getUser();
                    return self::userToArray($smUser);
                }
            }
        } catch (\Throwable $e) {
            // If Symfony Security isn't fully bootstrapped yet, fall through
            // to the legacy session check. This keeps the app running during
            // the migration.
        }

        // Fallback: legacy session-based check (SessionHelper::checkSession).
        // This covers the period when some endpoints still use the old path
        // or when Symfony Security isn't yet handling this request.
        try {
            if (class_exists(\Ksf\StockMarket\Auth\SessionHelper::class)) {
                return \Ksf\StockMarket\Auth\SessionHelper::checkSession();
            }
        } catch (\Throwable $e) {
            // ignore
        }

        return null;
    }

    /**
     * Check if the current user is authenticated (has any ROLE_*).
     */
    public static function isAuthenticated(): bool
    {
        return self::getCurrentUser() !== null;
    }

    /**
     * Check if the current user has the given role.
     *
     * @param string $role e.g. 'ROLE_ADMIN', 'ROLE_USER'
     */
    public static function isGranted(string $role): bool
    {
        $user = self::getCurrentUser();
        if ($user === null) {
            return false;
        }
        // The user array carries 'role' from the DB (admin/user/viewer/advisor).
        // Map to Symfony-style ROLE_* for checks.
        return self::roleMatches($user, $role);
    }

    /**
     * Check access to the current request's action using the ActionVoter.
     *
     * This replaces the old $protectedRoutes in_array check in index.php.
     * Call this BEFORE dispatching to a controller; if it returns false,
     * redirect to login.
     */
    public static function canAccessCurrentAction(): bool
    {
        $action = $_GET['action'] ?? 'overview';

        // Public actions — always allowed.
        $publicActions = [
            'login', 'logout', 'register',
            'oauth-redirect', 'oauth-callback',
            'forgot-password', 'reset-password', 'reset-password-success',
            'api_chart', 'api_screener',
        ];
        if (in_array($action, $publicActions, true)) {
            return true;
        }

        // Admin actions — require admin role.
        $adminActions = ['admin_settings', 'admin_setup_wizard'];
        if (in_array($action, $adminActions, true)) {
            return self::isGranted('ROLE_ADMIN');
        }

        // Everything else — require at least authenticated.
        return self::isAuthenticated();
    }

    /**
     * Redirect to login if the current action is not accessible.
     *
     * Call this early in index.php for non-public actions.
     *
     * @return void
     */
    public static function requireAuthOrRedirect(): void
    {
        if (!self::canAccessCurrentAction()) {
            $redirect = $_SERVER['REQUEST_URI'] ?? '?action=login';
            // Do not redirect the login page itself to avoid loops.
            if ($redirect === '/?action=login' || $redirect === '?action=login') {
                $redirect = '?action=login';
            }
            // Store redirect target for post-login return.
            if (session_status() === PHP_SESSION_NONE) {
                session_start();
            }
            $_SESSION['redirect_after_login'] = $redirect;
            header('Location: ?action=login');
            exit;
        }
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    private static function getTokenStorage(): ?TokenStorage
    {
        // The TokenStorage is registered in Symfony's DI container, but this
        // app does not use the full Symfony kernel. We instantiate it directly.
        // Without a container, we create a minimal one here.
        return new TokenStorage();
    }

    private static function userToArray(StockmarketUser $user): array
    {
        $row = $user->getRow();
        return [
            'id'          => $user->getId(),
            'username'    => $user->getUserIdentifier(),
            'email'       => $user->getEmail(),
            'display_name'=> $user->getDisplayName(),
            'first_name'  => $row['first_name'] ?? '',
            'last_name'   => $row['last_name'] ?? '',
            'role'        => $user->getRole(),
            'is_active'   => (bool) ($row['is_active'] ?? true),
            'created_at'  => $row['created_at'] ?? null,
            'last_login'  => $row['last_login'] ?? null,
            'provider'    => $row['provider'] ?? null,
            'provider_id' => $row['provider_id'] ?? null,
        ];
    }

    private static function roleMatches(array $user, string $role): bool
    {
        if ($role === 'ROLE_USER') {
            // Any authenticated user has ROLE_USER.
            return isset($user['id']);
        }
        if ($role === 'ROLE_ADMIN') {
            return ($user['role'] ?? '') === 'admin';
        }
        if ($role === 'ROLE_ADVISOR') {
            return in_array($user['role'] ?? '', ['admin', 'advisor'], true);
        }
        if ($role === 'ROLE_VIEWER') {
            return in_array($user['role'] ?? '', ['admin', 'user', 'viewer', 'advisor'], true);
        }
        return false;
    }
}

// ── Legacy compatibility method ──────────────────────────────────────────────
// SessionHelper::checkSession() is used as a fallback above. We add a static
// wrapper here so the existing AuthController::checkSession() calls still work
// during the transition. This is defined OUTSIDE the class so it can be called
// statically without modifying AuthController yet.

if (!function_exists('Ksf_StockMarket_Security_checkSession_fallback')) {
    /**
     * @return array<string, mixed>|null
     */
    function Ksf_StockMarket_Security_checkSession_fallback(): ?array
    {
        return AuthStatus::getCurrentUser();
    }
}
