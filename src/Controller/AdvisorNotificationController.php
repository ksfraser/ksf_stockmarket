<?php
declare(strict_types=1);

class AdvisorNotificationController
{
    public function preferences(): array
    {
        $user = AuthController::requireAuth();
        $pdo = Database::get();
        $userId = (int)$user['id'];

        // Load user_settings into a flat map
        $stmt = $pdo->prepare("SELECT setting_key, setting_value FROM user_settings WHERE user_id = :uid");
        $stmt->execute([':uid' => $userId]);
        $prefs = [];
        foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $r) {
            $prefs[$r['setting_key']] = $r['setting_value'];
        }

        // Load email
        $prefs['email'] = $user['email'] ?? '';

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $allowed = [
                'advisor_notify_email', 'advisor_notify_discord_dm',
                'advisor_notify_discord_channel', 'advisor_notify_whatsapp',
                'advisor_discord_user_id', 'advisor_discord_channel_id',
                'advisor_whatsapp_number', 'email',
            ];
            $updates = [];
            foreach ($allowed as $key) {
                if ($key === 'email') {
                    continue;
                }
                $val = $_POST[$key] ?? '';
                $updates[] = [$key, $val];
            }
            if (!empty($_POST['email']) && filter_var($_POST['email'], FILTER_VALIDATE_EMAIL)) {
                $stmt = $pdo->prepare("UPDATE users SET email = :e WHERE id = :uid");
                $stmt->execute([':e' => $_POST['email'], ':uid' => $userId]);
            }
            // batch upsert user_settings
            $stmtUpsert = $pdo->prepare("
                INSERT INTO user_settings (user_id, setting_key, setting_value)
                VALUES (:uid, :k, :v)
                ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            ");
            foreach ($updates as [$k, $v]) {
                $stmtUpsert->execute([':uid' => $userId, ':k' => $k, ':v' => $v]);
            }
            $_SESSION['flash_message'] = 'Notification preferences saved.';
            header('Location: ?action=advisor_preferences');
            exit;
        }

        return [
            'pageTitle' => 'Advisor Notification Preferences',
            'template' => 'notification_preferences',
            'prefs' => $prefs,
            'user' => $user,
        ];
    }

    public function myRecommendations(): array
    {
        $user = AuthController::requireAuth();
        $userId = (int)$user['id'];
        $pdo = Database::get();

        $stmt = $pdo->prepare("
            SELECT r.*, a.display_name AS advisor_name, a.slug AS advisor_slug
            FROM advisor_recommendations r
            JOIN advisor_accounts a ON a.id = r.advisor_id
            WHERE r.user_id = :uid
            ORDER BY r.recommended_at DESC
            LIMIT 100
        ");
        $stmt->execute([':uid' => $userId]);
        $recommendations = $stmt->fetchAll(PDO::FETCH_ASSOC);

        return [
            'pageTitle' => 'My Advisor Recommendations',
            'template' => 'my_recommendations',
            'recommendations' => $recommendations,
            'user' => $user,
        ];
    }
}
