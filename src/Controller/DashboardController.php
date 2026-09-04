<?php
/**
 * DashboardController — APP LEVEL overview/dashboard data.
 * Provides system-wide stats: all symbols, all gainers/losers, full coverage.
 */
class DashboardController {
    private $pdo;

    public function __construct() {
        $this->pdo = Database::get();
    }

    /**
     * GET /?action=overview — App-level dashboard stats, gainers, losers, freshness.
     */
    public function overview(): array {
        // Summary stats — ALL symbols (app level, no portfolio data)
        $stats = [
            'total_symbols'       => $this->pdo->query("SELECT COUNT(DISTINCT symbol) FROM stockprices")->fetchColumn(),
            'with_indicators'     => $this->pdo->query("SELECT COUNT(DISTINCT symbol) FROM indicators_json")->fetchColumn(),
            'total_prices'        => $this->pdo->query("SELECT COUNT(*) FROM stockprices")->fetchColumn(),
            'total_indicators'    => $this->pdo->query("SELECT COUNT(*) FROM indicators_json")->fetchColumn(),
            'active_fetching'     => $this->pdo->query("SELECT COUNT(*) FROM symbol_master WHERE is_active = 1")->fetchColumn(),
            'last_update'         => date('Y-m-d H:i:s'),
        ];

        // Recency window — only count symbols whose LATEST price_date is within the
        // last N business days. Prevents stale "gainers" from illiquid / delisted tickers
        // (e.g. RNK, which last traded years ago) from polluting the dashboard.
        // 5 business days ≈ 7 calendar days, with a buffer to 10 to be safe over long weekends.
        $recencyCutoff = date('Y-m-d', strtotime('-10 days'));

        // Top gainers — ALL symbols (app level), recent only
        $gainers = $this->pdo->prepare("
            SELECT sp.symbol, sp.close, sp.volume, sm.name,
                   prev.close as prev_close,
                   CASE WHEN prev.close > 0 THEN ((sp.close - prev.close) / prev.close * 100) ELSE 0 END as change_pct,
                   sp.price_date as price_date,
                   prev.price_date as prev_date,
                   sm.is_active
            FROM stockprices sp
            INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
            LEFT JOIN stockprices prev ON prev.symbol = sp.symbol
                AND prev.price_date = (SELECT MAX(price_date) FROM stockprices
                                        WHERE symbol = sp.symbol
                                          AND price_date < sp.price_date
                                          AND price_date >= DATE_SUB(sp.price_date, INTERVAL 14 DAY))
            WHERE prev.close > 0
              AND sp.price_date >= :cutoff
              AND sp.close > 0
              AND COALESCE(sm.is_active, 1) = 1
            ORDER BY change_pct DESC
            LIMIT 10
        ");
        $gainers->execute([':cutoff' => $recencyCutoff]);
        $gainers = $gainers->fetchAll();

        // Top losers — ALL symbols (app level), recent only
        $losers = $this->pdo->prepare("
            SELECT sp.symbol, sp.close, sp.volume, sm.name,
                   prev.close as prev_close,
                   CASE WHEN prev.close > 0 THEN ((sp.close - prev.close) / prev.close * 100) ELSE 0 END as change_pct,
                   sp.price_date as price_date,
                   prev.price_date as prev_date,
                   sm.is_active
            FROM stockprices sp
            INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
            LEFT JOIN stockprices prev ON prev.symbol = sp.symbol
                AND prev.price_date = (SELECT MAX(price_date) FROM stockprices
                                        WHERE symbol = sp.symbol
                                          AND price_date < sp.price_date
                                          AND price_date >= DATE_SUB(sp.price_date, INTERVAL 14 DAY))
            WHERE prev.close > 0
              AND sp.price_date >= :cutoff
              AND sp.close > 0
              AND COALESCE(sm.is_active, 1) = 1
            ORDER BY change_pct ASC
            LIMIT 10
        ");
        $losers->execute([':cutoff' => $recencyCutoff]);
        $losers = $losers->fetchAll();

        // Data freshness
        $freshness = $this->pdo->query("
            SELECT
                COUNT(CASE WHEN sp.price_date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY) THEN 1 END) as fresh,
                COUNT(CASE WHEN sp.price_date < DATE_SUB(CURDATE(), INTERVAL 3 DAY) THEN 1 END) as stale
            FROM stockprices sp
            INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
        ")->fetch();

        return [
            'stats'       => $stats,
            'gainers'     => $gainers,
            'losers'      => $losers,
            'freshness'   => $freshness,
            'last_update' => date('Y-m-d H:i:s'),
            'symbol_quality' => [
                'dead_names'     => (int)$this->pdo->query("SELECT COUNT(*) FROM symbol_master WHERE name LIKE '%(no data)%'")->fetchColumn(),
                'null_exchanges' => (int)$this->pdo->query("SELECT COUNT(*) FROM symbol_master WHERE exchange IS NULL OR exchange = ''")->fetchColumn(),
                'needs_review'   => (int)$this->pdo->query("SELECT COUNT(*) FROM symbol_master WHERE name LIKE '%(no data)%' OR exchange IS NULL OR exchange = ''")->fetchColumn(),
            ],
        ];
    }

    /** Performance math for each active portfolio (thin wrapper over ksfraser/portfolio-math). */
    private function portfolioPerformance(): array
    {
        if (!class_exists('App\Performance\Service\PerformanceService')) {
            return []; // composer dependency not installed
        }
        try {
            $svc = new \App\Performance\Service\PerformanceService();
            $end = date('Y-m-d');
            $start = date('Y-m-d', strtotime('-1 year'));
            $accounts = ['TFSA', 'RRSP', 'MARGIN'];
            $out = [];
            foreach ($accounts as $acct) {
                $out[$acct] = [
                    'twr'       => $svc->twr($acct, $start, $end),
                    'irr'       => $svc->irr($acct, $start, $end),
                    'drawdown'  => $svc->drawdown($acct, $start, $end),
                    'volatility'=> $svc->volatility($acct, $start, $end),
                ];
            }
            return $out;
        } catch (\Throwable $e) {
            // Log but don't break the dashboard
            error_log('PerformanceService failed: ' . $e->getMessage() . "\n" . $e->getTraceAsString());
            return ['error' => $e->getMessage()];
        }
    }
}
