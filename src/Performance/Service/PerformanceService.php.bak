<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Service;



/**
 * Thin wrapper: stockmarket app entry point into portfolio-math.
 *
 * All calculation logic lives in ksfraser/portfolio-math.
 * This class only adapts the stockmarket repository and formats results.
 */
class only adapts the stockmarket repository and formats results.
 */
class PerformanceService
{
    private TransactionRepositoryInterface $repo;

    public function __construct(int $userId = 0)
    {
        $repo = new StockmarketPerformanceRepository();
        $this->repo = $repo;
        if ($userId > 0) {
            // Set user scope on repository if it supports it
            if (method_exists($repo, 'setUserId')) {
                $repo->setUserId($userId);
            }
        }
    }

    public function twr(string $accountType, string $start, string $end): ?array
    {
        try {
            $svc = new TWRCalculatorService($this->repo);
            $result = $svc->calculate($accountType, $start, $end);
            return [
                'twr'            => $result->getTWR(),
                'annualized_twr' => $result->getAnnualizedTWR(),
                'days'           => $result->getDays(),
                'deltas'         => $result->getDeltas(),
                'accumulated'    => $result->getAccumulated(),
            ];
        } catch (\KSF\Performance\Exceptions\InsufficientDataException $e) {
            return null;
        }
    }

    public function irr(string $accountType, string $start, string $end): ?array
    {
        try {
            $svc = new IRRCalculatorService($this->repo);
            $result = $svc->calculate($accountType, $start, $end);
            return [
                'irr'        => $result->getIRR(),
                'iterations' => $result->getIterations(),
                'cashflows'  => $result->getCashflows(),
                'currency'   => $result->getCurrency(),
            ];
        } catch (\KSF\Performance\Exceptions\InsufficientDataException $e) {
            return null;
        } catch (\KSF\Performance\Exceptions\ConvergenceException $e) {
            return null;
        }
    }

    public function drawdown(string $accountType, string $start, string $end): ?array
    {
        try {
            $svc = new DrawdownCalculatorService($this->repo);
            $result = $svc->calculate($accountType, $start, $end);
            return [
                'max_drawdown'  => $result->getMaxDrawdown(),
                'peak_date'     => $result->getPeakDate()?->format('Y-m-d'),
                'trough_date'   => $result->getTroughDate()?->format('Y-m-d'),
                'recovery_days' => $result->getRecoveryDays(),
                'series'        => $result->getDrawdownSeries(),
            ];
        } catch (\KSF\Performance\Exceptions\InsufficientDataException $e) {
            return null;
        }
    }

    public function volatility(string $accountType, string $start, string $end): ?array
    {
        try {
            $svc = new VolatilityCalculatorService($this->repo);
            $result = $svc->calculate($accountType, $start, $end);
            return [
                'std_deviation'         => $result->getStdDeviation(),
                'semi_deviation'        => $result->getSemiDeviation(),
                'annualized_std_dev'    => $result->getAnnualizedStdDeviation(),
                'annualized_semi_dev'   => $result->getAnnualizedSemiDeviation(),
            ];
        } catch (\KSF\Performance\Exceptions\InsufficientDataException $e) {
            return null;
        }
    }
}
