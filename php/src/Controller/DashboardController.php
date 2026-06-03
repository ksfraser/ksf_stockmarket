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

        // Top gainers — ALL symbols (app level)
        $gainers = $this->pdo->query("
            SELECT sp.symbol, sp.close, sp.volume, sm.name,
                   prev.close as prev_close,
                   CASE WHEN prev.close > 0 THEN ((sp.close - prev.close) / prev.close * 100) ELSE 0 END as change_pct
            FROM stockprices sp
            INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
            LEFT JOIN stockprices prev ON prev.symbol = sp.symbol
                AND prev.price_date = (SELECT MAX(price_date) FROM stockprices WHERE symbol = sp.symbol AND price_date < sp.price_date)
            WHERE prev.close > 0
            ORDER BY change_pct DESC
            LIMIT 10
        ")->fetchAll();

        // Top losers — ALL symbols (app level)
        $losers = $this->pdo->query("
            SELECT sp.symbol, sp.close, sp.volume, sm.name,
                   prev.close as prev_close,
                   CASE WHEN prev.close > 0 THEN ((sp.close - prev.close) / prev.close * 100) ELSE 0 END as change_pct
            FROM stockprices sp
            INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) latest
                ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
            LEFT JOIN stockprices prev ON prev.symbol = sp.symbol
                AND prev.price_date = (SELECT MAX(price_date) FROM stockprices WHERE symbol = sp.symbol AND price_date < sp.price_date)
            WHERE prev.close > 0
            ORDER BY change_pct ASC
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
            'stats'       => $stats,
            'gainers'     => $gainers,
            'losers'      => $losers,
            'freshness'   => $freshness,
            'last_update' => date('Y-m-d H:i:s'),
        ];
    }
}
