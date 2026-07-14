<?php

declare(strict_types=1);

namespace App\Strategy;

/**
 * StrategyFactory — Creates and configures the StrategyRegistry with all available strategies.
 *
 * This replaces the hardcoded getDefaultStrategies() in the old StrategyController.
 * To add a new strategy: create a class implementing IStrategy and register it here.
 * For true auto-discovery, strategies can be loaded from a config file.
 */
class StrategyFactory
{
    /**
     * Create a fully populated StrategyRegistry.
     *
     * @param array<IStrategy> $additionalStrategies Extra strategies to register (for testing/plugin)
     */
    public static function create(array $additionalStrategies = []): StrategyRegistry
    {
        $strategies = array_merge(self::getDefaultStrategies(), $additionalStrategies);
        return new StrategyRegistry($strategies);
    }

    /**
     * All built-in strategies.
     * @return array<IStrategy>
     */
    public static function getDefaultStrategies(): array
    {
        return [
            // === STOCK SELECTION STRATEGIES ===
            new StockSelection\BuffettQualityStrategy(),
            new StockSelection\GARPStrategy(),
            new StockSelection\CANSLIMStrategy(),
            new StockSelection\MomentumRelativeStrengthStrategy(),
            new StockSelection\EarningsMomentumStrategy(),
            new StockSelection\PiotroskiFScoreStrategy(),
            new StockSelection\DividendAristocratsStrategy(),
            new StockSelection\AbnormalVolumeStrategy(),

            // === TIMING / TECHNICAL STRATEGIES ===
            new Timing\SMA1050Strategy(),
            new Timing\BollingerMeanReversionStrategy(),
            new Timing\BollingerSqueezeStrategy(),
            new Timing\MACDTrendStrategy(),
            new Timing\OscillatorConvergenceStrategy(),
            new Timing\TurtleBreakoutStrategy(),
            new Timing\EnsembleBlendStrategy(),
            new Timing\FibonacciRetracementStrategy(),
            new Timing\ADXTrendFilterStrategy(),
            new Timing\OBVDivergenceStrategy(),

            // === MONEY MANAGEMENT STRATEGIES ===
            new MoneyManagement\KellyCriterionStrategy(),
            new MoneyManagement\SleeveAllocationStrategy(),
            new MoneyManagement\ATRTrailingStopStrategy(),
        ];
    }

    /**
     * Get all strategy class names for the given category.
     * Useful for admin/testing UI that lists available strategies.
     */
    public static function getStrategiesByCategory(string $category): array
    {
        return array_filter(
            self::getDefaultStrategies(),
            fn(IStrategy $s) => $s->getCategory() === $category
        );
    }
}
