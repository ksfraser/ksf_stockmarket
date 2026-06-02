<?php

declare(strict_types=1);

namespace App\Strategy\StockSelection;

use App\Strategy\BaseStrategy;

/**
 * 3. GARP (Growth at Reasonable Price) — Peter Lynch's PEG-based approach.
 * Source: "One Up on Wall Street" (1989); Investopedia
 * Best for: Core/Tactical
 */
class GARPStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'GARP — Growth at Reasonable Price (Peter Lynch)';
        $this->category = 'stock_selection';
        $this->description = 'Buy companies growing earnings at 15-25% whose P/E is below their growth rate. '
            . 'Peter Lynch\'s approach: simple, intuitive, works well in growth markets. '
            . 'The PEG Ratio is the core metric.';
        $this->sleeve = 'core';
        $this->timeHorizon = 'medium_term';
        $this->riskLevel = 'medium';
        $this->status = 'battle_tested';
        $this->requiredData = ['price', 'fundamentals'];
        $this->sources = [
            'Peter Lynch — "One Up on Wall Street" (1989)',
            'Investopedia: Growth at a Reasonable Price (GARP)',
            'Fidelity Magellan Fund (1977-1990): 29.2% annualized',
        ];
        $this->screeningCriteria = [
            'PEG Ratio < 1.0 (ideal), < 1.5 (acceptable)',
            'EPS growth 15-25% — too fast is unsustainable',
            'Institutional ownership < 50% (not yet discovered)',
            'Insider buying in last 6 months',
            'Debt/Equity < industry average',
            'Cash from operations > net income (quality of earnings)',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A',
            profitFactor: 'N/A',
            avgWin: 'Long-term compound',
            avgLoss: 'N/A',
            totalTrades: 0,
            maxDrawdown: 'N/A',
            implications: 'Simple, intuitive, works well in growth markets. '
                . 'Lynch\'s Magellan Fund returned 29.2% annually (1977-1990). '
                . 'Misses deep value. Struggles when growth is scarce. '
                . 'Best combined with Buffett quality filter.',
        );
    }
}
