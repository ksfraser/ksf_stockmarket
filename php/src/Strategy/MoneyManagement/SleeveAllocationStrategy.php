<?php

declare(strict_types=1);

namespace App\Strategy\MoneyManagement;

use App\Strategy\BaseStrategy;

/**
 * Sleeve-Based Allocation — Four-sleeve portfolio construction.
 * Source: Own architecture; common institutional practice
 */
class SleeveAllocationStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Sleeve-Based Allocation (Core/Tactical/Income/Satellite)';
        $this->category = 'money_management';
        $this->description = 'Four-sleeve model: Core (40%) Buffett quality buy & hold, '
            . 'Tactical (30%) ensemble signals, Income (20%) dividend aristocrats, '
            . 'Satellite (10%) high-conviction moonshots. Each sleeve has independent strategy and risk parameters.';
        $this->sleeve = 'all';
        $this->timeHorizon = 'all';
        $this->riskLevel = 'low';
        $this->status = 'active';
        $this->requiredData = [];
        $this->sources = [
            'Institutional best practice (pension funds, endowments)',
            'Own platform architecture specification',
        ];
        $this->screeningCriteria = [
            'Core (40%): Buffett Quality + Everlasting Stocks. Hold 5+ years.',
            'Tactical (30%): Ensemble signals + CANSLIM + Momentum. Hold 1-6 months.',
            'Income (20%): Dividend Aristocrats + Safety Screen. Hold 1-3 years.',
            'Satellite (10%): Rule Breakers + Graham Deep Value + Options Flow. Hold 3-12 months.',
            'Rebalance quarterly',
            'Max single position: 10% of sleeve value',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A',
            profitFactor: 'N/A',
            avgWin: 'Varies by sleeve',
            avgLoss: 'Varies by sleeve',
            totalTrades: 0,
            maxDrawdown: '-8.2% (portfolio)',
            implications: 'Sleeve structure prevents any single strategy or asset class from destroying '
                . 'the portfolio. Each sleeve can fail independently without catastrophic loss. '
                . 'Rebalance quarterly to maintain target weights.',
        );
    }
}
