<?php

declare(strict_types=1);

namespace App\Strategy\StockSelection;

use App\Strategy\BaseStrategy;

/**
 * 4. Momentum + Relative Strength — Buy past winners, hold for continued outperformance.
 * Source: Jegadeesh & Titman (1993); AQR Momentum Index; Investopedia
 * Best for: Tactical sleeve
 */
class MomentumRelativeStrengthStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Momentum + Relative Strength';
        $this->category = 'stock_selection';
        $this->description = 'Stocks that outperformed over the past 6-12 months tend to continue '
            . 'outperforming for 3-6 more months (momentum anomaly). Academic backbone from '
            . 'Jegadeesh & Titman (1993). AQR Momentum Index has outperformed S&P by 3-5% annually.';
        $this->sleeve = 'tactical';
        $this->timeHorizon = 'medium_term';
        $this->riskLevel = 'medium';
        $this->status = 'battle_tested';
        $this->requiredData = ['price', 'volume'];
        $this->sources = [
            'Jegadeesh & Titman (1993): "Returns to Buying Winners and Selling Losers"',
            'AQR Momentum Index — outperformed S&P by 3-5% annually since 1980',
            'Investopedia: Momentum Investing',
        ];
        $this->screeningCriteria = [
            '6-month price return > 80th percentile (relative to universe)',
            '12-month price return > 70th percentile',
            'Relative Strength (RS) rating ≥ 80',
            'Price > 200-day MA',
            'Volume increasing on up days',
            'Sector RS > 60 — sector also outperforming',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A',
            profitFactor: 'N/A',
            avgWin: '3-5% annually over S&P',
            avgLoss: 'Momentum crash risk',
            totalTrades: 0,
            maxDrawdown: 'Severe during crashes (2009, 2020)',
            implications: 'Strong academic backing, works across markets and decades. '
                . 'DANGER: Momentum crashes in 2009 and 2020 were devastating. '
                . 'Must combine with VIX fear gauge and market direction filter. '
                . 'Tax inefficient due to high turnover.',
        );
    }
}
