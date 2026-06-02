<?php

declare(strict_types=1);

use App\Strategy\StrategyRegistry;
use App\Strategy\StrategyFactory;

/**
 * AlertsController — Displays cron job / alert monitoring status.
 *
 * Reads the Hermes cron job configuration and displays:
 * - All registered cron jobs with their schedule, last run, status
 * - Summary counts by status (ok, error, paused, scheduled)
 * - Volume snapshot schedule info
 * - Price alert monitor status
 */
class AlertsController
{
    private string $cronJobsPath;

    public function __construct()
    {
        $this->cronJobsPath = '/root/.hermes/cron/jobs.json';
    }

    /**
     * GET /?action=alerts_status — Alerts and cron monitoring dashboard.
     */
    public function index(): array
    {
        $jobs = $this->loadCronJobs();
        $summary = $this->computeSummary($jobs);
        $volumeSnapshots = $this->getVolumeSnapshotInfo($jobs);
        $priceAlerts = $this->getPriceAlertInfo($jobs);

        return [
            'pageTitle'       => 'Alerts & Cron Status',
            'template'        => 'alerts_status',
            'jobs'            => $jobs,
            'summary'         => $summary,
            'volumeSnapshots' => $volumeSnapshots,
            'priceAlerts'     => $priceAlerts,
        ];
    }

    /**
     * Load cron jobs from Hermes JSON store.
     */
    private function loadCronJobs(): array
    {
        if (!file_exists($this->cronJobsPath)) {
            return [];
        }

        $raw = file_get_contents($this->cronJobsPath);
        if (!$raw) {
            return [];
        }

        $data = json_decode($raw, true);
        if (!$data || !isset($data['jobs'])) {
            return [];
        }

        $jobs = [];
        foreach ($data['jobs'] as $job) {
            $jobs[] = [
                'id'           => $job['job_id'] ?? '',
                'name'         => $job['name'] ?? 'Unnamed',
                'schedule'     => $job['schedule'] ?? '',
                'enabled'      => $job['enabled'] ?? false,
                'state'        => $job['state'] ?? 'unknown',
                'last_run'     => $this->formatTimestamp($job['last_run_at'] ?? null),
                'next_run'     => $this->formatTimestamp($job['next_run_at'] ?? null),
                'last_status'  => $job['last_status'] ?? 'never_run',
                'last_error'   => $job['last_delivery_error'] ?? null,
                'deliver'      => $job['deliver'] ?? 'origin',
                'prompt'       => $this->truncate($job['prompt_preview'] ?? '', 120),
            ];
        }

        // Sort: errors first, then by next run time
        usort($jobs, function (array $a, array $b): int {
            $statusOrder = ['error' => 0, 'paused' => 1, 'scheduled' => 2, 'ok' => 3, 'never_run' => 4];
            $aOrder = $statusOrder[$a['last_status']] ?? 5;
            $bOrder = $statusOrder[$b['last_status']] ?? 5;
            if ($aOrder !== $bOrder) return $aOrder - $bOrder;
            return strcmp($a['next_run'], $b['next_run']);
        });

        return $jobs;
    }

    /**
     * Compute summary counts.
     */
    private function computeSummary(array $jobs): array
    {
        $total  = count($jobs);
        $ok     = 0;
        $errors = 0;
        $paused = 0;
        $scheduled = 0;
        $never  = 0;

        foreach ($jobs as $job) {
            switch ($job['last_status']) {
                case 'ok':       $ok++;       break;
                case 'error':    $errors++;   break;
                case 'paused':   $paused++;   break;
                case 'scheduled': $scheduled++; break;
                default:         $never++;    break;
            }
        }

        return [
            'total'     => $total,
            'ok'        => $ok,
            'errors'    => $errors,
            'paused'    => $paused,
            'scheduled' => $scheduled,
            'never_run' => $never,
        ];
    }

    /**
     * Extract volume snapshot job info.
     */
    private function getVolumeSnapshotInfo(array $jobs): array
    {
        $snapshots = [];
        foreach ($jobs as $job) {
            if (stripos($job['name'], 'volume snapshot') !== false || stripos($job['name'], 'volume spike') !== false) {
                $snapshots[] = $job;
            }
        }
        return $snapshots;
    }

    /**
     * Extract price alert job info.
     */
    private function getPriceAlertInfo(array $jobs): array
    {
        $alerts = [];
        foreach ($jobs as $job) {
            if (stripos($job['name'], 'price alert') !== false || stripos($job['name'], 'watchlist') !== false) {
                $alerts[] = $job;
            }
        }
        return $alerts;
    }

    private function formatTimestamp(?string $ts): string
    {
        if (!$ts) return '—';
        try {
            $dt = new DateTime($ts);
            return $dt->format('Y-m-d H:i');
        } catch (Exception $e) {
            return $ts;
        }
    }

    private function truncate(string $s, int $len): string
    {
        if (strlen($s) <= $len) return $s;
        return substr($s, 0, $len) . '…';
    }
}
