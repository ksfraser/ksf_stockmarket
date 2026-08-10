<?php

declare(strict_types=1);

namespace App\Strategy\StockSelection;

use App\Strategy\BaseStrategy;

/**
 * Dividend Aristocrats — 25+ years of consecutive dividend increases.
 * Source: S&P Indices; Investopedia
 */
class DividendAristocratsStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Dividend Aristocrats & Kings';
        $this->category = 'stock_selection';
        $this->description = 'Buy companies with 25+ years (Aristocrats) or 50+ years (Kings) of '
            . 'consecutive dividend increases. Quality filter + income generation.';
        $this->sleeve = 'income';
        $this->timeHorizon = 'long_term';
        $this->riskLevel = 'low';
        $this->status = 'battle_tested';
        $this->requiredData = ['fundamentals'];
        $this->sources = [
            'S&P Dividend Aristocrats Index — 10.5% annualized (2008-2023)',
            'Investopedia: Dividend Aristocrat',
        ];
        $this->screeningCriteria = [
            '25+ consecutive years of dividend increases (Aristocrats)',
            'OR 50+ consecutive years (Kings)',
            'Payout ratio < 60% (sustainable)',
            'Revenue growth > 0 (not shrinking)',
            'Credit rating BBB+ or higher',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A (Hold Strategy)',
            profitFactor: 'N/A',
            avgWin: '10.5% annualized (index avg)',
            avgLoss: 'Lower volatility than S&P',
            totalTrades: 0,
            maxDrawdown: 'Below average vs S&P',
            implications: 'Quality filter, dividend growth compounds over time, defensive in downturns. '
                . 'LOW growth in some names. Yield compression in low-rate environments. '
                . 'Best for Income sleeve with dividend safety screen.',
        );
    }
}
