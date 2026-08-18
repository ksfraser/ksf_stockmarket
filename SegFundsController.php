<?php
/**
 * SegFundsController — handles segregated fund listing, detail, and search.
 */
class SegFundsController {
    private $pdo;

    public function __construct() {
        $this->pdo = Database::get();
    }

    /**
     * GET /?action=seg_funds — List all seg funds with filters.
     */
    public function listFunds(string $carrier = '', string $category = '', string $series = '', string $search = '', string $sortBy = 'fund_name', string $sortDir = 'ASC'): array {
        $allowedSort = ['fund_name', 'carrier', 'fund_code', 'category', 'series', 'currency', 'asset_type', 'asset_class',
            'launch_date', 'aum_millions', 'mer', 'mer_pct', 'load_type', 'rrsp_eligible',
            'num_securities', 'pe', 'pb', 'eps_growth', 'div_yield', 'volatility',
            'nav', 'day_change_pct', 'week_pct', 'mtd_pct', 'ytd_pct', 'return_1mo', 'return_3mo',
            'return_1yr', 'return_3yr', 'return_5yr', 'return_10yr', 'return_15yr', 'return_inception',
            'quartile_ytd', 'quartile_1yr', 'quartile_3yr', 'quartile_5yr', 'quartile_10yr', 'quartile_15yr'];
        if (!in_array($sortBy, $allowedSort)) $sortBy = 'fund_name';
        $sortDir = strtoupper($sortDir) === 'DESC' ? 'DESC' : 'ASC';

        $where = ['is_active = 1'];
        $params = [];

        if ($carrier) {
            $where[] = 'carrier = :carrier';
            $params[':carrier'] = $carrier;
        }
        if ($category) {
            $where[] = 'category = :category';
            $params[':category'] = $category;
        }
        if ($series) {
            $where[] = 'series = :series';
            $params[':series'] = $series;
        }
        if ($search) {
            $where[] = '(fund_name LIKE :search1 OR carrier LIKE :search2)';
            $params[':search1'] = '%' . $search . '%';
            $params[':search2'] = '%' . $search . '%';
        }

        $whereSql = 'WHERE ' . implode(' AND ', $where);

        $sql = "SELECT id, fund_name, carrier, fund_code, category, series, currency, asset_type, asset_class,
                       launch_date, aum_millions, mer, mer_pct, load_type, rrsp_eligible,
                       num_securities, pe, pb, eps_growth, div_yield, volatility,
                       nav, day_change_dollars, day_change_pct, week_pct, mtd_pct, return_30day_pct, ytd_pct,
                       return_1mo, return_3mo, return_1yr, return_3yr, return_5yr, return_10yr, return_15yr, return_inception,
                       quartile_ytd, quartile_1yr, quartile_3yr, quartile_5yr, quartile_10yr, quartile_15yr,
                       pdf_path
                FROM seg_funds
                {$whereSql}
                ORDER BY {$sortBy} {$sortDir}
                LIMIT 500";

        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        $funds = $stmt->fetchAll();

        // Get filter options
        $carriers = $this->pdo->query("SELECT DISTINCT carrier FROM seg_funds WHERE is_active = 1 ORDER BY carrier")->fetchAll(PDO::FETCH_COLUMN);
        $categories = $this->pdo->query("SELECT DISTINCT category FROM seg_funds WHERE is_active = 1 ORDER BY category")->fetchAll(PDO::FETCH_COLUMN);
        $seriesList = $this->pdo->query("SELECT DISTINCT series FROM seg_funds WHERE is_active = 1 ORDER BY series")->fetchAll(PDO::FETCH_COLUMN);

        // Stats
        $totalActive = $this->pdo->query("SELECT COUNT(*) FROM seg_funds WHERE is_active = 1")->fetchColumn();
        $totalCarriers = count($carriers);

        return [
            'funds' => $funds,
            'carriers' => $carriers,
            'categories' => $categories,
            'seriesList' => $seriesList,
            'filter_carrier' => $carrier,
            'filter_category' => $category,
            'filter_series' => $series,
            'search' => $search,
            'sortBy' => $sortBy,
            'sortDir' => $sortDir,
            'total_active' => $totalActive,
            'total_carriers' => $totalCarriers,
        ];
    }

    /**
     * GET /?action=seg_fund_detail&id=XX — Single fund detail.
     */
    public function detail(int $id): array {
        $stmt = $this->pdo->prepare("SELECT * FROM seg_funds WHERE id = ?");
        $stmt->execute([$id]);
        $fund = $stmt->fetch();

        if (!$fund) {
            return ['error' => 'Fund not found', 'fund' => null, 'prices' => []];
        }

        // Get NAV history
        $priceStmt = $this->pdo->prepare(
            "SELECT price_date, nav FROM seg_fund_prices WHERE fund_id = ? ORDER BY price_date DESC LIMIT 100"
        );
        $priceStmt->execute([$id]);
        $prices = $priceStmt->fetchAll();

        return [
            'fund' => $fund,
            'prices' => $prices,
            'error' => null,
        ];
    }
}
