<?php
/**
 * RiskController - Risk management for ksf_stockmarket
 * 
 * Integrates pre-trade checks, circuit breakers, and audit features.
 */
class RiskController {
    private $pdo;
    /** @var SymbolResolver */
    private $resolver;
    
    public function __construct() {
        $this->pdo = Database::get();
        $this->resolver = new SymbolResolver($this->pdo);
    }
    
    /**
     * Pre-trade gate - check if a trade is safe to take.
     */
    public function preTradeGate(array $params): array {
        $userId = $params['user_id'] ?? 1;
        $symbol = $this->resolver->resolve(strtoupper($params['symbol'] ?? ''));
        $direction = strtoupper($params['direction'] ?? '');
        $entryPrice = (float)($params['entry_price'] ?? 0);
        $accountBalance = (float)($params['account_balance'] ?? 100000);
        $dailyPnl = (float)($params['daily_pnl'] ?? 0);
        
        // Get open positions
        $stmt = $this->pdo->prepare("SELECT symbol FROM portfolio WHERE user_id = :uid AND shares > 0");
        $stmt->execute([':uid' => $userId]);
        $openPositions = $stmt->fetchAll();
        
        $checks = [];
        
        // Daily loss limit (3%)
        $dailyLimit = $accountBalance * 0.03;
        $dailyBreached = $dailyPnl < -$dailyLimit;
        $checks[] = [
            'name' => 'Daily loss limit',
            'result' => $dailyBreached ? 'BLOCK' : 'PASS',
            'detail' => "P&L: \${$dailyPnl} vs limit: \${$dailyLimit}"
        ];
        
        // Max positions (12)
        $maxPositions = 12;
        $positionsBreached = count($openPositions) >= $maxPositions;
        $checks[] = [
            'name' => 'Max open positions',
            'result' => $positionsBreached ? 'BLOCK' : 'PASS',
            'detail' => count($openPositions) . "/{$maxPositions} positions open"
        ];
        
        // Same asset held (for BUY)
        $sameAsset = false;
        foreach ($openPositions as $p) {
            if ($p['symbol'] === $symbol) {
                $sameAsset = true;
                break;
            }
        }
        $checks[] = [
            'name' => 'Same asset held',
            'result' => $sameAsset && $direction === 'BUY' ? 'BLOCK' : 'PASS',
            'detail' => $sameAsset ? "Already long {$symbol}" : 'No conflict'
        ];
        
        // Risk per trade (2%)
        $riskOk = ($params['risk_pct'] ?? 0.02) <= 0.02;
        $checks[] = [
            'name' => 'Risk percentage',
            'result' => $riskOk ? 'PASS' : 'BLOCK',
            'detail' => ($params['risk_pct'] ?? 0.02) * 100 . '% <= 2% max'
        ];
        
        $blocked = array_filter($checks, fn($c) => $c['result'] === 'BLOCK');
        
        return [
            'checks' => $checks,
            'verdict' => count($blocked) > 0 ? 'BLOCKED' : 'APPROVED',
            'position_size' => count($blocked) === 0 ? $accountBalance * 0.02 : 0
        ];
    }
    
    /**
     * Get portfolio risk audit.
     */
    public function portfolioAudit(int $userId): array {
        $stmt = $this->pdo->prepare("
            SELECT symbol, shares, cost_basis, account_type 
            FROM portfolio 
            WHERE user_id = :uid AND shares > 0
        ");
        $stmt->execute([':uid' => $userId]);
        $positions = $stmt->fetchAll();
        
        $totalValue = 0;
        $totalRisk = 0;
        $concentration = [];
        
        foreach ($positions as $p) {
            // Simplified - would need current price
            $value = $p['shares'] * $p['cost_basis'];
            $totalValue += $value;
            
            // Account for stop loss risk (2% default)
            $risk = $value * 0.02;
            $totalRisk += $risk;
            
            // Track concentrations
            $firstTwo = substr($p['symbol'], 0, 2);
            $concentration[$firstTwo] = ($concentration[$firstTwo] ?? 0) + $value;
        }
        
        return [
            'total_value' => $totalValue,
            'total_risk_pct' => $totalValue > 0 ? ($totalRisk / $totalValue) * 100 : 0,
            'exposure_pct' => 100, // Simplified
            'concentrations' => $concentration,
            'rating' => ($totalRisk / $totalValue) < 0.1 ? 'GREEN' : 'AMBER'
        ];
    }
}