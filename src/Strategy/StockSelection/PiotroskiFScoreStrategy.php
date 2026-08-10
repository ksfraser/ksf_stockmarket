<?php

declare(strict_types=1);

namespace App\Strategy\StockSelection;

use App\Strategy\BaseStrategy;

/**
 * 6. Piotroski F-Score — Value + Quality combined screen.
 * Source: Piotroski (2000); Investopedia
 * Best for: Income sleeve screening
 */
class PiotroskiFScoreStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Piotroski F-Score';
        $this->category = 'stock_selection';
        $this->description = 'Among cheap stocks (low P/B), pick the financially healthy ones using '
            . '9 binary criteria. Score 8-9 = strong, 0-2 = weak. Academic: outperformed by 7.5% annually.';
        $this->sleeve = 'income';
        $this->timeHorizon = 'long_term';
        $this->riskLevel = 'medium';
        $this->status = 'battle_tested';
        $this->requiredData = ['fundamentals'];
        $this->sources = [
            'Piotroski (2000): "Value Investing: Use of Historical Financial Statement Information"',
            'Investopedia: Piotroski F-Score',
            'Academic: F-Score 8-9 stocks outperformed low-value universe by 7.5% annually',
        ];
        $this->screeningCriteria = [
            'P/B < 1.5 (value universe)',
            'F-Score 8 or 9 required:',
            '  +1 ROA > 0',
            '  +1 CFO > 0',
            '  +1 ΔROA increasing',
            '  +1 CFO > ROA (quality of earnings)',
            '  +1 ΔLeverage decreasing',
            '  +1 ΔCurrent Ratio increasing',
            '  +1 No new shares issued',
            '  +1 ΔGross Margin increasing',
            '  +1 ΔAsset Turnover increasing',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A',
            profitFactor: 'N/A',
            avgWin: '7.5% annually over value universe',
            avgLoss: 'N/A',
            totalTrades: 0,
            maxDrawdown: 'N/A',
            implications: 'Systematic, removes value trap risk. '
                . 'Academic: F-Score 8-9 stocks outperformed by 7.5% annually. '
                . 'Best used as quality filter within the value universe before applying other strategies.',
        );
    }
}
