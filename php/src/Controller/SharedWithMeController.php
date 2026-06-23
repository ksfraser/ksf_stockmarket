<?php
/**
 * SharedWithMeController — read-only access to other users' portfolios/transactions.
 */

class SharedWithMeController {
    private $pdo;

    public function __construct() {
        $this->pdo = Database::get();
    }

    private function isViewer() {
        // Must be logged in to view shared content
        return AuthController::checkSession();
    }

    private function currentUserId() {
        $u = AuthController::checkSession();
        return $u ? (int) $u['id'] : 0;
    }

    /**
     * List users who have shared with the current user.
     * Advisors (role='advisor') are prefixed with "ADVISOR " and sorted first.
     */
    public function listSharers(int $currentUserId): array {
        $sql = "
            SELECT u.id, u.username, u.display_name, u.role,
                   COALESCE(pv.is_public, 0) AS is_public
            FROM users u
            LEFT JOIN portfolio_visibilities pv ON pv.user_id = u.id
            WHERE u.is_active = 1
              AND u.id != :me
              AND (
                pv.is_public = 1
                OR EXISTS (
                    SELECT 1 FROM portfolio_share_users psu
                    WHERE psu.user_id = u.id AND psu.shared_with_user_id = :me
                )
              )
            ORDER BY (u.role = 'advisor') DESC, u.username ASC
        ";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([':me' => $currentUserId]);
        $rows = $stmt->fetchAll();

        foreach ($rows as &$r) {
            $r['label'] = ($r['role'] === 'advisor') ? 'ADVISOR ' . $r['username'] : $r['username'];
        }
        return $rows;
    }

    /**
     * Get portfolio summary for a shared user.
     */
    public function portfolioSummary(int $ownerUserId): array {
        $stmt = $this->pdo->prepare("
            SELECT p.symbol,
                   SUM(p.shares) as shares,
                   SUM(p.shares * p.cost_basis) / NULLIF(SUM(p.shares), 0) as cost_basis,
                   MIN(p.entry_date) as entry_date,
                   p.account_type,
                   p.strategy,
                   p.trailing_stop_pct,
                   p.stop_loss_pct,
                   p.atr_multiplier
            FROM portfolio p
            WHERE p.user_id = :uid
            GROUP BY p.symbol, p.account_type
            ORDER BY p.symbol
        ");
        $stmt->execute([':uid' => $ownerUserId]);
        $rows = $stmt->fetchAll();

        $symbols = array_unique(array_column($rows, 'symbol'));
        $prices = [];
        if ($symbols) {
            $in = implode(',', array_fill(0, count($symbols), '?'));
            $stmt = $this->pdo->prepare("
                SELECT sp1.symbol, sp1.close, sp1.price_date
                FROM stockprices sp1
                INNER JOIN (SELECT symbol, MAX(price_date) as md FROM stockprices WHERE symbol IN ($in) GROUP BY symbol) sp2
                ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.md
            ");
            $stmt->execute($symbols);
            foreach ($stmt->fetchAll() as $r) {
                $prices[$r['symbol']] = $r;
            }
        }

        $totalCost = 0;
        $totalValue = 0;
        foreach ($rows as &$r) {
            $sym = $r['symbol'];
            $price = $prices[$sym]['close'] ?? 0;
            $costTotal = ($r['shares'] ?? 0) * ($r['cost_basis'] ?? 0);
            $currentValue = ($r['shares'] ?? 0) * $price;
            $r['current_price'] = $price;
            $r['cost_total'] = $costTotal;
            $r['current_value'] = $currentValue;
            $r['pnl'] = $currentValue - $costTotal;
            $r['pnl_pct'] = $costTotal > 0 ? ($r['pnl'] / $costTotal) * 100 : 0;
            $totalCost += $costTotal;
            $totalValue += $currentValue;
        }

        return [
            'rows' => $rows,
            'total_cost' => $totalCost,
            'total_value' => $totalValue,
            'total_pnl' => $totalValue - $totalCost,
            'total_pnl_pct' => $totalCost > 0 ? (($totalValue - $totalCost) / $totalCost) * 100 : 0,
        ];
    }

    /**
     * Get recent transactions for a shared user.
     */
    public function transactions(int $ownerUserId, int $limit = 200): array {
        $stmt = $this->pdo->prepare("
            SELECT t.id, t.symbol, t.trade_date, t.type, t.quantity, t.price, t.total, t.commission,
                   t.account_type, t.notes, t.source_file, t.created_at
            FROM transactions t
            WHERE t.user_id = :uid AND t.is_deleted = 0
            ORDER BY t.trade_date DESC
            LIMIT :lim
        ");
        $stmt->bindValue(':uid', $ownerUserId);
        $stmt->bindValue(':lim', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /**
     * Owner summary (read-only).
     */
    public function ownerSummary(int $ownerUserId): array {
        $stmt = $this->pdo->prepare("
            SELECT u.username, u.display_name, u.role
            FROM users u
            WHERE u.id = :uid
        ");
        $stmt->execute([':uid' => $ownerUserId]);
        $user = $stmt->fetch() ?: [];

        $portStmt = $this->pdo->prepare("
            SELECT COUNT(DISTINCT symbol) as cnt, SUM(shares) as total_shares
            FROM portfolio WHERE user_id = :uid
        ");
        $portStmt->execute([':uid' => $ownerUserId]);
        $portfolio = $portStmt->fetch() ?: [];

        $txnStmt = $this->pdo->prepare("
            SELECT COUNT(*) as cnt, MAX(trade_date) as last_date
            FROM transactions WHERE user_id = :uid
        ");
        $txnStmt->execute([':uid' => $ownerUserId]);
        $txns = $txnStmt->fetch() ?: [];

        return array_merge($user, $portfolio, $txns);
    }

    /**
     * Main page.
     */
    public function index(): array {
        $currentUserId = $this->currentUserId();
        $selectedId = isset($_GET['user_id']) ? (int) $_GET['user_id'] : 0;
        $tab = $_GET['tab'] ?? 'portfolio';

        $sharers = $this->listSharers($currentUserId);

        $ownerSummary = [];
        $portfolioData = [];
        $transactions = [];
        if ($selectedId > 0) {
            $ownerSummary = $this->ownerSummary($selectedId);
            if ($tab === 'transactions') {
                $transactions = $this->transactions($selectedId);
            } else {
                $portfolioData = $this->portfolioSummary($selectedId);
            }
        }

        return [
            'sharers' => $sharers,
            'selected_user_id' => $selectedId,
            'tab' => $tab,
            'owner_summary' => $ownerSummary,
            'portfolio_data' => $portfolioData,
            'transactions' => $transactions,
        ];
    }
}
