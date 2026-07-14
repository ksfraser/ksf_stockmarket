<?php
/**
 * BrokerStopController - Track stops you've actually placed with your brokerage.
 */
class BrokerStopController {

    private $pdo;
    private $userId;
    /** @var SymbolResolver */
    private $resolver;

    public function __construct() {
        $this->pdo = Database::get();
        $this->currentUser = AuthController::requireAuth();
        $this->userId = $this->currentUser['id'];
        $this->resolver = new SymbolResolver($this->pdo);
    }

    /**
     * GET /?action=broker_stops - List your active broker stops.
     */
    public function index(string $account_filter = 'all'): array {
        $where = ['user_id = :uid'];
        $params = [':uid' => $this->userId];
        
        if ($account_filter !== 'all') {
            $where[] = 'account_type = :acct';
            $params[':acct'] = $account_filter;
        }
        
        $sql = "
            SELECT bs.*, latest.close as current_price
            FROM broker_stop_orders bs
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close
                FROM stockprices sp1
                INNER JOIN (
                    SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol
                ) sp2 ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON bs.symbol = latest.symbol
            WHERE " . implode(' AND ', $where) . "
            ORDER BY placed_at DESC
        ";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        $stops = $stmt->fetchAll();
        
        // Calculate distance to stop
        foreach ($stops as &$s) {
            $price = $s['current_price'] ?? 0;
            $s['distance_pct'] = $this->calculateDistance($s, $price);
        }
        
        return [
            'pageTitle' => 'Broker Stop Orders',
            'template' => 'broker_stops',
            'stops' => $stops,
            'account_filter' => $account_filter,
            'account_types' => ['TFSA', 'RRSP', 'MARGIN'],
            'history' => $this->history(),
        ];
    }

    /**
     * Calculate distance percentage to stop level.
     */
    private function calculateDistance(array $stop, float $currentPrice): ?float {
        if (!$currentPrice) return null;
        
        $type = $stop['stop_type'];
        $value = $stop['stop_value'];
        
        switch ($type) {
            case 'trailing_pct':
                return $value * 100; // This is the pct itself
            case 'stop_loss':
                return $value * 100;
            case 'trailing_price':
            case 'stop_limit':
                if ($value > 0) {
                    return (($currentPrice - $value) / $currentPrice) * 100;
                }
                return null;
            default:
                return null;
        }
    }

    /**
     * POST /?action=broker_stops - Place a new stop order.
     */
    public function placeStop(array $post): array {
        $required = ['symbol', 'account_type', 'stop_type', 'stop_value'];
        foreach ($required as $field) {
            if (empty($post[$field])) {
                return ['error' => "Missing required field: $field"];
            }
        }
        
        $stmt = $this->pdo->prepare("
            INSERT INTO broker_stop_orders 
            (user_id, symbol, account_type, stop_type, stop_value, shares, status, notes)
            VALUES (:uid, :sym, :acct, :type, :val, :shares, 'active', :notes)
        ");
        
        $sym = strtoupper(trim($post['symbol']));
        $resolved = (new SymbolResolver(Database::get()))->resolve($sym);
        $shares = (float)($post['shares'] ?? 0);
        $sellMode = $post['sell_mode'] ?? 'all';
        $sellPct = ($sellMode === 'portion') ? (float)($post['sell_pct'] ?? 100) : 100.0;

        $stmt->execute([
            ':uid' => $this->userId,
            ':sym' => $resolved,
            ':acct' => $post['account_type'],
            ':type' => $post['stop_type'],
            ':val' => (float)$post['stop_value'],
            ':shares' => $shares,
            ':notes' => ($post['notes'] ?? '') . ($sellMode === 'portion' ? " [sell_pct=$sellPct%]" : ''),
        ]);
        
        return ['success' => "Stop order placed for {$post['symbol']}"];
    }

    /**
     * Mark a stop as triggered.
     */
    public function markTriggered(int $stopId): array {
        $stmt = $this->pdo->prepare("
            UPDATE broker_stop_orders 
            SET status = 'triggered', triggered_at = NOW()
            WHERE id = :id AND user_id = :uid
        ");
        $stmt->execute([':id' => $stopId, ':uid' => $this->userId]);
        
        return ['success' => "Stop marked as triggered"];
    }

    /**
     * Historical expired/cancelled/triggered stops.
     */
    public function history(): array {
        $stmt = $this->pdo->prepare("
            SELECT bs.*, latest.close as current_price
            FROM broker_stop_orders bs
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close
                FROM stockprices sp1
                INNER JOIN (
                    SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol
                ) sp2 ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON bs.symbol = latest.symbol
            WHERE bs.user_id = :uid
              AND bs.status IN ('triggered', 'cancelled', 'expired')
            ORDER BY bs.placed_at DESC
            LIMIT 200
        ");
        $stmt->execute([':uid' => $this->userId]);
        return $stmt->fetchAll();
    }
}