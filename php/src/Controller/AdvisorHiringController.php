<?php
declare(strict_types=1);

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

        // Load which ones this user has hired
        $stmt = $pdo->prepare("
            SELECT advisor_id, is_active, hired_at, paused_at, notes
            FROM user_advisors
            WHERE user_id = :uid
        ");
        $stmt->execute([':uid' => $userId]);
        $hired = [];
        foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
            $hired[(int)$row['advisor_id']] = $row;
        }

        // Process POST actions
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $action = $_POST['action'] ?? '';
            $advisorId = (int)($_POST['advisor_id'] ?? 0);

            if ($action === 'hire' && $advisorId > 0) {
                $stmt = $pdo->prepare("
                    INSERT IGNORE INTO user_advisors (user_id, advisor_id, notes)
                    VALUES (:uid, :aid, :notes)
                ");
                $stmt->execute([
                    ':uid' => $userId,
                    ':aid' => $advisorId,
                    ':notes' => $_POST['notes'] ?? '',
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
        ];
    }

    public function myAdvisors(): array
    {
        AuthController::requireAuth();
        $userId = (int)($_SESSION['user_id'] ?? 0);
        $pdo = Database::get();

        $stmt = $pdo->prepare("
            SELECT ua.id, ua.hired_at, ua.paused_at, ua.notes AS user_notes, ua.is_active,
                   a.slug, a.display_name, a.strategy, a.profile_json
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
