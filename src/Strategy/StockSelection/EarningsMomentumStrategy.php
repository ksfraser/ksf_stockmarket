<?php

declare(strict_types=1);

namespace App\Strategy\StockSelection;

use App\Strategy\BaseStrategy;

/**
 * 5. Post-Earnings Announcement Drift (PEAD) — Trade earnings surprises.
 * Source: Bernard & Thomas (1989); Investopedia
 * Best for: Tactical sleeve — quarterly rebalance
 */
class EarningsMomentumStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Earnings Momentum (PEAD)';
        $this->category = 'stock_selection';
        $this->description = 'Stocks that beat earnings expectations continue to drift upward for 60-90 days '
            . 'after the announcement (Post-Earnings Announcement Drift). Well-documented academic anomaly.';
        $this->sleeve = 'tactical';
        $this->timeHorizon = 'short_term';
        $this->riskLevel = 'medium';
        $this->status = 'battle_tested';
        $this->requiredData = ['fundamentals', 'price'];
        $this->sources = [
            'Bernard & Thomas (1989): "Post-Earnings-Announcement Drift"',
            'Investopedia: Post-Earnings Announcement Drift',
            'Academic: 6-9% annualized excess return',
        ];
        $this->screeningCriteria = [
            'Earnings surprise > 5% (actual vs consensus)',
            'Revenue surprise > 3%',
            'Forward guidance raised',
            'Institutional buying after announcement',
            'Stock gap up on earnings > 3%',
            'Short interest < 10% (not crowded short)',
            'Estimate revisions: ↑ for next quarter',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A',
            profitFactor: 'N/A',
            avgWin: '6-9% annualized excess',
            avgLoss: 'N/A',
            totalTrades: 0,
            maxDrawdown: 'N/A',
            implications: 'Well-documented anomaly, relatively low risk. '
                . 'Requires real-time earnings data and consensus estimate feeds. '
                . 'Best in Tactical sleeve with quarterly rebalance around earnings.',
        );
    }
}
