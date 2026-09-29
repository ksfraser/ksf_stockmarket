<?php

require_once __DIR__ . '/src/Security/AuthStatus.php';

// Compatibility shim: AuthController::checkSession() delegates to Symfony Security.
// Drop-in replacement so AuthController::requireAuth() still works during migration.
//
// Once all callers are migrated to AuthStatus::isAuthenticated() / AuthStatus::getCurrentUser(),
// this shim can be removed.
if (!function_exists('Ksf\StockMarket\Auth\SessionHelper_checkSessionAsArray')) {
    /**
     * @return array<string, mixed>|null
     */
    function Ksf_StockMarket_Auth_checkSessionAsArray(): ?array
    {
        return \Ksf\StockMarket\Security\AuthStatus::getCurrentUser();
    }
}
