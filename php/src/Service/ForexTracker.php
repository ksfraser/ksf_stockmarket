<?php
/**
 * Forex Tracker - For EUR/USD, USD/CAD, etc.
 * 
 * Extends ksf_stockmarket to support FX pairs.
 * Uses same portfolio architecture but handles 24/5 trading hours.
 */
class ForexTracker {
    private $pdo;
    
    public function __construct() {
        $this->pdo = Database::get();
    }
    
    /**
     * Get active forex pairs from symbol_master.
     */
    public function getForexPairs(): array {
        $stmt = $this->pdo->prepare(
            "SELECT symbol, name FROM symbol_master 
             WHERE is_active = 1 AND symbol LIKE '%.%' 
             ORDER BY symbol"
        );
        $stmt->execute();
        return $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
    }
    
    /**
     * Calculate rollover/overnight financing for Forex positions.
     * This applies to CFD-style forex where you pay/take overnight interest.
     */
    public function calculateRollover(string $symbol, float $notional, int $daysHeld): float {
        // Get swap rates from symbol metadata or hardcode majors
        $swapRates = [
            'EUR.CAD' => -0.8, // -0.8% annual for long
            'USD.CAD' => -1.2,
            'GBP.CAD' => -2.1,
            'AUD.CAD' => 2.6,   // positive carry for AUD/CAD long
        ];
        
        $rate = $swapRates[$symbol] ?? -0.5; // default
        return $notional * $rate * ($daysHeld / 365);
    }
    
    /**
     * Check if forex position should be closed for weekend/holiday.
     */
    public function shouldCloseForWeekend(string $symbol, string $dayOfWeek): bool {
        // Don't hold short AUD/USD or NZD/USD over weekend (high rollover risk)
        // Don't hold short EUR/USD on Sunday open
        return false; // Placeholder - could implement rules based on carry
    }
}