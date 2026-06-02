<?php

declare(strict_types=1);

namespace App\Strategy;

use App\Strategy\IStrategy;

/**
 * BaseStrategy — Abstract base with common strategy functionality.
 * All concrete strategies extend this and implement the IStrategy interface.
 */
abstract class BaseStrategy implements IStrategy
{
    protected string $name;
    protected string $category;
    protected string $description;
    protected string $sleeve;
    protected string $timeHorizon;
    protected string $riskLevel;
    protected string $status;
    protected array $requiredData;
    protected array $sources;
    protected array $screeningCriteria;
    protected array $backtestResults;

    public function __construct()
    {
        $this->init();
    }

    /**
     * Each strategy defines its own properties.
     */
    abstract protected function init(): void;

    public function getName(): string { return $this->name; }
    public function getCategory(): string { return $this->category; }
    public function getDescription(): string { return $this->description; }
    public function getSleeve(): string { return $this->sleeve; }
    public function getTimeHorizon(): string { return $this->timeHorizon; }
    public function getRiskLevel(): string { return $this->riskLevel; }
    public function getStatus(): string { return $this->status; }
    public function getRequiredData(): array { return $this->requiredData; }
    public function getSources(): array { return $this->sources; }
    public function getScreeningCriteria(): array { return $this->screeningCriteria; }
    public function getBacktestResults(): array { return $this->backtestResults; }

    public function score(array $indicators): float
    {
        // Default: no score unless overridden
        return 0.0;
    }

    /**
     * Flatten strategy to array for template rendering.
     */
    public function toArray(): array
    {
        return [
            'name'           => $this->name,
            'category'       => $this->category,
            'description'    => $this->description,
            'sleeve'         => $this->sleeve,
            'time_horizon'   => $this->timeHorizon,
            'risk_level'     => $this->riskLevel,
            'status'         => $this->status,
            'status_color'   => $this->getStatusColor(),
            'criteria'       => $this->screeningCriteria,
            'backtest'       => $this->backtestResults,
            'required_data'  => $this->requiredData,
            'sources'        => $this->sources,
        ];
    }

    protected function getStatusColor(): string
    {
        return match ($this->status) {
            'battle_tested'         => 'green',
            'promising'             => 'yellow',
            'needs_improvement'     => 'red',
            'active'                => 'accent',
            'recommended'           => 'green',
            'screening_tool'        => 'accent',
            default                 => 'blue',
        };
    }

    /**
     * Build backtest results array with defaults.
     */
    protected function buildBacktest(
        string $winRate = 'N/A',
        string $profitFactor = 'N/A',
        string $avgWin = 'N/A',
        string $avgLoss = 'N/A',
        int $totalTrades = 0,
        string $maxDrawdown = 'N/A',
        string $lastTested = '',
        string $testedBy = '',
        string $implications = '',
    ): array {
        return [
            'win_rate'     => $winRate,
            'profit_factor' => $profitFactor,
            'avg_win'      => $avgWin,
            'avg_loss'     => $avgLoss,
            'total_trades' => $totalTrades,
            'max_drawdown' => $maxDrawdown,
            'last_tested'  => $lastTested,
            'tested_by'    => $testedBy,
            'implications' => $implications,
        ];
    }
}
