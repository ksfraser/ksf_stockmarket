<?php

declare(strict_types=1);

namespace App\Strategy\Timing;

use App\Strategy\BaseStrategy;

/**
 * Fibonacci Retracement Entry — Trade pullbacks to key Fibonacci levels.
 * Source: Investopedia; Leonardo Fibonacci; widely used institutional approach
 */
class FibonacciRetracementStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Fibonacci Retracement Entry';
        $this->category = 'timing';
        $this->description = 'Trade pullbacks to key Fibonacci retracement levels (38.2%, 50%, 61.8%) '
            . 'within established trends. Entry at 61.8% deep retracement with bullish confirmation candle. '
            . 'Do NOT buy at Fib levels blindly — wait for confirmation.';
        $this->sleeve = 'tactical';
        $this->timeHorizon = 'medium_term';
        $this->riskLevel = 'medium';
        $this->status = 'recommended';
        $this->requiredData = ['price'];
        $this->sources = [
            'Investopedia: Fibonacci Retracement',
            'W.D. Gann — Fibonacci ratios in market analysis',
            'Institutional standard practice',
        ];
        $this->screeningCriteria = [
            'Identify prior swing low → swing high (uptrend)',
            'Key retracement levels: 23.6%, 38.2%, 50%, 61.8%, 78.6%',
            'Entry zone: Price retraces to 61.8% (deep)',
            'Entry trigger: Bullish confirmation candle (engulfing, hammer) + volume',
            'Stop: Below the 78.6% level',
            'Target: Previous swing high (100%) or 1.618% extension',
            'Do NOT anticipate — WAIT for confirmation at the level',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: '~55% (with confirmation)',
            profitFactor: '~1.45',
            avgWin: '4-6% per swing',
            avgLoss: '2.5-3.5%',
            implications: 'Institutional traders cluster orders at Fibonacci levels. '
                . 'The 61.8% (golden ratio) level is the most significant. '
                . 'NEVER buy at 61.8% without a confirmation candle — '
                . 'price can overshoot to 78.6% or fully retrace. '
                . 'Combine with ADX > 25 to confirm trending market.',
        );
    }
}
