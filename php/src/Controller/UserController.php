<?php
/**
 * UserController — per-user settings and profile.
 */
class UserController {

    private $currentUser;

    public function __construct() {
        $this->currentUser = AuthController::requireAuth();
    }

    /**
     * GET /?action=my_dashboard — User's personalized dashboard.
     */
    public function myDashboard(): array {
        $this->currentUser = AuthController::requireAuth();
        $pdo = Database::get();
        $userId = $this->currentUser['id'];

        // Get user settings
        $settings = $this->getSettings($userId);

        // Get buy/sell recommendations for user's portfolio
        $recommendations = $this->getRecommendations($pdo, $userId);

        // Upcoming earnings for portfolio symbols
        $upcomingEarnings = $this->getUpcomingEarnings($pdo, $userId);

        // Dividend dates
        $dividendDates = $this->getDividendDates($pdo, $userId);

        // Top gainers/losers within portfolio
        $portfolioMovers = $this->getPortfolioMovers($pdo, $userId);

        // Data coverage: count symbols in portfolio with indicators
        $coverage = $this->getPortfolioCoverage($pdo, $userId);

        // Portfolio summary for My Dashboard
        $portfolioSummary = $this->getPortfolioSummary($pdo, $userId);

        return [
            'pageTitle' => 'My Dashboard',
            'template' => 'my_dashboard',
            'settings' => $settings,
            'recommendations' => $recommendations,
            'upcoming_earnings' => $upcomingEarnings,
            'dividend_dates' => $dividendDates,
            'portfolio_movers' => $portfolioMovers,
            'portfolio_summary' => $portfolioSummary,
            'coverage' => $coverage,
            'user' => $this->currentUser,
        ];
    }

