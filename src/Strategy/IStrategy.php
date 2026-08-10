<?php

declare(strict_types=1);

namespace App\Strategy;

/**
 * IStrategy — Contract for all stock selection and money/risk management strategies.
 *
 * Every strategy must be able to:
 * - Describe itself (name, category, description)
 * - Score a candidate symbol given indicator data
 * - Report backtest results (win rate, profit factor, drawdown, etc.)
 * - Declare which sleeve it belongs to (Core, Tactical, Income, Satellite)
 */
interface IStrategy
{
    /** Strategy display name */
    public function getName(): string;

    /** Strategy category: stock_selection, money_management, timing */
    public function getCategory(): string;

    /** Strategy description for display */
    public function getDescription(): string;

    /** Which portfolio sleeve this strategy is designed for */
    public function getSleeve(): string; // 'core', 'tactical', 'income', 'satellite'

    /** Time horizon for this strategy */
    public function getTimeHorizon(): string; // 'long_term', 'medium_term', 'short_term', 'swing'

    /** Risk level */
    public function getRiskLevel(): string; // 'low', 'medium', 'high', 'very_high'

    /** Screening criteria as structured data */
    public function getScreeningCriteria(): array;

    /** Expected performance stats from backtests */
    public function getBacktestResults(): array;

    /** Strategy status: battle_tested, promising, needs_improvement, theoretical, active */
    public function getStatus(): string;

    /** Data sources required (e.g. ['price', 'volume', 'fundamentals', 'options']) */
    public function getRequiredData(): array;

    /** Academic/real-world sources for this strategy */
    public function getSources(): array;

    /** Score a symbol's indicators (0.0 to 1.0). Higher = better candidate. */
    public function score(array $indicators): float;
}
