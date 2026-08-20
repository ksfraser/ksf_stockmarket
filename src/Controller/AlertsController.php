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
     * POST /?action=alerts_status — Update alert status (ack/ignore).
     */
    public function index(): array
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            return $this->updateStatus();
        }

        $jobs = $this->loadCronJobs();
        $summary = $this->computeSummary($jobs);
        $volumeSnapshots = $this->getVolumeSnapshotInfo($jobs);
        $priceAlerts = $this->getPriceAlertInfo($jobs);
        
        $watchlistSymbols = $this->loadWatchlistSymbols();
        $alertQueueCounts = $this->getAlertQueueCounts();
        $filter = $_GET['filter'] ?? '';
        $recentAlerts = $this->getRecentAlerts($filter === 'portfolio' ? 'portfolio' : null);

        return [
            'pageTitle'       => 'Alerts & Cron Status',
            'template'        => 'alerts_status',
            'jobs'            => $jobs,
            'summary'         => $summary,
            'volumeSnapshots' => $volumeSnapshots,
            'priceAlerts'     => $priceAlerts,
            'watchlistSymbols'=> $watchlistSymbols,
            'alertCounts'     => $alertQueueCounts,
            'recentAlerts'    => $recentAlerts,
            'filter'          => $filter,
        ];
    }

    private function updateStatus(): array
    {
        $alertId = trim((string)($_POST['alert_id'] ?? ''));
        $status = strtolower(trim((string)($_POST['status'] ?? '')));
        $allowed = ['ack', 'ignore'];

        if ($alertId === '' || !in_array($status, $allowed, true)) {
            return ['updateStatus' => 'missing'];
        }

        try {
            $pdo = Database::get();
            $stmt = $pdo->prepare("UPDATE alert_queue SET status = :status WHERE id = :id");
            $stmt->execute([':status' => $status, ':id' => $alertId]);
            return ['updateStatus' => $stmt->rowCount() > 0 ? 'ok' : 'missing'];
        } catch (Exception $e) {
            return ['updateStatus' => 'error'];
        }
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
                'last_run_at'  => $job['last_run_at'] ?? null,
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

    /**
     * Load watchlist_symbols from the database.
     */
    private function loadWatchlistSymbols(): array
    {
        try {
            $pdo = Database::get();
            $stmt = $pdo->query("
                SELECT symbol, list_type, monitor_volume, monitor_price,
                       volume_spike_threshold, alert_threshold_pct, notes, is_active
                FROM watchlist_symbols
                ORDER BY list_type, symbol
            ");
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }

    /**
     * Get alert_queue counts by status from MariaDB.
     */
    private function getAlertQueueCounts(): array
    {
        try {
            $pdo = Database::get();
            $stmt = $pdo->query("
                SELECT status, COUNT(*) as cnt 
                FROM alert_queue 
                GROUP BY status
            ");
            $counts = ['pending' => 0, 'completed' => 0, 'failed' => 0];
            foreach ($stmt->fetchAll() as $row) {
                $counts[$row['status']] = (int)$row['cnt'];
            }
            return $counts;
        } catch (Exception $e) {
            return ['pending' => 0, 'completed' => 0, 'failed' => 0];
        }
    }

    /**
     * Get recent triggered alerts from MariaDB (last 7 days).
     * Can filter by portfolio symbols if provided.
     */
    private function getRecentAlerts(?string $portfolioFilter = null): array
    {
        try {
            $pdo = Database::get();
            
            $sql = "
                SELECT id, symbol, alert_type, severity, payload, status, created_at, completed_at
                FROM alert_queue 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ";
            
            // Optional filter by portfolio symbols
            if ($portfolioFilter === 'portfolio') {
                $sql = "
                    SELECT aq.id, aq.symbol, aq.alert_type, aq.severity, aq.payload, aq.status, aq.created_at, aq.completed_at
                    FROM alert_queue aq
                    INNER JOIN portfolio_holdings ph ON aq.symbol = ph.symbol
                    WHERE aq.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ";
            }
            
            $sql .= " ORDER BY created_at DESC LIMIT 100";
            
            $stmt = $pdo->query($sql);
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }

    private function truncate(string $s, int $len): string
    {
        if (strlen($s) <= $len) return $s;
        return substr($s, 0, $len) . '…';
    }
}
