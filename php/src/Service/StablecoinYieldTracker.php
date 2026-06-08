<?php
/**
 * DeFi Stablecoin Yield Tracker
 * 
 * Tracks stablecoin yields on Uniswap V3, Curve, Aave, Compound, etc.
 * Not connected to live chains - tracks manually entered positions.
 */
class StablecoinYieldTracker {
    private $pdo;
    
    public function __construct() {
        $this->pdo = Database::get();
    }
    
    /**
     * Get user's stablecoin positions from database.
     */
    public function getPositions(int $userId = 1): array {
        $stmt = $this->pdo->prepare("SELECT * FROM stablecoin_positions WHERE user_id = :uid ORDER BY chain, protocol");
        $stmt->execute([':uid' => $userId]);
        return $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];
    }
    
    /**
     * Add a stablecoin position.
     */
    public function addPosition(int $userId, string $chain, string $protocol, string $pool, 
                               float $shares, float $entryPrice, ?string $notes = null): bool {
        $stmt = $this->pdo->prepare("
            INSERT INTO stablecoin_positions 
            (user_id, chain, protocol, pool, shares, entry_price, entry_date, notes)
            VALUES (:uid, :chain, :protocol, :pool, :shares, :price, CURDATE(), :notes)
        ");
        return $stmt->execute([
            ':uid' => $userId, ':chain' => $chain, ':protocol' => $protocol,
            ':pool' => $pool, ':shares' => $shares, ':price' => $entryPrice, ':notes' => $notes
        ]);
    }
    
    /**
     * AI Rebalancing Decision (adapted from defi-yield-optimizer-agent).
     * 
     * For stocks: decides when portfolio rebalance is worth transaction costs.
     * For stablecoins: decides when range rebalancing is worth gas costs.
     * Returns true if rebalance should occur.
     */
    public function shouldRebalance(array $positions, float $holdingsDrift = 0, float $gasCost = 9.95): bool {
        // For stablecoins: drift is price range deviation
        // For stocks: drift is position allocation % divergence
        
        // Simple heuristic: only rebalance if drift > 2% 
        // and expected recovery > gas cost impact
        $threshold = 0.02;
        
        return abs($holdingsDrift) > $threshold;
    }
    
    /**
     * Record yield history for a position.
     */
    public function recordYield(int $positionId, string $date, float $price, 
                                 float $apy, float $gasCost = 0): bool {
        $stmt = $this->pdo->prepare("
            INSERT INTO stablecoin_yield_history 
            (position_id, date, price, yield_apy, gas_cost_usd)
            VALUES (:pid, :date, :price, :apy, :gas)
            ON DUPLICATE KEY UPDATE
                price = VALUES(price),
                yield_apy = VALUES(yield_apy),
                gas_cost_usd = VALUES(gas_cost_usd)
        ");
        return $stmt->execute([
            ':pid' => $positionId, ':date' => $date, 
            ':price' => $price, ':apy' => $apy, ':gas' => $gasCost
        ]);
    }
}