    /**
     * GET/POST /?action=settings — User settings page.
     */
    public function settings(): array {
        $this->currentUser = AuthController::requireAuth();
        $pdo = Database::get();
        $userId = $this->currentUser['id'];
        $message = '';
        $error = '';

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            // Save settings
            $allowedSettings = [
                'color_scheme' => ['dark', 'darker', 'nord'],
                'font_size' => ['small', 'medium', 'large'],
                'compact_tables' => ['0', '1'],
                'show_sparks' => ['0', '1'],
                'decimal_places' => ['0','1','2','3','4'],
                'date_format' => ['Y-m-d','m/d/Y','d/m/Y'],
                'default_page' => ['overview','portfolio','my_dashboard'],
            ];

            foreach ($allowedSettings as $key => $allowed) {
                $val = $_POST[$key] ?? '';
                if (in_array($val, $allowed, true)) {
                    $stmt = $pdo->prepare("
                        INSERT INTO user_settings (user_id, setting_key, setting_value)
                        VALUES (:uid, :key, :val)
                        ON DUPLICATE KEY UPDATE setting_value = :val2
                    ");
                    $stmt->execute([':uid' => $userId, ':key' => $key, ':val' => $val, ':val2' => $val]);
                }
            }

            // Save sharing settings
            $shareGlobal = isset($_POST['share_global']) ? 1 : 0;
            $stmt = $pdo->prepare("
                INSERT INTO user_settings (user_id, setting_key, setting_value)
                VALUES (:uid, 'share_global', :val)
                ON DUPLICATE KEY UPDATE setting_value = :val2
            ");
            $stmt->execute([':uid' => $userId, ':val' => (string)$shareGlobal, ':val2' => (string)$shareGlobal]);

            $shareScope = in_array($_POST['share_scope'] ?? 'global', ['global','selected'], true) ? $_POST['share_scope'] : 'global';
            $stmt = $pdo->prepare("
                INSERT INTO user_settings (user_id, setting_key, setting_value)
                VALUES (:uid, 'share_scope', :val)
                ON DUPLICATE KEY UPDATE setting_value = :val2
            ");
            $stmt->execute([':uid' => $userId, ':val' => $shareScope, ':val2' => $shareScope]);

            // Sync visibility + designated shares
            if ($shareGlobal) {
                $pdo->prepare("
                    INSERT INTO portfolio_visibilities (user_id, is_public) VALUES (:uid, 1)
                    ON DUPLICATE KEY UPDATE is_public = 1
                ")->execute([':uid' => $userId]);
            } else {
                $pdo->prepare("
                    INSERT INTO portfolio_visibilities (user_id, is_public) VALUES (:uid, 0)
                    ON DUPLICATE KEY UPDATE is_public = 0
                ")->execute([':uid' => $userId]);
            }

            // Designated users
            $pdo->prepare("DELETE FROM portfolio_share_users WHERE user_id = :uid")->execute([':uid' => $userId]);
            if ($shareScope === 'selected' && !empty($_POST['shared_user_ids'])) {
                $ids = array_unique(array_map('intval', $_POST['shared_user_ids']));
                $stmt = $pdo->prepare("
                    INSERT INTO portfolio_share_users (user_id, shared_with_user_id) VALUES (:uid, :sid)
                ");
                foreach ($ids as $sid) {
                    if ($sid > 0 && $sid !== $userId) {
                        $stmt->execute([':uid' => $userId, ':sid' => $sid]);
                    }
                }
            }

            $message = 'Sharing settings saved.';

            // Handle password change
            $currentPw = $_POST['current_password'] ?? '';
            $newPw = $_POST['new_password'] ?? '';
            $newPw2 = $_POST['new_password_confirm'] ?? '';

            if ($currentPw || $newPw || $newPw2) {
                if (!$currentPw) {
                    $error = 'Current password is required to change password.';
                } elseif (strlen($newPw) < 8) {
                    $error = 'New password must be at least 8 characters.';
                } elseif ($newPw !== $newPw2) {
                    $error = 'New passwords do not match.';
                } else {
                    // Verify current password
                    $stmt = $pdo->prepare("SELECT password_hash FROM users WHERE id = :id");
                    $stmt->execute([':id' => $userId]);
                    $user = $stmt->fetch();
                    if (!password_verify($currentPw, $user['password_hash'])) {
                        $error = 'Current password is incorrect.';
                    } else {
                        $hash = password_hash($newPw, PASSWORD_DEFAULT);
                        $pdo->prepare("UPDATE users SET password_hash = :h WHERE id = :id")
                            ->execute([':h' => $hash, ':id' => $userId]);
                        $message = 'Settings saved and password updated.';
                    }
                }
            }

            if (!$error && !$message) {
                $message = 'Settings saved successfully.';
            }
        }

        $settings = $this->getSettings($userId);

        $allUsers = [];
        try {
            $stmt = $pdo->query("SELECT id, username, display_name, role FROM users WHERE is_active = 1 AND id != :me ORDER BY role DESC, username ASC");
            $stmt->execute([':me' => $userId]);
            $allUsers = $stmt->fetchAll();
        } catch (Exception $e) {}

        $sharedWithMe = [];
        try {
            $stmt = $pdo->prepare("
                SELECT u.id, u.username, u.display_name, u.role
                FROM portfolio_share_users psu
                JOIN users u ON u.id = psu.shared_with_user_id
                WHERE psu.user_id = :me
            ");
            $stmt->execute([':me' => $userId]);
            $sharedWithMe = $stmt->fetchAll();
        } catch (Exception $e) {}

        return [
            'pageTitle' => 'My Settings',
            'template' => 'settings',
            'settings' => $settings,
            'message' => $message,
            'error' => $error,
            'user' => $this->currentUser,
            'all_users' => $allUsers,
            'shared_with_me' => $sharedWithMe,
        ];
    }

    /**
     * Get all settings with defaults.
     */
    private function getSettings(int $userId): array {
        $defaults = [
            'color_scheme' => 'dark',
            'font_size' => 'medium',
            'compact_tables' => '0',
            'show_sparks' => '1',
            'decimal_places' => '2',
            'date_format' => 'Y-m-d',
            'default_page' => 'overview',
        ];

        try {
            $pdo = Database::get();
            $stmt = $pdo->prepare("SELECT setting_key, setting_value FROM user_settings WHERE user_id = :uid");
            $stmt->execute([':uid' => $userId]);
            while ($row = $stmt->fetch()) {
                $defaults[$row['setting_key']] = $row['setting_value'];
            }
        } catch (Exception $e) {}

        return $defaults;
    }

    /**
     * Get buy/sell recommendations for portfolio holdings.
     */
    private function getRecommendations(PDO $pdo, int $userId): array {
        $sql = "
            SELECT p.symbol, p.shares, p.cost_basis, p.trailing_stop_pct, p.stop_loss_pct,
                   p.strategy, p.atr_multiplier,
                   latest.close as current_price,
                   latest.price_date,
                   ind.data as indicators
            FROM portfolio p
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close, sp1.price_date
                FROM stockprices sp1
                INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) sp2
                    ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON COALESCE(p.price_symbol, p.symbol) = latest.symbol
            LEFT JOIN (
                SELECT i1.symbol, i1.data
                FROM indicators_json i1
                INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM indicators_json GROUP BY symbol) i2
                    ON i1.symbol = i2.symbol AND i1.price_date = i2.max_date
            ) ind ON COALESCE(p.price_symbol, p.symbol) = ind.symbol
            WHERE p.user_id = :uid AND p.shares > 0
            ORDER BY p.symbol
        ";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([':uid' => $userId]);
        $rows = $stmt->fetchAll();

        $recs = [];
        foreach ($rows as $r) {
            $price = $r['current_price'] ?? 0;
            $ind = json_decode($r['indicators'] ?? '{}', true);
            $rsi = $ind['rsi_14'] ?? 50;
            $macd = $ind['macd'] ?? 0;
            $sma50 = $ind['sma_50'] ?? 0;
            $sma200 = $ind['sma_200'] ?? 0;
            $atr14 = $ind['atr_14'] ?? 0;

            // Simple recommendation logic
            $score = 0;
            $reasons = [];

            if ($rsi < 30) { $score += 2; $reasons[] = 'RSI oversold (' . round($rsi, 1) . ')'; }
            elseif ($rsi > 70) { $score -= 2; $reasons[] = 'RSI overbought (' . round($rsi, 1) . ')'; }

            if ($macd > 0) { $score += 1; $reasons[] = 'MACD positive'; }
            else { $score -= 1; $reasons[] = 'MACD negative'; }

            if ($price > $sma50 && $sma50 > 0) { $score += 1; $reasons[] = 'Above SMA50'; }
            elseif ($price < $sma50 && $sma50 > 0) { $score -= 1; $reasons[] = 'Below SMA50'; }

            if ($price > $sma200 && $sma200 > 0) { $score += 1; $reasons[] = 'Above SMA200 (bullish)'; }
            elseif ($price < $sma200 && $sma200 > 0) { $score -= 1; $reasons[] = 'Below SMA200 (bearish)'; }

            // Trailing stop proximity
            $trailingStopPrice = $price * (1 - ($r['trailing_stop_pct'] ?? 0.10));
            if ($trailingStopPrice >= $price * 0.98) {
                $score -= 1;
                $reasons[] = 'Near trailing stop';
            }

            if ($score >= 2) $action = 'STRONG BUY';
            elseif ($score >= 1) $action = 'BUY';
            elseif ($score <= -2) $action = 'STRONG SELL';
            elseif ($score <= -1) $action = 'SELL';
            else $action = 'HOLD';

            $r['action'] = $action;
            $r['score'] = $score;
            $r['reasons'] = $reasons;
            $r['rsi'] = $rsi;
            $r['atr_14'] = $atr14;
            $recs[] = $r;
        }

        return $recs;
    }

    /**
     * Get upcoming earnings dates for portfolio symbols.
     */
    private function getUpcomingEarnings(PDO $pdo, int $userId): array {
        try {
            $stmt = $pdo->prepare("
                SELECT DISTINCT f.symbol, f.earnings_date, f.eps_estimate, f.revenue_estimate
                FROM fundamentals f
                INNER JOIN portfolio p ON f.symbol = COALESCE(p.price_symbol, p.symbol) AND p.user_id = :uid AND p.shares > 0
                INNER JOIN (
                    SELECT symbol, MAX(fetch_date) as max_date FROM fundamentals GROUP BY symbol
                ) latest ON f.symbol = latest.symbol AND f.fetch_date = latest.max_date
                WHERE f.earnings_date IS NOT NULL AND f.earnings_date >= CURDATE()
                ORDER BY f.earnings_date ASC
                LIMIT 20
            ");
            $stmt->execute([':uid' => $userId]);
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }

    /**
     * Get upcoming dividend dates for portfolio symbols.
     */
    private function getDividendDates(PDO $pdo, int $userId): array {
        try {
            $stmt = $pdo->prepare("
                SELECT DISTINCT f.symbol, f.dividend_rate, f.ex_dividend_date, f.dividend_yield
                FROM fundamentals f
                INNER JOIN portfolio p ON f.symbol = COALESCE(p.price_symbol, p.symbol) AND p.user_id = :uid AND p.shares > 0
                INNER JOIN (
                    SELECT symbol, MAX(fetch_date) as max_date FROM fundamentals GROUP BY symbol
                ) latest ON f.symbol = latest.symbol AND f.fetch_date = latest.max_date
                WHERE f.ex_dividend_date IS NOT NULL AND f.ex_dividend_date >= CURDATE()
                ORDER BY f.ex_dividend_date ASC
                LIMIT 20
            ");
            $stmt->execute([':uid' => $userId]);
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }

    /**
     * Get top gainers and losers within portfolio.
     */
    private function getPortfolioMovers(PDO $pdo, int $userId): array {
        $sql = "
            SELECT p.symbol,
                   latest.close as current_price,
                   latest.price_date as price_date,
                   prev.close as prev_close,
                   CASE WHEN prev.close > 0 THEN ((latest.close - prev.close) / prev.close) * 100 ELSE 0 END as change_pct
            FROM portfolio p
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close, sp1.price_date
                FROM stockprices sp1
                INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) sp2
                    ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON p.price_symbol = latest.symbol
            LEFT JOIN (
                SELECT sp3.symbol, sp3.close
                FROM stockprices sp3
                INNER JOIN (
                    SELECT symbol, MAX(price_date) as max_date
                    FROM stockprices
                    WHERE price_date < (SELECT MAX(price_date) FROM stockprices sp4 WHERE sp4.symbol = stockprices.symbol)
                    GROUP BY symbol
                ) sp4 ON sp3.symbol = sp4.symbol AND sp3.price_date = sp4.max_date
            ) prev ON p.price_symbol = prev.symbol
            WHERE p.user_id = :uid AND p.shares > 0 AND latest.price_date IS NOT NULL
            ORDER BY latest.price_date DESC,
                     CASE WHEN ((latest.close - prev.close) / prev.close) * 100 > 0
                          THEN ((latest.close - prev.close) / prev.close) * 100
                          ELSE 0 END DESC
        ";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([':uid' => $userId]);
        $rows = $stmt->fetchAll();

        // Filter: only consider symbols from the most recent price date
        $latestDate = null;
        $recentRows = [];
        foreach ($rows as $r) {
            if ($latestDate === null) {
                $latestDate = $r['price_date'];
            }
            if ($r['price_date'] === $latestDate) {
                $recentRows[] = $r;
            }
        }

        $gainers = array_filter($recentRows, fn($r) => ($r['change_pct'] ?? 0) > 0);
        $losers = array_filter($recentRows, fn($r) => ($r['change_pct'] ?? 0) < 0);

        return [
            'gainers' => array_slice($gainers, 0, 5),
            'losers' => array_slice($losers, 0, 5),
        ];
    }

    /**
     * Get data coverage stats for portfolio symbols.
     */
    private function getPortfolioCoverage(PDO $pdo, int $userId): array {
        $stmt = $pdo->prepare("SELECT COUNT(DISTINCT symbol) FROM portfolio WHERE user_id = :uid AND shares > 0");
        $stmt->execute([':uid' => $userId]);
        $totalSymbols = $stmt->fetchColumn();

        $stmt = $pdo->prepare("
            SELECT COUNT(DISTINCT COALESCE(p.price_symbol, p.symbol)) FROM portfolio p
            LEFT JOIN stockprices sp ON COALESCE(p.price_symbol, p.symbol) = sp.symbol
            WHERE p.user_id = :uid AND p.shares > 0
        ");
        $stmt->execute([':uid' => $userId]);
        $withPrices = $stmt->fetchColumn();

        $stmt = $pdo->prepare("
            SELECT COUNT(DISTINCT COALESCE(p.price_symbol, p.symbol)) FROM portfolio p
            LEFT JOIN indicators_json ij ON COALESCE(p.price_symbol, p.symbol) = ij.symbol
            WHERE p.user_id = :uid AND p.shares > 0
        ");
        $stmt->execute([':uid' => $userId]);
        $withIndicators = $stmt->fetchColumn();

        $stmt = $pdo->prepare("
            SELECT COUNT(*) FROM stockprices sp
            LEFT JOIN portfolio p ON COALESCE(p.price_symbol, p.symbol) = sp.symbol
            WHERE p.user_id = :uid AND p.shares > 0
        ");
        $stmt->execute([':uid' => $userId]);
        $totalRows = $stmt->fetchColumn();

        return [
            'total' => $totalSymbols,
            'with_prices' => $withPrices,
            'with_indicators' => $withIndicators,
            'total_rows' => $totalRows,
        ];
    }

    /**
     * Get portfolio summary for My Dashboard.
     */
    private function getPortfolioSummary(PDO $pdo, int $userId): ?array {
        $stmt = $pdo->prepare("
            SELECT p.symbol, p.shares, p.cost_basis, p.account_type,
                   latest.close as current_price,
                   latest.price_date
            FROM portfolio p
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close, sp1.price_date
                FROM stockprices sp1
                INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) sp2
                    ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON COALESCE(p.price_symbol, p.symbol) = latest.symbol
            WHERE p.user_id = :uid AND p.shares > 0
            ORDER BY p.symbol
        ");
        $stmt->execute([':uid' => $userId]);
        $holdings = $stmt->fetchAll();

        if (empty($holdings)) return null;

        $totalCost = 0;
        $totalValue = 0;
        $topPnlPct = -999;
        $worstPnlPct = 999;

        foreach ($holdings as $h) {
            $cost = $h['shares'] * $h['cost_basis'];
            $value = $h['shares'] * ($h['current_price'] ?? 0);
            $totalCost += $cost;
            $totalValue += $value;
            $pnlPct = $cost > 0 ? (($value - $cost) / $cost) * 100 : 0;
            if ($pnlPct > $topPnlPct) $topPnlPct = $pnlPct;
            if ($pnlPct < $worstPnlPct) $worstPnlPct = $pnlPct;
        }

        return [
            'market_value' => $totalValue,
            'cost_basis' => $totalCost,
            'pnl' => $totalValue - $totalCost,
            'pnl_pct' => $totalCost > 0 ? (($totalValue - $totalCost) / $totalCost) * 100 : 0,
            'num_holdings' => count($holdings),
            'top_pnl_pct' => $topPnlPct,
            'worst_pnl_pct' => $worstPnlPct,
        ];
    }
}
