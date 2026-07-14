<?php
/**
 * ATRSweepController — best ATR stop factor per symbol + portfolio stats + charts.
 */

class ATRSweepController {
    private $pdo;
    /** @var SymbolResolver */
    private $resolver;

    public function __construct() {
        $this->pdo = Database::get();
        $this->resolver = new SymbolResolver($this->pdo);
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

    /**
     * GET /?action=atr_sweep&symbol=XXX — Generate ATR stop optimization chart.
     * Uses resolver so Canadian symbols hit the canonical DB symbol.
     */
    public function chart(): void {
        $raw = strtoupper(trim($_GET['symbol'] ?? ''));
        $symbol = $this->resolver->resolve($raw);
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

    /**
     * Get best/second best/worst/second worst ATR params for a symbol.
     */
    private function getBestParams(string $symbol): ?array {
        $stmt = $this->pdo->prepare("
            SELECT stop_factor, trailing_pct, pnl_pct, n_trades, win_rate, avg_win, avg_loss, expectancy
            FROM atr_stop_optimization
            WHERE symbol = :s
            ORDER BY pnl_pct DESC
            LIMIT 1
        ");
        $stmt->execute([':s' => $symbol]);
        $row = $stmt->fetch();
        if (!$row) return null;

        $second = $this->getRanked($symbol, 2);
        $worst = $this->getRanked($symbol, -1);
        $secondWorst = $this->getRanked($symbol, -2);

        return [
            'symbol' => $symbol,
            'best' => $row,
            'second_best' => $second,
            'worst' => $worst,
            'second_worst' => $secondWorst,
        ];
    }

    private function getRanked(string $symbol, int $rank): ?array {
        $dir = $rank > 0 ? 'ASC' : 'DESC';
        $offset = abs($rank) - 1;
        $stmt = $this->pdo->prepare("
            SELECT stop_factor, trailing_pct, pnl_pct, n_trades, win_rate, expectancy
            FROM atr_stop_optimization
            WHERE symbol = :s
            ORDER BY pnl_pct " . $dir . "
            LIMIT 1 OFFSET " . (int)$offset
        );
        $stmt->execute([':s' => $symbol]);
        return $stmt->fetch() ?: null;
    }

    private function aggregateStats(array $items): array {
        if (empty($items)) {
            return ['symbols' => 0, 'avg_best_pnl_pct' => 0, 'avg_n_trades' => 0];
        }
        $pnls = [];
        $trades = [];
        foreach ($items as $item) {
            if (!empty($item['best'])) {
                $pnls[] = (float)$item['best']['pnl_pct'];
                $trades[] = (int)$item['best']['n_trades'];
            }
        }
        return [
            'symbols' => count($items),
            'avg_best_pnl_pct' => count($pnls) ? array_sum($pnls) / count($pnls) : 0,
            'avg_n_trades' => count($trades) ? array_sum($trades) / count($trades) : 0,
            'min_best_pnl_pct' => count($pnls) ? min($pnls) : 0,
            'max_best_pnl_pct' => count($pnls) ? max($pnls) : 0,
        ];
    }
}
