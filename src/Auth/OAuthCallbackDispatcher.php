<?php

/**
 * OAuth callback dispatcher — included from index.php for ?action=oauth-callback.
 *
 * This file is require_once'd directly by index.php (not via the controller
 * autoload) so it can run before the controller autoloading kicks in.
 */
require_once __DIR__ . '/Auth/AuthServiceProvider.php';
require_once __DIR__ . '/Auth/SessionHelper.php';

$providerName = $_GET['provider'] ?? $_POST['provider'] ?? '';

// Fallback: if provider was stashed in session during the redirect.
if ($providerName === '') {
    $providerName = $_SESSION['pending_provider'] ?? '';
}

if ($providerName === '') {
    $_SESSION['auth_error'] = 'No authentication provider specified.';
    header('Location: ?action=login');
    exit;
}

try {
    $manager = \Ksf\StockMarket\Auth\AuthServiceProvider::createManager();
    $provider = $manager->getProvider($providerName);

    if ($provider === null || !$provider->isAvailable()) {
        throw new \Ksf\StockMarket\Auth\AuthProviderException("Provider unavailable: $providerName");
    }

    // Collect callback data (OAuth2 returns to us via GET query params).
    $callbackData = $_GET;

    $user = $manager->handleCallback($providerName, $callbackData);

    // Log the user in.
    SessionHelper::loginSuccess($user, false);

    // Clear the pending provider from session.
    unset($_SESSION['pending_provider']);

    // Redirect to the stored destination or default.
    $redirect = $_SESSION['redirect_after_login'] ?? '?action=overview';
    unset($_SESSION['redirect_after_login']);

    header("Location: $redirect");
    exit;

} catch (\Ksf\StockMarket\Auth\AuthProviderException $e) {
    $_SESSION['auth_error'] = $e->getMessage();
    error_log('[Auth] OAuth callback error for ' . $providerName . ': ' . $e->getMessage());
    header('Location: ?action=login');
    exit;

} catch (\Exception $e) {
    $_SESSION['auth_error'] = 'Authentication failed. Please try again.';
    error_log('[Auth] OAuth callback exception for ' . $providerName . ': ' . $e->getMessage());
    header('Location: ?action=login');
    exit;
}
