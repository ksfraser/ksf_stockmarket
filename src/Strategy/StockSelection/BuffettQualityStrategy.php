<?php

declare(strict_types=1);

namespace App\Strategy\StockSelection;

use App\Strategy\BaseStrategy;

/**
 * 1. Warren Buffett "Wonderful Company at Fair Quality" — Buy wonderful companies at fair prices, hold forever.
 * Source: Berkshire Hathaway letters, Motley Fool Stock Advisor "Wide Moat"
 * Best for: Core sleeve (40%)
 */
class BuffettQualityStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Buffett Quality Score';
        $this->category = 'stock_selection';
        $this->description = 'Buy wonderful companies at fair prices and hold forever. '
            . 'Screens for wide moat businesses with consistent ROE, low debt, positive FCF, '
            . 'and honest management. Not a timing strategy — use as first-pass universe filter.';
        $this->sleeve = 'core';
        $this->timeHorizon = 'long_term';
        $this->riskLevel = 'low';
        $this->status = 'screening_tool';
        $this->requiredData = ['fundamentals'];
        $this->sources = [
            'Berkshire Hathaway Shareholder Letters (1977-2024)',
            'Motley Fool Stock Advisor — Wide Moat (+978% vs S&P +212%, 2002-2026)',
        ];
        $this->screeningCriteria = [
            'ROE > 15% (5-year average)',
            'Debt/Equity < 0.5',
            'Gross Margin > 40%',
            'Operating Margin > 15%',
            'Free Cash Flow positive 5+ years',
            'Revenue growth > 10% (5-year CAGR)',
            'PEG Ratio < 1.5',
            'Management ownership > 1%',
            'No earnings decline in last 5 years',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A (Hold Strategy)',
            profitFactor: 'N/A',
            avgWin: 'Long-term compound',
            avgLoss: 'N/A',
            totalTrades: 0,
            maxDrawdown: 'N/A',
            implications: 'Not a timing strategy — filters universe to high-quality companies. '
                . 'Use as first-pass filter before applying technical entry signals. '
                . 'Portfolio holdings scored above 60/100 show significantly lower volatility.',
        );
    }
}
