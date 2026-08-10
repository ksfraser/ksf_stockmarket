<?php
/**
 * Futures Tracker - For ES, NQ, CL, GC, etc.
 * 
 * Extends ksf_stockmarket to support futures contracts.
 */
class FuturesTracker {
    private $pdo;
    
    public function __construct() {
        $this->pdo = Database::get();
    }
    
    /**
     * Get active futures from symbol_master.
     */
    public function getFuturesSymbols(): array {
        $stmt = $this->pdo->prepare(
            "SELECT symbol, name FROM symbol_master 
             WHERE is_active = 1 AND (
                 symbol IN ('ES','NQ','CL','GC','NG','SI','HG','6E','6B','ZN','ZS')
                 OR symbol REGEXP '^[A-Z]{1,2}[0-9]$'  -- futures like NQ1, ES2
             )
             ORDER BY symbol"
        );
        $stmt->execute();
        return $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
    }
    
    /**
     * Get contract specifications.
     */
    public function getContractSpec(string $symbol): array {
        $specs = [
            'ES' => ['tickValue' => 12.50, 'tickSize' => 0.25, 'contractSize' => 50],
            'NQ' => ['tickValue' => 5.00, 'tickSize' => 0.25, 'contractSize' => 20],
            'CL' => ['tickValue' => 10.00, 'tickSize' => 0.01, 'contractSize' => 1000],
            'GC' => ['tickValue' => 10.00, 'tickSize' => 0.10, 'contractSize' => 100],
            '6E' => ['tickValue' => 12.50, 'tickSize' => 0.0001, 'contractSize' => 100000],
        ];
        return $specs[$symbol] ?? ['tickValue' => 1, 'tickSize' => 0.01, 'contractSize' => 1];
    }
    
    /**
     * Calculate margin requirement for futures position.
     */
    public function calculateMargin(string $symbol, float $price, int $numContracts): float {
        $spec = $this->getContractSpec($symbol);
        $notional = $price * $spec['contractSize'] * $numContracts;
        
        // Simplified: assume 10% margin for stocks-like, 5% for futures
        $marginRate = 0.10;
        return $notional * $marginRate;
    }
    
    /**
     * Check if contract is expiring - needs roll.
     */
    public function isExpiringSoon(string $symbol, string $currentDate, int $daysThreshold = 30): bool {
        // For stocks, this always returns false
        // For actual futures (like ES2406), would check expiry date
        return false;
    }
}