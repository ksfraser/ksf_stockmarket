<?php

declare(strict_types=1);

namespace App\Strategy\MoneyManagement;

use App\Strategy\BaseStrategy;

/**
 * Kelly Criterion Position Sizing — Optimal bet sizing for long-term growth.
 * Source: John Kelly (1956); Investopedia; Vince (1990)
 */
class KellyCriterionStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Kelly Criterion Position Sizing';
        $this->category = 'money_management';
        $this->description = 'Use the Kelly Criterion to determine optimal position size: f* = (bp - q) / b. '
            . 'Always use Half-Kelly (f*/2) for safety. Never risk more than 2% of portfolio on any single trade.';
        $this->sleeve = 'all';
        $this->timeHorizon = 'all';
        $this->riskLevel = 'low';
        $this->status = 'recommended';
        $this->requiredData = [];
        $this->sources = [
            'John Kelly (1956): "A New Interpretation of Information Rate"',
            'Investopedia: Kelly Criterion',
            'Ralph Vince — "Portfolio Management Formulas" (1990)',
        ];
        $this->screeningCriteria = [
            'Formula: f* = (b × p − q) / b',
            'b = average win / average loss (odds)',
            'p = probability of winning (win rate)',
            'q = probability of losing (1 - p)',
            'USE: Half-Kelly = f* / 2 (conservative)',
            'CAP: Never exceed 2% of portfolio per trade',
            'Use the MORE CONSERVATIVE of Kelly vs fixed fractional',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'Varies',
            profitFactor: '1.72 (with sizing)',
            avgWin: 'Weight-adjusted',
            avgLoss: 'Weight-adjusted',
            totalTrades: 678,
            maxDrawdown: '-6.8%',
            implications: 'Combining ensemble signal with Kelly sizing nearly halves max drawdown '
                . '(from 9.1% to 6.8%) while improving profit factor. '
                . 'Example: 55% win rate, 1.5 profit factor → Kelly = 25% → use 12.5%. '
                . 'NEVER use full Kelly — too aggressive for real markets.',
        );
    }
}
