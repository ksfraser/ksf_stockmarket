<?php
/**
 * AuthController — handles login, logout, registration, and session management.
 */
class AuthController {

    /**
     * Check if a valid session exists. Returns user array or null.
     */
    public static function checkSession(): ?array {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }

        // Check PHP session
        if (!empty($_SESSION['user_id'])) {
            return $_SESSION['user'] ?? null;
        }

        // Check remember-me cookie
        if (!empty($_COOKIE['owl_session'])) {
            try {
                $pdo = Database::get();
                $stmt = $pdo->prepare("
                    SELECT s.user_id, s.expires_at, u.username, u.email, u.display_name, u.role, u.is_active
                    FROM user_sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.id = :sid AND s.expires_at > NOW() AND u.is_active = 1
                ");
                $stmt->execute([':sid' => $_COOKIE['owl_session']]);
                $row = $stmt->fetch();
                if ($row) {
                    $_SESSION['user_id'] = $row['user_id'];
                    $_SESSION['user'] = $row;
                    return $row;
                }
            } catch (Exception $e) {
                // Silently fail
            }
        }

        return null;
    }

    /**
     * Require authenticated user. Redirects to login if not authenticated.
     */
    public static function requireAuth(): array {
        $user = self::checkSession();
        if (!$user) {
            $_SESSION['redirect_after_login'] = $_SERVER['REQUEST_URI'];
            header('Location: ?action=login');
            exit;
        }
        return $user;
    }

    /**
     * GET/POST /?action=login
     */
    public function login(): array {
        $error = '';

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $username = trim($_POST['username'] ?? '');
            $password = $_POST['password'] ?? '';
            $remember = !empty($_POST['remember']);

            try {
                $pdo = Database::get();
                $stmt = $pdo->prepare("SELECT * FROM users WHERE username = :u AND is_active = 1");
                $stmt->execute([':u' => $username]);
                $user = $stmt->fetch();

                if ($user && password_verify($password, $user['password_hash'])) {
                    // Login successful
                    if (session_status() === PHP_SESSION_NONE) session_start();
                    $_SESSION['user_id'] = $user['id'];
                    $_SESSION['user'] = $user;

                    // Update last login
                    $pdo->prepare("UPDATE users SET last_login = NOW() WHERE id = :id")
                        ->execute([':id' => $user['id']]);

                    // Remember me
                    if ($remember) {
                        $sid = bin2hex(random_bytes(64));
                        $expires = date('Y-m-d H:i:s', strtotime('+30 days'));
                        $pdo->prepare("INSERT INTO user_sessions (id, user_id, ip_address, user_agent, expires_at) VALUES (:sid, :uid, :ip, :ua, :exp)")
                            ->execute([
                                ':sid' => $sid,
                                ':uid' => $user['id'],
                                ':ip' => $_SERVER['REMOTE_ADDR'] ?? '',
                                ':ua' => $_SERVER['HTTP_USER_AGENT'] ?? '',
                                ':exp' => $expires,
                            ]);
                        setcookie('owl_session', $sid, strtotime('+30 days'), '/', '', false, true);
                    }

                    // Redirect
                    $redirect = $_SESSION['redirect_after_login'] ?? '?action=overview';
                    unset($_SESSION['redirect_after_login']);
                    header("Location: $redirect");
                    exit;
                } else {
                    $error = 'Invalid username or password.';
                }
            } catch (Exception $e) {
                $error = 'Login error. Please try again.';
            }
        }

        // Return template data
        return ['error' => $error, 'pageTitle' => 'Login', 'template' => 'login'];
    }

    /**
     * GET /?action=logout
     */
    public function logout(): void {
        if (session_status() === PHP_SESSION_NONE) session_start();

        // Remove remember-me cookie
        if (!empty($_COOKIE['owl_session'])) {
            try {
                $pdo = Database::get();
                $pdo->prepare("DELETE FROM user_sessions WHERE id = :sid")
                    ->execute([':sid' => $_COOKIE['owl_session']]);
            } catch (Exception $e) {}
            setcookie('owl_session', '', time() - 3600, '/');
        }

        session_destroy();
        header('Location: ?action=login');
        exit;
    }

    /**
     * GET/POST /?action=register
     */
    public function register(): array {
        $error = '';
        $success = '';

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $username = trim($_POST['username'] ?? '');
            $email = trim($_POST['email'] ?? '');
            $password = $_POST['password'] ?? '';
            $password2 = $_POST['password2'] ?? '';

            // Validation
            if (strlen($username) < 3) {
                $error = 'Username must be at least 3 characters.';
            } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
                $error = 'Please enter a valid email address.';
            } elseif (strlen($password) < 8) {
                $error = 'Password must be at least 8 characters.';
            } elseif ($password !== $password2) {
                $error = 'Passwords do not match.';
            } else {
                try {
                    $pdo = Database::get();
                    $hash = password_hash($password, PASSWORD_DEFAULT);
                    $stmt = $pdo->prepare("INSERT INTO users (username, email, password_hash, display_name) VALUES (?, ?, ?, ?)");
                    $stmt->execute([$username, $email, $hash, $username]);
                    $success = 'Account created! You can now log in.';
                } catch (PDOException $e) {
                    if ($e->getCode() == 23000) {
                        $error = 'Username or email already exists.';
                    } else {
                        $error = 'Registration error. Please try again.';
                    }
                }
            }
        }

        return compact('error', 'success', 'pageTitle', 'template');
    }
}
