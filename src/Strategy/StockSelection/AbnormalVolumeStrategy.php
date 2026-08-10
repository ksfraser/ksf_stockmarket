<?php

declare(strict_types=1);

namespace App\Strategy\StockSelection;

use App\Strategy\BaseStrategy;

/**
 * Abnormal Volume Detection — Smart money accumulation/distribution signal.
 * Source: Investopedia; Wyckoff; own analysis
 */
class AbnormalVolumeStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Abnormal Volume Detection';
        $this->category = 'timing';
        $this->description = 'Unusual volume (3× average or higher) often precedes significant price moves. '
            . 'Institutions are quietly accumulating or distributing. Leading indicator for position entry/exit.';
        $this->sleeve = 'all';
        $this->timeHorizon = 'short_term';
        $this->riskLevel = 'medium';
        $this->status = 'promising';
        $this->requiredData = ['price', 'volume'];
        $this->sources = [
            'Investopedia: Volume Analysis',
            'Richard Wyckoff — Composite Operator theory',
        ];
        $this->screeningCriteria = [
            'Volume > 3× 20-day average volume',
            'Price change > ±2% on the high-volume day',
            'NOT an earnings day (earnings volume is noise)',
            'Insider filing in last 30 days (Form 4)',
            'Sector also showing abnormal volume',
            'Options volume also elevated (if applicable)',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A (Confirmation Signal)',
            profitFactor: 'N/A',
            avgWin: 'Leading indicator',
            avgLoss: 'N/A',
            totalTrades: 0,
            maxDrawdown: 'N/A',
            implications: 'Not a standalone signal — use to CONFIRM other strategy entries. '
                . 'Best used across ALL sleeves as a leading indicator. '
                . 'High volume without price movement = institutional accumulation. '
                . 'High volume with price spike = potential breakout or exhaustion.',
        );
    }
}
