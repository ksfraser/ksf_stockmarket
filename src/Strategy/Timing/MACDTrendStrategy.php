<?php

declare(strict_types=1);

namespace App\Strategy\Timing;

use App\Strategy\BaseStrategy;

/**
 * MACD Trend — Trade MACD signal line crossovers.
 * Source: Gerald Appel; Investopedia; backtested
 */
class MACDTrendStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'MACD Trend Following';
        $this->category = 'timing';
        $this->description = 'Buy when MACD crosses above signal line. Sell when MACD crosses below. '
            . 'Trend momentum indicator — works best in trending markets, whipsaws in ranges.';
        $this->sleeve = 'tactical';
        $this->timeHorizon = 'medium_term';
        $this->riskLevel = 'medium';
        $this->status = 'needs_improvement';
        $this->requiredData = ['price'];
        $this->sources = [
            'Gerald Appel — MACD inventor',
            'Investopedia: MACD',
            'Backtested on this platform',
        ];
        $this->screeningCriteria = [
            'Entry: MACD > signal (bullish crossover)',
            'Exit: MACD < signal (bearish crossover)',
            'Confirmation: ROC > 2% (momentum confirmation)',
            'Override: RSI > 70 (overbought → exit regardless)',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: '46%',
            profitFactor: '1.08',
            avgWin: '2.8%',
            avgLoss: '2.6%',
            totalTrades: 1654,
            maxDrawdown: '-16.2%',
            implications: '46% win rate, barely profitable. Whipsaws in range-bound markets. '
                . 'Needs combination with other signals. Not strong enough as standalone. '
                . 'Only use as part of ensemble consensus voting.',
        );
    }
}
