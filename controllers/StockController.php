<?php
/**
 * StockController — handles all stock-related pages.
 */
class StockController {
    private $pdo;

    public function __construct() {
        $this->pdo = Database::get();
    }

    /**
     * GET /?action=list — List all symbols with latest price.
     */
    public function listSymbols(string $search = '', string $exchange = '', string $sortBy = 'symbol', string $sortDir = 'ASC'): array {
        $allowedSort = ['symbol','close','volume','change_pct','price_date'];
        if (!in_array($sortBy, $allowedSort)) $sortBy = 'symbol';
        $sortDir = strtoupper($sortDir) === 'DESC' ? 'DESC' : 'ASC';

        $where = [];
        $params = [];

        if ($search) {
            $where[] = "(sp.symbol LIKE :search OR sm.name LIKE :search)";
            $params[':search'] = '%' . $search . '%';
        }
        if ($exchange) {
            $where[] = "sm.exchange = :exchange";
            $params[':exchange'] = $exchange;
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        // Get previous close for change calculation
        $sql = "SELECT sp.symbol, sp.price_date, sp.close, sp.volume, sp.open, sp.high, sp.low,
                       sm.name, sm.exchange, sm.sector, sm.industry,
                       prev.close as prev_close
                FROM stockprices sp
                INNER JOIN (
                    SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol
                ) latest ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
                LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
                LEFT JOIN stockprices prev ON prev.symbol = sp.symbol
                    AND prev.price_date = (
                        SELECT MAX(price_date) FROM stockprices WHERE symbol = sp.symbol AND price_date < sp.price_date
                    )
                {$whereSql}
                ORDER BY {$sortBy} {$sortDir}
                LIMIT 200";

        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        $rows = $stmt->fetchAll();

        // Calculate change % for each
        foreach ($rows as &$row) {
            if ($row['prev_close'] && $row['prev_close'] > 0) {
                $row['change_pct'] = (($row['close'] - $row['prev_close']) / $row['prev_close']) * 100;
            } else {
                $row['change_pct'] = null;
            }
        }

        return $rows;
    }

    /**
     * GET /?action=detail&symbol=XXX — Single symbol detail page.
     */
    public function detail(string $symbol): array {
        $symbol = strtoupper(trim($symbol));

        // Latest info
        $stmt = $this->pdo->prepare("
            SELECT sp.*, sm.name, sm.exchange, sm.sector, sm.industry, sm.market_cap_weight
            FROM stockprices sp
            LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
            WHERE sp.symbol = :sym
            ORDER BY sp.price_date DESC
            LIMIT 1
        ");
        $stmt->execute([':sym' => $symbol]);
        $latest = $stmt->fetch();

        if (!$latest) {
            return ['error' => 'Symbol not found', 'symbol' => $symbol];
        }

        // 250 days of price history for charting
        $stmt = $this->pdo->prepare("
            SELECT price_date, open, high, low, close, volume
            FROM stockprices
            WHERE symbol = :sym
            ORDER BY price_date DESC
            LIMIT 250
        ");
        $stmt->execute([':sym' => $symbol]);
        $history = array_reverse($stmt->fetchAll());

        // Latest indicators
        $stmt = $this->pdo->prepare("
            SELECT price_date, data FROM indicators_json
            WHERE symbol = :sym
            ORDER BY price_date DESC
            LIMIT 1
        ");
        $stmt->execute([':sym' => $symbol]);
        $indRow = $stmt->fetch();
        $indicators = $indRow ? json_decode($indRow['data'], true) : [];

        // 30 days of key indicators for mini charts
        $stmt = $this->pdo->prepare("
            SELECT price_date, data FROM indicators_json
            WHERE symbol = :sym
            ORDER BY price_date DESC
            LIMIT 30
        ");
        $stmt->execute([':sym' => $symbol]);
        $indHistory = [];
        foreach (array_reverse($stmt->fetchAll()) as $row) {
            $d = json_decode($row['data'], true);
            $d['price_date'] = $row['price_date'];
            $indHistory[] = $d;
        }

        // Check if in portfolio
        $stmt = $this->pdo->prepare("SELECT * FROM portfolio WHERE symbol = :sym");
        $stmt->execute([':sym' => $symbol]);
        $portfolio = $stmt->fetch();

        // Year-to-date, 1-year performance
        $perf = $this->calcPerformance($symbol);

        return [
            'symbol' => $symbol,
            'latest' => $latest,
            'history' => $history,
            'indicators' => $indicators,
            'ind_history' => $indHistory,
            'portfolio' => $portfolio,
            'performance' => $perf,
        ];
    }

    /**
     * GET /?action=portfolio — Portfolio holdings.
     */
    public function portfolio(): array {
        $stmt = $this->pdo->query("
            SELECT p.*, sp.close as current_price, sp.volume as current_volume, sp.price_date as price_date
            FROM portfolio p
            LEFT JOIN stockprices sp ON p.symbol = sp.symbol
            LEFT JOIN (
                SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol
            ) latest ON sp.symbol = latest.symbol AND sp.price_date = latest.max_date
            ORDER BY p.symbol
        ");
        $holdings = $stmt->fetchAll();

        $totalCost = 0;
        $totalValue = 0;
        foreach ($holdings as &$h) {
            $h['cost_total'] = $h['shares'] * $h['cost_basis'];
            $h['current_value'] = $h['shares'] * ($h['current_price'] ?? 0);
            $h['pnl'] = $h['current_value'] - $h['cost_total'];
            $h['pnl_pct'] = $h['cost_total'] > 0 ? ($h['pnl'] / $h['cost_total']) * 100 : 0;
            $totalCost += $h['cost_total'];
            $totalValue += $h['current_value'];
        }

        return [
            'holdings' => $holdings,
            'total_cost' => $totalCost,
            'total_value' => $totalValue,
            'total_pnl' => $totalValue - $totalCost,
            'total_pnl_pct' => $totalCost > 0 ? (($totalValue - $totalCost) / $totalCost) * 100 : 0,
        ];
    }

    /**
     * GET /?action=chart&symbol=XXX — Chart data as JSON.
     */
    public function chartData(string $symbol, int $days = 250): array {
        $stmt = $this->pdo->prepare("
            SELECT price_date, open, high, low, close, volume
            FROM stockprices
            WHERE symbol = :sym
            ORDER BY price_date DESC
            LIMIT :limit
        ");
        $stmt->bindValue(':sym', $symbol);
        $stmt->bindValue(':limit', $days, PDO::PARAM_INT);
        $stmt->execute();
        return array_reverse($stmt->fetchAll());
    }

    /**
     * GET /?action=indicators&symbol=XXX — Indicator detail page.
     */
    public function indicatorDetail(string $symbol): array {
        return $this->detail($symbol); // Same data, different template
    }

    private function calcPerformance(string $symbol): array {
        $stmt = $this->pdo->prepare("
            SELECT close, price_date FROM stockprices
            WHERE symbol = :sym ORDER BY price_date DESC
        ");
        $stmt->execute([':sym' => $symbol]);
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $perf = ['ytd' => null, '1y' => null, '3y' => null, '5y' => null, '10y' => null];
        if (empty($rows)) return $perf;

        $latest = $rows[0]['close'];
        $latestDate = $rows[0]['price_date'];

        foreach ($rows as $row) {
            $daysAgo = (strtotime($latestDate) - strtotime($row['price_date'])) / 86400;
            if ($perf['1y'] === null && $daysAgo >= 365) {
                $perf['1y'] = (($latest / $row['close']) - 1) * 100;
            }
            if ($perf['3y'] === null && $daysAgo >= 1095) {
                $perf['3y'] = (($latest / $row['close']) - 1) * 100;
            }
            if ($perf['5y'] === null && $daysAgo >= 1825) {
                $perf['5y'] = (($latest / $row['close']) - 1) * 100;
            }
            if ($perf['10y'] === null && $daysAgo >= 3650) {
                $perf['10y'] = (($latest / $row['close']) - 1) * 100;
            }
        }

        // YTD
        $stmt = $this->pdo->prepare("
            SELECT close FROM stockprices
            WHERE symbol = :sym AND price_date <= :yearStart
            ORDER BY price_date DESC LIMIT 1
        ");
        $yearStart = date('Y') . '-01-01';
        $stmt->execute([':sym' => $symbol, ':yearStart' => $yearStart]);
        $ytdRow = $stmt->fetch();
        if ($ytdRow) {
            $perf['ytd'] = (($latest / $ytdRow['close']) - 1) * 100;
        }

        return $perf;
    }
}
