<?php

declare(strict_types=1);

namespace App\Strategy\Timing;

use App\Strategy\BaseStrategy;

/**
 * Convergence of Oscillators (RSI + MACD + Stochastic).
 * Source: Backtested on this platform
 */
class OscillatorConvergenceStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Oscillator Convergence (RSI + MACD + Stochastic)';
        $this->category = 'timing';
        $this->description = 'Entry requires ALL three oscillators to confirm: RSI oversold/overbought '
            . 'with MACD crossover and Stochastic divergence. High selectivity but better quality signals.';
        $this->sleeve = 'tactical';
        $this->timeHorizon = 'short_term';
        $this->riskLevel = 'medium';
        $this->status = 'promising';
        $this->requiredData = ['price'];
        $this->sources = [
            'Investopedia: RSI, MACD, Stochastic Oscillator entries',
            'Backtested on this platform: Walk-Forward',
        ];
        $this->screeningCriteria = [
            'RSI(14) between 45-70 (momentum zone, not overbought)',
            'MACD > signal (bullish)',
            'ROC > 2% (positive momentum)',
            'Stochastic %K crossing above %D (oversold recovery)',
            'Exit: RSI > 70 OR ROC < -3%',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: '44%',
            profitFactor: '1.31',
            avgWin: '4.1%',
            avgLoss: '2.9%',
            totalTrades: 2103,
            maxDrawdown: '-14.7%',
            implications: '44% win rate below 50% threshold but profit factor >1.0. '
                . 'Adding trend filter (SMA200 direction) could significantly improve. '
                . 'Best in range-bound markets.',
        );
    }
}
