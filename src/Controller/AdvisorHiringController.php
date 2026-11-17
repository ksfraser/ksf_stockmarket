<?php
declare(strict_types=1);

namespace ksfraser\StockMarket\Controller;

use ksfraser\StockMarket\Model\Database;
use ksfraser\StockMarket\Strategy\StrategyFactory;
use App\Strategy\StrategyRegistry;


class AdvisorHiringController
{
    public function index(): array
    {
        AuthController::requireAuth();
        $userId = (int)($_SESSION['user_id'] ?? 0);

        $pdo = Database::get();

        // Load all active advisors
        $stmt = $pdo->query("
            SELECT a.id, a.slug, a.display_name, a.strategy, a.profile_json, a.is_active
            FROM advisor_accounts a
            ORDER BY a.display_name ASC
        ");
        $advisors = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // Load which ones this user has hired, including new columns
        $stmt = $pdo->prepare("
            SELECT advisor_id, is_active, hired_at, paused_at, notes,
                   linked_screen_ids, strategy_rules, money_management
            FROM user_advisors
            WHERE user_id = :uid
        ");
        $stmt->execute([':uid' => $userId]);
        $hired = [];
        foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
            $hired[(int)$row['advisor_id']] = $row;
        }

        // Load screens for linking
        $stmt = $pdo->query("
            SELECT id, name, category
            FROM user_screens
            WHERE universe = 'stocks' AND is_deleted = 0
            ORDER BY name ASC
        ");
        $allScreens = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // Load strategies for selection
        $registry = StrategyFactory::create();
        $allStrategies = $registry->all();

        // Process POST actions
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $action = $_POST['action'] ?? '';
            $advisorId = (int)($_POST['advisor_id'] ?? 0);

            if ($action === 'hire' && $advisorId > 0) {
                $linked = isset($_POST['linked_screen_ids']) && is_array($_POST['linked_screen_ids'])
                    ? implode(',', array_map('intval', $_POST['linked_screen_ids'])) : null;
                $strategyRules = !empty($_POST['strategy_rules']) ? json_encode($_POST['strategy_rules']) : null;
                $moneyMgmt = !empty($_POST['money_management']) ? json_encode($_POST['money_management']) : null;

                $stmt = $pdo->prepare("
                    INSERT IGNORE INTO user_advisors
                        (user_id, advisor_id, notes, linked_screen_ids, strategy_rules, money_management)
                    VALUES (:uid, :aid, :notes, :screens, :strat, :money)
                ");
                $stmt->execute([
                    ':uid' => $userId,
                    ':aid' => $advisorId,
                    ':notes' => $_POST['notes'] ?? '',
                    ':screens' => $linked,
                    ':strat' => $strategyRules,
                    ':money' => $moneyMgmt,
                ]);
            } elseif ($action === 'configure' && $advisorId > 0 && !empty($hired[$advisorId])) {
                $linked = isset($_POST['linked_screen_ids']) && is_array($_POST['linked_screen_ids'])
                    ? implode(',', array_map('intval', $_POST['linked_screen_ids'])) : null;
                $strategyRules = !empty($_POST['strategy_rules']) ? json_encode($_POST['strategy_rules']) : null;
                $moneyMgmt = !empty($_POST['money_management']) ? json_encode($_POST['money_management']) : null;

                $pdo->prepare("
                    UPDATE user_advisors
                    SET notes = :notes,
                        linked_screen_ids = :screens,
                        strategy_rules = :strat,
                        money_management = :money
                    WHERE user_id = :uid AND advisor_id = :aid
                ")->execute([
                    ':notes' => $_POST['notes'] ?? '',
                    ':screens' => $linked,
                    ':strat' => $strategyRules,
                    ':money' => $moneyMgmt,
                    ':uid' => $userId,
                    ':aid' => $advisorId,
                ]);
            } elseif ($action === 'pause' && $advisorId > 0 && !empty($hired[$advisorId])) {
                $pdo->prepare("
                    UPDATE user_advisors SET is_active = 0, paused_at = NOW()
                    WHERE user_id = :uid AND advisor_id = :aid
                ")->execute([':uid' => $userId, ':aid' => $advisorId]);
            } elseif ($action === 'resume' && $advisorId > 0 && !empty($hired[$advisorId])) {
                $pdo->prepare("
                    UPDATE user_advisors SET is_active = 1, paused_at = NULL
                    WHERE user_id = :uid AND advisor_id = :aid
                ")->execute([':uid' => $userId, ':aid' => $advisorId]);
            } elseif ($action === 'fire' && $advisorId > 0 && !empty($hired[$advisorId])) {
                $pdo->prepare("
                    DELETE FROM user_advisors
                    WHERE user_id = :uid AND advisor_id = :aid
                ")->execute([':uid' => $userId, ':aid' => $advisorId]);
            }

            header('Location: ?action=hire_advisors');
            exit;
        }

        return [
            'advisors' => $advisors,
            'hired' => $hired,
            'all_screens' => $allScreens,
            'all_strategies' => $allStrategies,
        ];
    }

    /**
     * POST /?action=generate_advisor_portfolios
     * Trigger portfolio generation for all active hired advisors.
     */
    public function generatePortfolios(): array
    {
        AuthController::requireAuth();
        $userId = (int)($_SESSION['user_id'] ?? 0);

        $service = new \ksfraser\StockMarket\Service\AdvisorPortfolioService();
        $result = $service->generateForUser($userId);

        return [
            'pageTitle' => 'Generate Advisor Portfolios',
            'template' => 'generate_advisor_portfolios',
            'result' => $result,
        ];
    }

    public function myAdvisors(): array
    {
        AuthController::requireAuth();
        $userId = (int)($_SESSION['user_id'] ?? 0);
        $pdo = Database::get();

        $stmt = $pdo->prepare("
            SELECT ua.id, ua.hired_at, ua.paused_at, ua.notes AS user_notes, ua.is_active,
                   a.slug, a.display_name, a.strategy, a.profile_json,
                   ua.linked_screen_ids, ua.strategy_rules, ua.money_management
            FROM user_advisors ua
            JOIN advisor_accounts a ON a.id = ua.advisor_id
            WHERE ua.user_id = :uid
            ORDER BY ua.is_active DESC, ua.hired_at DESC
        ");
        $stmt->execute([':uid' => $userId]);
        $my = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // Load recent advisor trades for this user
        $stmt = $pdo->prepare("
            SELECT t.id, t.symbol, t.trade_date, t.type, t.quantity, t.price, t.total, t.commission, t.notes, t.created_at,
                   a.display_name AS advisor_name, a.slug AS advisor_slug
            FROM transactions t
            JOIN advisor_accounts a ON a.id = t.advisor_id
            WHERE t.user_id = :uid AND t.source_file = 'advisor'
            ORDER BY t.trade_date DESC, t.id DESC
            LIMIT 100
        ");
        $stmt->execute([':uid' => $userId]);
        $trades = $stmt->fetchAll(PDO::FETCH_ASSOC);

        return [
            'advisors' => $my,
            'trades' => $trades,
        ];
    }
}
