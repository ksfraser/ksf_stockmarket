<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Security\Voter;

use Symfony\Component\Security\Core\Authorization\Voter\Voter;
use Symfony\Component\Security\Core\Authentication\Token\TokenInterface;
use Symfony\Component\Security\Core\User\UserInterface;

/**
 * ActionVoter - dispatches access decisions based on the ?action= query param.
 *
 * Symfony's access_control matches against the REQUEST URI path, but this app
 * routes everything through ?action=XXX (the URI is always / or /index.php).
 * This voter inspects $_GET['action'] and votes accordingly.
 */
class ActionVoter extends Voter
{
    public const ATTRIBUTE = 'action';

    /** Actions anyone can access (no auth required). */
    private const PUBLIC_ACTIONS = [
        'login',
        'logout',
        'register',
        'oauth-redirect',
        'oauth-callback',
        'forgot-password',
        'reset-password',
        'reset-password-success',
        'api_chart',
        'api_screener',
    ];

    /** Actions that require ROLE_ADMIN. */
    private const ADMIN_ACTIONS = [
        'admin_settings',
        'admin_setup_wizard',
    ];

    protected function supports(string $attribute, mixed $subject): bool
    {
        return $attribute === self::ATTRIBUTE;
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        if ($attribute !== self::ATTRIBUTE) {
            return self::ACCESS_ABSTAIN;
        }

        $action = $_GET['action'] ?? 'overview';

        if (in_array($action, self::PUBLIC_ACTIONS, true)) {
            return true;
        }

        if (in_array($action, self::ADMIN_ACTIONS, true)) {
            $user = $token->getUser();
            if ($user === null || !$token->isAuthenticated()) {
                return false;
            }
            if (!($user instanceof UserInterface)) {
                return false;
            }
            return $user->isGranted('ROLE_ADMIN');
        }

        $user = $token->getUser();
        return $user !== null && $token->isAuthenticated();
    }
}
