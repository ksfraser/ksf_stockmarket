<?php
/**
 * DashboardController — overview/home page data.
 */
class DashboardController {
    private $pdo;

    public function __construct() {
        $this->pdo = Database::get();
    }

    public function overview(): array {
        // Portfolio summary
        $port = $this->pdo->query("
            SELECT p.*, sp.close as current_price
            FROM portfolio p
            LEFT JOIN stockprices sp ON p.symbol = sp.symbol
            LEFT JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            ORDER BY p.symbol
        ")->fetchAll();

        $totalCost = 0;
        $totalValue = 0;
        foreach ($port as $h) {
            $totalCost += $h['shares'] * $h['cost_basis'];
            $totalValue += $h['shares'] * ($h['current_price'] ?? 0);
        }

        // Summary stats
        $stats = [
            'total_symbols' => $this->pdo->query("SELECT COUNT(DISTINCT symbol) FROM stockprices")->fetchColumn(),
            'with_indicators' => $this->pdo->query("SELECT COUNT(DISTINCT symbol) FROM indicators_json")->fetchColumn(),
            'total_prices' => number_format($this->pdo->query("SELECT COUNT(*) FROM stockprices")->fetchColumn()),
            'portfolio_holdings' => count($port),
            'portfolio_cost' => $totalCost,
            'portfolio_value' => $totalValue,
            'portfolio_pnl' => $totalValue - $totalCost,
        ];

        // Top movers today
        $gainers = $this->pdo->query("
            SELECT sp.symbol, sp.close, sp.volume, prev.close as prev_close,
                   ((sp.close - prev.close) / prev.close * 100) as change_pct
            FROM stockprices sp
            INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            LEFT JOIN stockprices prev ON prev.symbol = sp.symbol
                AND prev.price_date = (SELECT MAX(price_date) FROM stockprices WHERE symbol = sp.symbol AND price_date < sp.price_date)
            WHERE prev.close > 0
            ORDER BY change_pct DESC
            LIMIT 10
        ")->fetchAll();

        $losers = $this->pdo->query("
            SELECT sp.symbol, sp.close, sp.volume, prev.close as prev_close,
                   ((sp.close - prev.close) / prev.close * 100) as change_pct
            FROM stockprices sp
            INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            LEFT JOIN stockprices prev ON prev.symbol = sp.symbol
                AND prev.price_date = (SELECT MAX(price_date) FROM stockprices WHERE symbol = sp.symbol AND price_date < sp.price_date)
            WHERE prev.close > 0
            ORDER BY change_pct ASC
            LIMIT 10
        ")->fetchAll();

        // Most active by volume
        $active = $this->pdo->query("
            SELECT sp.symbol, sp.close, sp.volume
            FROM stockprices sp
            INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            ORDER BY sp.volume DESC
            LIMIT 10
        ")->fetchAll();

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
            'stats' => $stats,
            'portfolio' => $port,
            'gainers' => $gainers,
            'losers' => $losers,
            'active' => $active,
            'freshness' => $freshness,
            'last_update' => date('Y-m-d H:i:s'),
        ];
    }
}
