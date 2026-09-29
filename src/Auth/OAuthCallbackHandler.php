<?php

/**
 * OAuth callback handler — dispatched from index.php when
 * ?action=oauth-callback&provider=<name> is requested.
 *
 * Flow:
 *   1. Load the AuthManager (with all registered providers).
 *   2. Delegate to the matching provider's handleCallback().
 *   3. On success, log the user in via SessionHelper and redirect to overview.
 *   4. On failure, redirect back to login with an error message.
 */
require_once __DIR__ . '/Auth/AuthServiceProvider.php';
require_once __DIR__ . '/Auth/SessionHelper.php';

// The provider name is passed as a query parameter.
$providerName = $_GET['provider'] ?? '';

if ($providerName === '') {
    // No provider specified — bounce to login.
    header('Location: ?action=login');
    exit;
}

try {
    $manager = \Ksf\StockMarket\Auth\AuthServiceProvider::createManager();
    $provider = $manager->getProvider($providerName);

    if ($provider === null) {
        throw new \Exception("Unknown auth provider: $providerName");
    }

    // Collect callback data from GET (OAuth2 authorization code flow uses GET).
    $callbackData = $_GET;

    $user = $manager->handleCallback($providerName, $callbackData);

    // Log the user in.
    SessionHelper::loginSuccess($user, !empty($_POST['remember']));

    // Redirect to the stored destination or default to overview.
    $redirect = $_SESSION['redirect_after_login'] ?? '?action=overview';
    unset($_SESSION['redirect_after_login']);

    header("Location: $redirect");
    exit;

} catch (\Ksf\StockMarket\Auth\AuthProviderException $e) {
    // Auth provider errors (invalid code, network error, etc.) — show on login page.
    $_SESSION['auth_error'] = $e->getMessage();
    header('Location: ?action=login');
    exit;

} catch (\Exception $e) {
    $_SESSION['auth_error'] = 'Authentication failed. Please try again.';
    error_log('[Auth] OAuth callback error for ' . $providerName . ': ' . $e->getMessage());
    header('Location: ?action=login');
    exit;
}
