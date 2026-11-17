# Auth Package Migration Plan — StockMarket App

Status: Planned (not started). Reset-flow fixes delivered first (DB columns + Symfony Mailer + admin UI).
Target: Battle-tested Symfony Security + supporting packages.
Charset: Latin (English only).

## Target packages

- symfony/security-bundle (v6.4 or v7.4) — authentication, authorization, firewall, access_control, voters, role hierarchy.
- symfony/security-csrf — replaces SessionHelper CSRF tokens.
- symfony/security-core — user providers, password encoders, authentication tokens.
- (Keep) symfony/mailer v6.4 — already installed for reset emails; stays.

Why these over alternatives:
- laravel/ui or laravel/passport: Laravel framework required; current app is vanilla PHP + Twig, not Laravel.
- lcobucci/jwt: Good for API tokens only; does not provide form login, session firewall, or RBAC out of the box.
- Custom AuthManager: Already working but unmaintained; Symfony Security is actively maintained, audited, and used at scale.

## Compatibility assessment

Current environment: PHP 8.1, Twig 3, Monolog 3, PDO MariaDB, custom AuthManager (provider registry), session-based auth, OAuth providers (Google, Facebook, LDAP, OIDC), Argon2id password hashes, custom User model.

Compatible:
- PHP 8.1 matches Symfony 6.4/7.4 requirements.
- Twig templates work unchanged (Symfony Security does not enforce a view engine).
- Existing users DB schema works with Symfony's `entity` user provider or a custom `chain` provider.
- Argon2id hashes work with Symfony `NativePasswordHasher` (auto-detects algorithm, supports migration).

Requires adapter work:
- AuthServiceProvider (custom provider registry) must be replaced or wrapped as a Symfony `UserProviderInterface`.
- AuthController session checks must be replaced with Symfony `security: firewalls:` + `access_control:`.
- OAuth callback dispatcher (OAuthCallbackDispatcher.php) needs to align with Symfony's `security: authenticators:`.
- Admin role check (`$this->currentUser['role'] === 'admin'`) should become Symfony role `ROLE_ADMIN` + voter checks.

## Migration phases (recommended order)

Phase 1 — Install + firewall config (low risk, high value)
1. `composer require symfony/security-bundle symfony/security-csrf symfony/security-core`
2. Create `config/packages/security.yaml`:
   - `encoders: Symfony\Component\Security\Core\User\PasswordAuthenticatedUserInterface: 'native'`
   - `providers: app_user_provider` (PDO / entity adapter pointing to current `users` table)
   - `firewalls: main:` form_login, logout, anonymous, csrf: true
   - `access_control:` protected routes (`portfolio`, `transactions`, `admin_settings`, etc.) require `ROLE_USER`; admin routes require `ROLE_ADMIN`

Phase 2 — User provider adapter (medium risk)
3. Implement or configure a `UserProviderInterface` adapter that reads from `users` table (`username`, `email`, `password_hash`, `role`, `is_active`).
4. Adapt `User.php` (or create Symfony `User` entity/class) to implement `Symfony\Component\Security\Core\User\UserInterface` and `PasswordAuthenticatedUserInterface`.
5. Verify `NativePasswordHasher` verifies existing Argon2id hashes (`password_hash` column, length 255, already compatible).

Phase 3 — Auth controller replacement (medium risk)
6. Replace `AuthController::checkSession()` with Symfony `Security::getUser()` or `#[CurrentUser]` controller arguments.
7. Replace custom session login/logout with Symfony firewall form_login/logout handlers.
8. Keep `register()` action but delegate password hashing to Symfony `UserPasswordHasherInterface` (replaces `password_hash()` call).

Phase 4 — OAuth providers (medium risk)
9. Evaluate knpuniversity/oauth2-client-bundle or Symfony's built-in OAuth authenticators.
10. Migrate `GoogleProvider.php`, `FacebookProvider.php`, `LDAPProvider.php`, `GenericOIDCProvider.php` to Symfony authenticator interfaces (`AbstractAuthenticator`, `Passport`, badges).
11. Update `OAuthCallbackDispatcher.php` to align with Symfony `security: custom_authenticators:`.

Phase 5 — RBAC + admin controls (low-medium risk)
12. Replace hard-coded role checks (`=== 'admin'`) with Symfony `ROLE_ADMIN`, `ROLE_USER`, `ROLE_VIEWER`, `ROLE_ADVISOR`.
13. Implement Symfony voters (`UserVoter`, `AdminVoter`) for fine-grained authorization (e.g., can reset user passwords only if admin + target user is not self).
14. Update `AdminSettingsController` to use `Security::isGranted('ROLE_ADMIN')` instead of manual `role` string check.

Phase 6 — CSRF + form security (low risk)
15. Replace `SessionHelper::generateCsrfToken()` with Symfony `CsrfTokenManager`.
16. Update all POST forms (`login.php`, `forgot_password.php`, `reset_password.php`, `register.php`, `admin_settings.php`) to include Symfony CSRF tokens.

Phase 7 — Testing + rollback plan
17. Unit tests: user provider adapter, password verification with existing hashes, role-based access.
18. Integration tests: login flow, forgot-password flow, admin reset, protected routes blocked for anonymous.
19. Rollback: keep `src/Auth/` directory intact until Phase 7 passes; rollback = revert `security.yaml` and restore `AuthController` session logic.

## What stays the same (does not change)

- Database: `users` table columns (`id`, `username`, `email`, `password_hash`, `display_name`, `role`, `is_active`, `created_at`, `last_login`, `password_reset_token`, `password_reset_expires_at`) remain unchanged.
- Templates: Twig `.php` files (login, forgot_password, reset_password, admin_settings) stay in `templates/`.
- Routes: `index.php` route definitions (`?action=login`, `?action=reset-password`, etc.) stay intact; Symfony Security firewall handles authorization independently of route names.
- Email delivery: Symfony Mailer (installed) remains; reset email flow in `User.php` stays.
- Non-auth features: portfolio, transactions, price refresh, analysis modules unchanged.

## Risk notes

- Custom `AuthServiceProvider` registry is the biggest adapter task. It must be mapped to `UserProviderInterface` implementations (one per provider: local DB, OAuth callbacks).
- OAuth callbacks (Google/Facebook) rely on external redirect URLs. Changing the auth mechanism may invalidate active OAuth tokens; test with a new OAuth flow after migration.
- Memory: user emphasized comparing news/numbers/reasonableness to catch bugs. Apply this to auth: compare before/after session state (is user logged in? is role correct?) after each phase.

## Deliverables completed in this session

- [x] DB migration applied (`password_reset_token`, `password_reset_expires_at`).
- [x] Symfony Mailer (`symfony/mailer` v6.4.46) installed + wired into `User.php::requestPasswordReset()`.
- [x] `reset_password_success.php` template verified present.
- [x] Admin user-management tab built (`AdminSettingsController` + `admin_settings.php`).
- [x] Migration SQL saved at `sql/migrations/2026-09-25_add_password_reset_token.sql`.
- [x] Auth package migration plan written (this file).

Next action (user decision required): Approve Phase 1 (`composer require symfony/security-bundle`) or hold.
