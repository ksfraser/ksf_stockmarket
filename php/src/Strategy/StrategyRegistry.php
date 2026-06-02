<?php

declare(strict_types=1);

namespace App\Strategy;

/**
 * StrategyRegistry — Holds all registered strategies. Uses DI to load them.
 *
 * Register strategies via constructor injection or auto-discovery.
 * The StrategyController asks this registry for strategies by category.
 */
class StrategyRegistry
{
    /** @var IStrategy[] */
    private array $strategies = [];

    /**
     * @param IStrategy[] $strategies Array of strategy instances (injected via DI)
     */
    public function __construct(array $strategies = [])
    {
        foreach ($strategies as $strategy) {
            $this->register($strategy);
        }
    }

    public function register(IStrategy $strategy): void
    {
        $this->strategies[] = $strategy;
    }

    /**
     * Get all strategies, optionally filtered by category or sleeve.
     *
     * @return array Array of strategy->toArray() results
     */
    public function all(?string $category = null, ?string $sleeve = null): array
    {
        $filtered = $this->strategies;

        if ($category !== null) {
            $filtered = array_filter($filtered, fn($s) => $s->getCategory() === $category);
        }
        if ($sleeve !== null) {
            $filtered = array_filter($filtered, fn($s) => $s->getSleeve() === $sleeve);
        }

        return array_map(fn($s) => $s->toArray(), array_values($filtered));
    }

    /**
     * Get all strategies grouped by sleeve.
     * @return array<string, array> keyed by sleeve name
     */
    public function bySleeve(?string $category = null): array
    {
        $groups = ['core' => [], 'tactical' => [], 'income' => [], 'satellite' => []];
        foreach ($this->all($category) as $strategy) {
            $sleeve = $strategy['sleeve'];
            if (!isset($groups[$sleeve])) {
                $groups[$sleeve] = [];
            }
            $groups[$sleeve][] = $strategy;
        }
        return $groups;
    }

    /**
     * Get all strategies grouped by category within sleeve.
     */
    public function byCategory(): array
    {
        $groups = [];
        foreach ($this->all() as $strategy) {
            $cat = $strategy['category'];
            if (!isset($groups[$cat])) {
                $groups[$cat] = [];
            }
            $groups[$cat][] = $strategy;
        }
        return $groups;
    }

    public function count(): int
    {
        return count($this->strategies);
    }
}
