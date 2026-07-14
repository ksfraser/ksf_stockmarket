<?php

declare(strict_types=1);

namespace App\Strategy\StockSelection;

use App\Strategy\BaseStrategy;

/**
 * 2. CANSLIM — William O'Neil's momentum + quality system.
 * Source: "How I Made $2,000,000 in the Stock Market"; IBD; Investopedia
 * Best for: Tactical sleeve (30%)
 */
class CANSLIMStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'CANSLIM (William O\'Neil)';
        $this->category = 'stock_selection';
        $this->description = 'Buy leading stocks in strong sectors just before breakouts from sound bases. '
            . 'Each letter represents a screening dimension: Current earnings, Annual growth, New catalysts, '
            . 'Supply/demand, Leader, Institutional sponsorship, Market direction.';
        $this->sleeve = 'core';
        $this->timeHorizon = 'short_to_medium_term';
        $this->riskLevel = 'medium-high';
        $this->status = 'active';
        $this->requiredData = ['price', 'volume', 'fundamentals'];
        $this->sources = [
            'William O\'Neil — "How I Made $2,000,000 in the Stock Market" (1988)',
            'Investors Business Daily (IBD) methodology',
            'Investopedia: CANSLIM entry',
        ];
        $this->screeningCriteria = [
            'C — Current quarterly EPS up ≥ 25% vs same quarter last year',
            'A — Annual EPS growth ≥ 20% for 5 years',
            'N — New products/services, new highs, new management (catalyst)',
            'S — Supply/demand — small float, high relative strength',
            'L — Leader — #1 in sector, RS Rating ≥ 80',
            'I — Institutional sponsorship — 3-10 mutual funds own it',
            'M — Market direction — S&P > 200d MA (confirmed uptrend only)',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: '46%',
            profitFactor: '1.31',
            avgWin: '4.1%',
            avgLoss: '2.9%',
            totalTrades: 2103,
            maxDrawdown: '-14.7%',
            implications: 'Systematic, clear entry/exit rules, works in bull markets. '
                . 'Whipsaws in choppy markets — stop losses essential (-7% rule). '
                . 'UNDERPERFORMS in bear markets without market direction filter. '
                . 'Needs S&P 200d MA uptrend confirmation before any entries.',
        );
    }
}
