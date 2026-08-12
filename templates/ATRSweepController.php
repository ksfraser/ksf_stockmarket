<?php
/**
 * ATRSweepController — best ATR stop factor per symbol + portfolio stats + charts.
 */

class ATRSweepController {
    private $pdo;

    public function __construct() {
        $this->pdo = Database::get();
    }

    /**
     * get best/second best/worst/second worst per symbol
     * and aggregate stats across portfolio + all symbols.
     */
    public function index(): array {
        $symbols = $this->getPortfolioSymbols();
        $all = $this->getAllSweepSymbols();

        $perSymbol = [];
        foreach ($symbols as $sym) {
            $perSymbol[$sym] = $this->getBestParams($sym);
        }

        $allSymbolStats = [];
        foreach ($all as $sym) {
            $allSymbolStats[$sym] = $this->getBestParams($sym);
        }

        $portfolioStats = $this->aggregateStats(array_filter($perSymbol));
        $allStats = $this->aggregateStats(array_filter($allSymbolStats));

        return [
            'pageTitle' => 'ATR Stop Optimization',
            'template' => 'atr_sweep',
            'portfolio_symbols' => $symbols,
            'per_symbol' => $perSymbol,
            'all_symbols' => $all,
            'all_symbol_stats' => $allSymbolStats,
            'portfolio_stats' => $portfolioStats,
            'all_stats' => $allStats,
        ];
    }

    public function chart(): void {
        $symbol = strtoupper(trim($_GET['symbol'] ?? ''));
        if (!$symbol) {
            http_response_code(400);
            echo 'Missing symbol';
            return;
        }

        $script = '/home/ksf_stockmarket/ksf_stockmarket/python/generate_atr_chart.py';
        if (!is_file($script)) {
            http_response_code(500);
            echo 'Chart generator not found';
            return;
        }

        $tmp = sys_get_temp_dir() . '/atr_chart_' . md5($symbol . date('YmdHis')) . '.png';
        $cmd = escapeshellcmd('python3') . ' ' . escapeshellarg($script) . ' ' . escapeshellarg($symbol) . ' ' . escapeshellarg($tmp) . ' 2>&1';
        exec($cmd, $output, $rc);

        if ($rc !== 0 || !is_file($tmp)) {
            http_response_code(500);
            echo 'Chart generation failed: ' . htmlspecialchars(implode("\n", $output));
            return;
        }

        header('Content-Type: image/png');
        header('Content-Length: ' . filesize($tmp));
        readfile($tmp);
        @unlink($tmp);
    }

    private function getPortfolioSymbols(): array {
        try {
            $stmt = $this->pdo->query("SELECT DISTINCT symbol FROM portfolio WHERE shares > 0 ORDER BY symbol");
            return array_column($stmt->fetchAll(), 'symbol');
        } catch (Exception $e) {
            return [];
        }
    }

    private function getAllSweepSymbols(): array {
        try {
            $stmt = $this->pdo->query("SELECT DISTINCT symbol FROM atr_stop_optimization ORDER BY symbol");
            return array_column($stmt->fetchAll(), 'symbol');
        } catch (Exception $e) {
            return [];
        }
    }

    private function getBestParams(string $symbol): ?array {
        try {
            $stmt = $this->pdo->prepare("
                SELECT atr_multiple, n_drops, bounce_back_rate, avg_recovery_days,
                       max_drawdown_atr, recommended
                FROM atr_stop_optimization
                WHERE symbol = :s
                ORDER BY recommended DESC, atr_multiple ASC
                LIMIT 1
            ");
            $stmt->execute([':s' => $symbol]);
            $rec = $stmt->fetch();
            if (!$rec) return null;
            return [
                'symbol' => $symbol,
                'recommended' => $rec,
                'at_2_0' => $this->getAtMultiple($symbol, 2.0),
                'at_2_5' => $this->getAtMultiple($symbol, 2.5),
            ];
        } catch (Exception $e) {
            return null;
        }
    }

    private function getAtMultiple(string $symbol, float $m): ?array {
        $stmt = $this->pdo->prepare("
            SELECT atr_multiple, n_drops, bounce_back_rate, avg_recovery_days
            FROM atr_stop_optimization
            WHERE symbol = :s AND atr_multiple = :m
            LIMIT 1
        ");
        $stmt->execute([':s' => $symbol, ':m' => $m]);
        return $stmt->fetch() ?: null;
    }

    private function aggregateStats(array $items): array {
        if (empty($items)) {
            return ['symbols' => 0, 'avg_recommended_multiple' => 0, 'avg_max_drawdown_atr' => 0];
        }
        $recs = [];
        $dds = [];
        foreach ($items as $item) {
            if (!empty($item['recommended'])) {
                $recs[] = (float)$item['recommended']['atr_multiple'];
                if (isset($item['recommended']['max_drawdown_atr'])) {
                    $dds[] = (float)$item['recommended']['max_drawdown_atr'];
                }
            }
        }
        return [
            'symbols' => count($items),
            'avg_recommended_multiple' => $recs ? array_sum($recs) / count($recs) : 0,
            'avg_max_drawdown_atr' => $dds ? array_sum($dds) / count($dds) : 0,
        ];
    }
}
