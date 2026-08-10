<?php

declare(strict_types=1);

namespace App\Strategy\MoneyManagement;

use App\Strategy\BaseStrategy;

/**
 * ATR Trailing Stop — Dynamic position-level risk management.
 * Source: Welles Wilder; Investopedia; J. Wilder (1978)
 */
class ATRTrailingStopStrategy extends BaseStrategy
{
    protected function init(): void
    {
        $this->name = 'ATR Trailing Stop';
        $this->category = 'money_management';
        $this->description = 'Every position gets two stops: fixed (max acceptable loss from cost) and '
            . 'trailing (ATR-based dynamic). Once trailing exceeds fixed, the trailing stop controls. '
            . 'Self-adjusting: widens in high-vol, tightens in low-vol.';
        $this->sleeve = 'all';
        $this->timeHorizon = 'all';
        $this->riskLevel = 'low';
        $this->status = 'recommended';
        $this->requiredData = ['price'];
        $this->sources = [
            'Welles Wilder — "New Concepts in Technical Trading Systems" (1978)',
            'Investopedia: Average True Range (ATR)',
        ];
        $this->screeningCriteria = [
            'Fixed stop: Maximum acceptable loss from cost basis (e.g., 15%)',
            'Trailing stop: Dynamic, follows price up',
            'Once trailing > fixed → trailing controls (ignore fixed)',
            'ATR calculation: Stop = Price − (ATR(14) × Multiplier)',
            'Initial: 2× ATR, tighten to 1× after 3× ATR profit',
        ];
        $this->backtestResults = $this->buildBacktest(
            winRate: 'N/A (Risk Mgmt)',
            profitFactor: 'N/A',
            avgWin: 'Trend-captured',
            avgLoss: 'ATR-limited',
            totalTrades: 0,
            maxDrawdown: 'Controlled',
            implications: 'ALWAYS use trailing stops — the single most important risk tool. '
                . 'Self-adjusting mechanism is why ATR beats fixed-percentage stops. '
                . 'Once trailing stop exceeds fixed stop, ignore the fixed stop entirely. '
                . 'Recommended: 2× ATR(14) initially, tighten to 1× after 3× ATR profit.',
        );
    }
}
