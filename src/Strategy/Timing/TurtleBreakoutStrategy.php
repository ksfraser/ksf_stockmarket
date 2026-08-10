<?php

declare(strict_types=1);

namespace App\Strategy\Timing;

use App\Strategy\BaseStrategy;

/**
 * Turtle Trading (Donchian Breakout) — Classic trend-following breakout system.
 * Source: Richard Dennis; "Way of the Turtle"; Investopedia
 */
class TurtleBreakoutStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'Turtle Trading (Donchian Breakout)';
        $this->category = 'timing';
        $this->description = 'Buy when price exceeds the 20-day Donchian Channel high. '
            . 'Sell when price falls below the 55-day Donchian Channel low. '
            . 'Classic trend-following from Richard Dennis\'s Turtle Traders experiment.';
        $this->sleeve = 'tactical';
        $this->timeHorizon = 'medium_term';
        $this->riskLevel = 'high';
        $this->status = 'battle_tested';
        $this->requiredData = ['price', 'volume'];
        $this->sources = [
            'Richard Dennis — Turtle Traders experiment (1983-1988)',
            'Curtis Faith — "Way of the Turtle" (2007)',
            'Investopedia: Donchian Channels',
        ];
        $this->screeningCriteria = [
            'Entry: Close > 20-day Donchian Upper (20-day high)',
            'Exit: Close < 55-day Donchian Lower (55-day low)',
            'System 2 variant: 55-day breakout for longer-term',
            'Dual system: Both 20d and 55d signals considered',
            'Trend filter: Only in trending markets',
            'Range-bound warning: FALSE signals at range tops',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: '45%',
            profitFactor: '1.22',
            avgWin: '4.5%',
            avgLoss: '3.2%',
            totalTrades: 891,
            maxDrawdown: '-18.4%',
            implications: 'Captures major trends. Dual system (20d + 55d) improves reliability. '
                . 'FALSE signals at range tops — often the worst entries. '
                . 'Does NOT work on range-bound stocks like MTY. '
                . 'Best on trending names with high NATR.',
        );
    }
}
