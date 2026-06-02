<?php

declare(strict_types=1);

use App\Strategy\StrategyRegistry;
use App\Strategy\StrategyFactory;

/**
 * StrategyController — Displays backtested strategy results and methodology.
 *
 * Uses Dependency Injection via StrategyRegistry. All strategies are loaded
 * through the registry — no hardcoded strategy data.
 *
 * Construction:
 *   $registry = StrategyFactory::create();
 *   $controller = new StrategyController($registry);
 *
 * Or with DI container:
 *   $controller = $container->get(StrategyController::class);
 */
class StrategyController
{
    private StrategyRegistry $registry;

    /**
     * @param StrategyRegistry $registry Injected strategy registry
     */
    public function __construct(StrategyRegistry $registry)
    {
        $this->registry = $registry;
    }

    /**
     * GET /?action=strategy_stock — Stock selection strategies page.
     * Groups strategies by sleeve: Core, Tactical, Income, Satellite.
     */
    public function stockSelection(): array
    {
        // Stock selection strategies, grouped by sleeve
        $bySleeve = $this->registry->bySleeve('stock_selection');

        // Timing strategies (available for all sleeves)
        $timing = $this->registry->all('timing');

        return [
            'pageTitle'    => 'Stock Selection Strategies',
            'template'     => 'strategy_stock',
            'bySleeve'     => $bySleeve,
            'timing'       => $timing,
            'totalCount'   => $this->registry->count(),
        ];
    }

    /**
     * GET /?action=strategy_money — Money/risk management strategies page.
     */
    public function moneyManagement(): array
    {
        $strategies = $this->registry->all('money_management');

        return [
            'pageTitle'  => 'Money & Risk Management',
            'template'   => 'strategy_money',
            'strategies' => $strategies,
            'totalCount' => count($strategies),
        ];
    }

    /**
     * GET /?action=strategy_timing — Technical timing strategies page.
     */
    public function timing(): array
    {
        // Split by status: battle_tested first, then promising, then needs work
        $all = $this->registry->all('timing');
        $tested = array_filter($all, fn($s) => in_array($s['status'], ['battle_tested', 'active', 'recommended']));
        $development = array_filter($all, fn($s) => in_array($s['status'], ['promising', 'needs_improvement', 'theoretical']));

        return [
            'pageTitle'  => 'Timing & Technical Strategies',
            'template'   => 'strategy_timing',
            'tested'     => array_values($tested),
            'development' => array_values($development),
            'totalCount' => count($all),
        ];
    }
}
