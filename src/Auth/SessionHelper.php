<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Auth;

use Ksf\StockMarket\Model\Database;

/**
 * SessionHelper — thin wrapper for auth-session lifecycle.
 *
 * Centralizes the session/cookie logic that was previously inline in
 * AuthController::login().  Other parts of the system (e.g. OAuth callback
 * handler) can call loginSuccess() without duplicating the remember-me cookie
 * and user_sessions insertion.
 */
class SessionHelper
{
    /**
     * Establish a logged-in session for the given user row.
     *
     * @param array<string, mixed> $user  Full user row from the users table.
     * @param bool $remember  Whether to set a 30-day remember-me cookie.
     * @return void
     */
    public static function loginSuccess(array $user, bool $remember = false): void
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }

        $_SESSION['user_id'] = $user['id'];
        $_SESSION['user']    = $user;

        // Update last login timestamp.
        $pdo = Database::get();
        $pdo->prepare('UPDATE users SET last_login = NOW() WHERE id = :id')
            ->execute([':id' => $user['id']]);

        // Remember-me cookie.
        if ($remember) {
            $sid = bin2hex(random_bytes(64));
            $expires = date('Y-m-d H:i:s', strtotime('+30 days'));
            $pdo->prepare(
                'INSERT INTO user_sessions (id, user_id, ip_address, user_agent, expires_at)
                 VALUES (:sid, :uid, :ip, :ua, :exp)'
            )->execute([
                ':sid'  => $sid,
                ':uid'  => $user['id'],
                ':ip'   => $_SERVER['REMOTE_ADDR'] ?? '',
                ':ua'   => $_SERVER['HTTP_USER_AGENT'] ?? '',
                ':exp'  => $expires,
            ]);
            setcookie('owl_session', $sid, strtotime('+30 days'), '/', '', false, true);
        }
    }

    /**
     * Destroy the current session and remember-me cookie.
     */
    public static function logout(): void
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }

        if (!empty($_COOKIE['owl_session'])) {
            try {
                $pdo = Database::get();
                $pdo->prepare('DELETE FROM user_sessions WHERE id = :sid')
                    ->execute([':sid' => $_COOKIE['owl_session']]);
            } catch (\Exception $e) {
                // ignore
            }
            setcookie('owl_session', '', time() - 3600, '/');
        }

        session_destroy();
    }

    /**
     * Generate a CSRF token and store it in the session.
     *
     * @return string
     */
    public static function generateCsrfToken(): string
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
        return $_SESSION['csrf_token'];
    }

    /**
     * Validate a CSRF token submitted in a form.
     *
     * @param string $token  Token from $_POST['csrf_token'] (or equivalent).
     * @return bool
     */
    public static function validateCsrfToken(string $token): bool
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        $sessionToken = $_SESSION['csrf_token'] ?? '';
        return hash_equals($sessionToken, $token);
    }
}
