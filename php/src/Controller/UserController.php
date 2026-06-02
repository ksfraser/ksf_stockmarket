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
        $recommendations = $this->getRecommendations($pdo);

        // Upcoming earnings for portfolio symbols
        $upcomingEarnings = $this->getUpcomingEarnings($pdo);

        // Dividend dates
        $dividendDates = $this->getDividendDates($pdo);

        // Top gainers/losers within portfolio
        $portfolioMovers = $this->getPortfolioMovers($pdo);

        // Data coverage: count symbols in portfolio with indicators
        $coverage = $this->getPortfolioCoverage($pdo);

        return [
            'pageTitle' => 'My Dashboard',
            'template' => 'my_dashboard',
            'settings' => $settings,
            'recommendations' => $recommendations,
            'upcoming_earnings' => $upcomingEarnings,
            'dividend_dates' => $dividendDates,
            'portfolio_movers' => $portfolioMovers,
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

        return [
            'pageTitle' => 'My Settings',
            'template' => 'settings',
            'settings' => $settings,
            'message' => $message,
            'error' => $error,
            'user' => $this->currentUser,
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
    private function getRecommendations(PDO $pdo): array {
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
            ) latest ON p.symbol = latest.symbol
            LEFT JOIN (
                SELECT i1.symbol, i1.data
                FROM indicators_json i1
                INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM indicators_json GROUP BY symbol) i2
                    ON i1.symbol = i2.symbol AND i1.price_date = i2.max_date
            ) ind ON p.symbol = ind.symbol
            ORDER BY p.symbol
        ";
        $rows = $pdo->query($sql)->fetchAll();

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
    private function getUpcomingEarnings(PDO $pdo): array {
        try {
            $stmt = $pdo->query("
                SELECT DISTINCT f.symbol, f.earnings_date, f.eps_estimate, f.revenue_estimate
                FROM fundamentals f
                INNER JOIN portfolio p ON f.symbol = p.symbol
                INNER JOIN (
                    SELECT symbol, MAX(fetch_date) as max_date FROM fundamentals GROUP BY symbol
                ) latest ON f.symbol = latest.symbol AND f.fetch_date = latest.max_date
                WHERE f.earnings_date IS NOT NULL AND f.earnings_date >= CURDATE()
                ORDER BY f.earnings_date ASC
                LIMIT 20
            ");
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }

    /**
     * Get upcoming dividend dates for portfolio symbols.
     */
    private function getDividendDates(PDO $pdo): array {
        try {
            $stmt = $pdo->query("
                SELECT DISTINCT f.symbol, f.dividend_rate, f.ex_dividend_date, f.dividend_yield
                FROM fundamentals f
                INNER JOIN portfolio p ON f.symbol = p.symbol
                INNER JOIN (
                    SELECT symbol, MAX(fetch_date) as max_date FROM fundamentals GROUP BY symbol
                ) latest ON f.symbol = latest.symbol AND f.fetch_date = latest.max_date
                WHERE f.ex_dividend_date IS NOT NULL AND f.ex_dividend_date >= CURDATE()
                ORDER BY f.ex_dividend_date ASC
                LIMIT 20
            ");
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }

    /**
     * Get top gainers and losers within portfolio.
     */
    private function getPortfolioMovers(PDO $pdo): array {
        $sql = "
            SELECT p.symbol,
                   latest.close as current_price,
                   prev.close as prev_close,
                   CASE WHEN prev.close > 0 THEN ((latest.close - prev.close) / prev.close) * 100 ELSE 0 END as change_pct
            FROM portfolio p
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close
                FROM stockprices sp1
                INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) sp2
                    ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON p.symbol = latest.symbol
            LEFT JOIN (
                SELECT sp3.symbol, sp3.close
                FROM stockprices sp3
                INNER JOIN (
                    SELECT symbol, MAX(price_date) as max_date
                    FROM stockprices
                    WHERE price_date < (SELECT MAX(price_date) FROM stockprices sp4 WHERE sp4.symbol = stockprices.symbol)
                    GROUP BY symbol
                ) sp4 ON sp3.symbol = sp4.symbol AND sp3.price_date = sp4.max_date
            ) prev ON p.symbol = prev.symbol
            ORDER BY change_pct DESC
        ";
        $rows = $pdo->query($sql)->fetchAll();

        $gainers = array_filter($rows, fn($r) => ($r['change_pct'] ?? 0) > 0);
        $losers = array_filter($rows, fn($r) => ($r['change_pct'] ?? 0) < 0);

        return [
            'gainers' => array_slice($gainers, 0, 5),
            'losers' => array_slice($losers, 0, 5),
        ];
    }

    /**
     * Get data coverage stats for portfolio symbols.
     */
    private function getPortfolioCoverage(PDO $pdo): array {
        $totalSymbols = $pdo->query("SELECT COUNT(DISTINCT symbol) FROM portfolio")->fetchColumn();
        $withPrices = $pdo->query("
            SELECT COUNT(DISTINCT p.symbol) FROM portfolio p
            INNER JOIN stockprices sp ON p.symbol = sp.symbol
        ")->fetchColumn();
        $withIndicators = $pdo->query("
            SELECT COUNT(DISTINCT p.symbol) FROM portfolio p
            INNER JOIN indicators_json ij ON p.symbol = ij.symbol
        ")->fetchColumn();
        $totalRows = $pdo->query("
            SELECT COUNT(*) FROM stockprices sp
            INNER JOIN portfolio p ON sp.symbol = p.symbol
        ")->fetchColumn();

        return [
            'total' => $totalSymbols,
            'with_prices' => $withPrices,
            'with_indicators' => $withIndicators,
            'total_rows' => $totalRows,
        ];
    }
}
