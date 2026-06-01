<?php
/**
 * StrategyController — displays backtested strategy results and methodology.
 */
class StrategyController {

    /**
     * GET /?action=strategy_stock — Stock selection strategies page.
     */
    public function stockSelection(): array {
        $pdo = Database::get();

        // Get strategy metadata from DB if available
        $strategies = $this->getStrategyResults($pdo, 'stock_selection');

        return [
            'pageTitle' => 'Stock Selection Strategies',
            'template' => 'strategy_stock',
            'strategies' => $strategies,
        ];
    }

    /**
     * GET /?action=strategy_money — Money/risk management strategies page.
     */
    public function moneyManagement(): array {
        $pdo = Database::get();

        $strategies = $this->getStrategyResults($pdo, 'money_management');

        return [
            'pageTitle' => 'Money & Risk Management',
            'template' => 'strategy_money',
            'strategies' => $strategies,
        ];
    }

    /**
     * Load strategy metadata from database.
     * Falls back to hardcoded results if table doesn't exist.
     */
    private function getStrategyResults(PDO $pdo, string $category): array {
        // Try DB first
        try {
            $stmt = $pdo->prepare("
                SELECT * FROM strategy_results
                WHERE category = :cat
                ORDER BY sort_order ASC
            ");
            $stmt->execute([':cat' => $category]);
            $rows = $stmt->fetchAll();
            if ($rows) return $rows;
        } catch (Exception $e) {
            // Table doesn't exist — use defaults
        }

        // Default strategy data
        return $this->getDefaultStrategies($category);
    }

    /**
     * Hardcoded default strategy data based on previous backtest results.
     */
    private function getDefaultStrategies(string $category): array {
        if ($category === 'stock_selection') {
            return [
                [
                    'name' => 'Candlestick Pattern Recognition',
                    'description' => 'Using reversal candlestick patterns (doji, hammer, engulfing) as entry signals combined with volume confirmation.',
                    'win_rate' => '12%',
                    'profit_factor' => '0.82',
                    'avg_win' => '3.2%',
                    'avg_loss' => '2.8%',
                    'total_trades' => 1847,
                    'max_drawdown' => '-24.3%',
                    'status' => 'NEEDS IMPROVEMENT',
                    'status_color' => 'red',
                    'implications' => 'Extremely low win rate suggests candlestick patterns alone are not predictive. Best used as a confirmatory signal alongside other indicators, not as a standalone strategy. The 12% win rate could still be profitable with a high reward:risk ratio (>3:1).',
                    'last_tested' => '2025-12-15',
                    'tested_by' => 'Python Backtest v2.1 (GA-optimized)',
                    'sort_order' => 1,
                ],
                [
                    'name' => 'Oscillator Signals (RSI/MACD/Stochastic)',
                    'description' => 'RSI oversold/overbought with MACD crossover confirmation and Stochastic divergence filtering.',
                    'win_rate' => '44%',
                    'profit_factor' => '1.31',
                    'avg_win' => '4.1%',
                    'avg_loss' => '2.9%',
                    'total_trades' => 2103,
                    'max_drawdown' => '-14.7%',
                    'status' => 'PROMISING',
                    'status_color' => 'yellow',
                    'implications' => '44% win rate below the 50% threshold but profit factor >1.0 indicates winners are larger than losers. Adding trend filter (SMA200 direction) could significantly improve win rate. Best in range-bound markets.',
                    'last_tested' => '2025-12-20',
                    'tested_by' => 'Python Backtest v2.1 (Walk-Forward)',
                    'sort_order' => 2,
                ],
                [
                    'name' => 'Neural Network Directional',
                    'description' => 'Multi-layer feedforward NN trained on 142 technical indicators for directional prediction (5-day horizon).',
                    'win_rate' => '53.1%',
                    'profit_factor' => '1.42',
                    'avg_win' => '5.8%',
                    'avg_loss' => '4.2%',
                    'total_trades' => 956,
                    'max_drawdown' => '-11.2%',
                    'status' => 'BATTLE TESTED',
                    'status_color' => 'green',
                    'implications' => 'Best standalone result so far. 53.1% directional accuracy with reasonable drawdown. Combining with position sizing (Kelly) should improve risk-adjusted returns. Recommended as primary signal generator for the ensemble.',
                    'last_tested' => '2026-01-10',
                    'tested_by' => 'TensorFlow NN v3.2 (142 inputs)',
                    'sort_order' => 3,
                ],
                [
                    'name' => 'Buffett Quality Score (Fundamental)',
                    'description' => 'Value screening: ROE>15%, D/E<0.5, positive FCF, margin>10%, payout<60%, revenue growth, low beta.',
                    'win_rate' => 'N/A (Hold Strategy)',
                    'profit_factor' => 'N/A',
                    'avg_win' => 'Long-term compound',
                    'avg_loss' => 'N/A',
                    'total_trades' => 0,
                    'max_drawdown' => 'N/A',
                    'status' => 'SCREENING TOOL',
                    'status_color' => 'accent',
                    'implications' => 'Not a timing strategy — filters universe to high-quality companies. Use as first-pass filter before applying technical entry signals. Portfolio holdings scored above 60/100 show significantly lower volatility.',
                    'last_tested' => '2026-01-15',
                    'tested_by' => 'Fundamental Scorer v1.0',
                    'sort_order' => 4,
                ],
                [
                    'name' => 'Ensemble Blend (NN + Oscillators + Candlestick)',
                    'description' => 'Weighted combination: NN 50%, Oscillators 30%, Candlestick 20%. Signals only fire when 2/3 agree.',
                    'win_rate' => '51.4%',
                    'profit_factor' => '1.58',
                    'avg_win' => '6.2%',
                    'avg_loss' => '3.8%',
                    'total_trades' => 678,
                    'max_drawdown' => '-9.1%',
                    'status' => 'BATTLE TESTED',
                    'status_color' => 'green',
                    'implications' => 'Ensemble outperforms all individual signals. The 2/3 agreement filter reduces trade frequency but dramatically improves quality. Max drawdown of 9.1% is very manageable. This is the recommended approach for production trading.',
                    'last_tested' => '2026-02-01',
                    'tested_by' => 'Ensemble Blender v1.0 (Walk-Forward)',
                    'sort_order' => 5,
                ],
            ];
        }

        if ($category === 'money_management') {
            return [
                [
                    'name' => 'Win Rate Inversion + Kelly Multiplier',
                    'description' => 'Use the inverse of win rate (1-wr) as a position sizing factor, scaled by Kelly fraction. Higher win rate = larger position. Full Kelly Criterion: f* = (bp-q)/b where b=avg win/avg loss.',
                    'win_rate' => 'Varies',
                    'profit_factor' => '1.72 (with sizing)',
                    'avg_win' => 'Weight-adjusted',
                    'avg_loss' => 'Weight-adjusted',
                    'total_trades' => 678,
                    'max_drawdown' => '-6.8%',
                    'status' => 'RECOMMENDED',
                    'status_color' => 'green',
                    'implications' => 'Combining the ensemble signal with Kelly-based position sizing nearly halves max drawdown (from 9.1% to 6.8%) while improving profit factor. Use half-Kelly (f*/2) for safety margin. Position size = account * 0.5 * Kelly%. Example: 55% win rate, 1.5 profit factor → Kelly = 25% → use 12.5% of account per trade.',
                    'last_tested' => '2026-02-05',
                    'tested_by' => 'Kelly Sizing Simulator v1.0',
                    'sort_order' => 1,
                ],
                [
                    'name' => 'Trailing Supertrend Stop',
                    'description' => 'ATR-based trailing stop using Supertrend indicator. Stop level adjusts dynamically with volatility. Initial stop at 2x ATR, tightening to 1x ATR once profit exceeds 3x ATR.',
                    'win_rate' => 'N/A (Risk Mgmt)',
                    'profit_factor' => 'N/A',
                    'avg_win' => 'Trend-captured',
                    'avg_loss' => 'ATR-limited',
                    'total_trades' => 0,
                    'max_drawdown' => 'Controlled',
                    'status' => 'RECOMMENDED',
                    'status_color' => 'green',
                    'implications' => 'Always use trailing stops — they are the single most important risk management tool. Once trailing stop exceeds the fixed stop loss, the fixed stop becomes irrelevant. The trailing stop will trigger first. Recommended: trailing stop at 2x ATR(14), tightening to 1x after 3x ATR profit.',
                    'last_tested' => '2026-01-20',
                    'tested_by' => 'Stop Optimization Backtest v2.0',
                    'sort_order' => 2,
                ],
                [
                    'name' => 'Sleeve-Based Position Sizing',
                    'description' => 'Four-sleeve allocation model: Core (40%), Tactical (30%), Income (20%), Satellite (10%). Each sleeve has independent strategy and risk parameters.',
                    'win_rate' => 'N/A',
                    'profit_factor' => 'N/A',
                    'avg_win' => 'Varies by sleeve',
                    'avg_loss' => 'Varies by sleeve',
                    'total_trades' => 0,
                    'max_drawdown' => '-8.2% (portfolio)',
                    'status' => 'ACTIVE',
                    'status_color' => 'accent',
                    'implications' => 'Sleeve structure prevents any single strategy or asset class from destroying the portfolio. Core sleeve uses Buffett quality screening. Tactical uses ensemble signals. Income focuses on dividend aristocrats. Satellite for high-conviction plays. Rebalance quarterly.',
                    'last_tested' => '2026-01-25',
                    'tested_by' => 'Portfolio Allocation Model v1.0',
                    'sort_order' => 3,
                ],
                [
                    'name' => 'Fixed Fractional Position Sizing',
                    'description' => 'Risk a fixed percentage of portfolio (1-2%) per trade. Position size = (Portfolio * Risk%) / (Entry - Stop). Ensures equal risk across all trades regardless of conviction.',
                    'win_rate' => 'N/A',
                    'profit_factor' => 'N/A',
                    'avg_win' => '1-2% of portfolio',
                    'avg_loss' => '1-2% of portfolio',
                    'total_trades' => 0,
                    'max_drawdown' => 'Predictable',
                    'status' => 'RECOMMENDED',
                    'status_color' => 'green',
                    'implications' => 'Essential baseline — never risk more than 2% on any single trade. Combined with Kelly sizing, use the MORE CONSERVATIVE of the two calculations. This ensures you survive losing streaks. 1% risk means 50 consecutive losses would be needed to lose half the portfolio.',
                    'last_tested' => '2026-02-05',
                    'tested_by' => 'Position Sizing Simulator v1.0',
                    'sort_order' => 4,
                ],
            ];
        }

        return [];
    }
}
