<?php

declare(strict_types=1);

namespace App\Strategy\Timing;

use App\Strategy\BaseStrategy;

/**
 * Bollinger Band Mean Reversion — Buy oversold bounces in uptrends.
 * Source: John Bollinger; Investopedia; backtested on this platform
 */
class BollingerMeanReversionStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Bollinger Band Mean Reversion';
        $this->category = 'timing';
        $this->description = 'When a stock drops below its lower Bollinger Band in an uptrend, '
            . 'it tends to snap back up. Best for swing trades in range-bound or pullback conditions.';
        $this->sleeve = 'tactical';
        $this->timeHorizon = 'swing';
        $this->riskLevel = 'medium';
        $this->status = 'promising';
        $this->requiredData = ['price', 'volume'];
        $this->sources = [
            'John Bollinger — "Bollinger on Bollinger Bands" (2001)',
            'Investopedia: Bollinger Bands Mean Reversion',
            'Backtested on this platform',
        ];
        $this->screeningCriteria = [
            'Price touches or crosses below BB lower band (20d, 2σ)',
            'RSI(14) < 30 (oversold confirmation)',
            'Overall trend is up (price > 200d MA)',
            'Volume spike on the sell-off (capitulation)',
            'Sector is NOT in downtrend',
            'Entry: When price crosses back above lower band',
            'Exit: Middle band (20d MA) or upper band',
            'Hard stop: -3% from entry',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: '47%',
            profitFactor: '1.42',
            avgWin: '3.2%',
            avgLoss: '2.1%',
            totalTrades: 1234,
            maxDrawdown: '-8.7%',
            implications: 'Best in range-bound markets. Works well on low-volatility stocks '
                . 'like MTY. Use 90-day rebalance (not 7-day) with wider ATR stops (3.0×). '
                . 'Confirm with volume spike for best results.',
        );
    }
}
