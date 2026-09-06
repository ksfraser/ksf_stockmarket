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
     * Supports BR-11/FR-11 risk_rating, death_pct, mat_pct, and bucket_1y/5y/10y/ytd.
     */
    public function listFunds(
        string $carrier = '',
        string $category = '',
        string $series = '',
        string $search = '',
        string $sortBy = 'fund_name',
        string $sortDir = 'ASC',
        array  $risk_rating = [],
        array  $death_pct = [],
        array  $mat_pct = [],
        string $bucket_1y = '',
        string $bucket_5y = '',
        string $bucket_10y = '',
        string $bucket_ytd = ''
    ): array {
        $allowedSort = ['fund_name', 'carrier', 'category', 'series', 'mer', 'return_1yr', 'return_3yr', 'return_5yr', 'return_10yr', 'risk_rating', 'death_benefit_pct', 'maturity_benefit_pct'];
        if (!in_array($sortBy, $allowedSort)) $sortBy = 'fund_name';
        $sortDir = strtoupper($sortDir) === 'DESC' ? 'DESC' : 'ASC';

        $filterSpec = [
            'carrier'     => $carrier,
            'category'    => $category,
            'series'      => $series,
            'search'      => $search,
            'risk_rating' => $risk_rating,
            'death_pct'   => $death_pct,
            'mat_pct'     => $mat_pct,
        ];

        $built = SegFundFilter::buildWhere($filterSpec);
        $whereSql = $built['where'];
        $params = $built['params'];

        // Bucket filters: resolve label → NTILE(5) range, append extra clause
        $bucketSelections = [
            'bucket_1y'  => $bucket_1y,
            'bucket_5y'  => $bucket_5y,
            'bucket_10y' => $bucket_10y,
            'bucket_ytd' => $bucket_ytd,
        ];
        $bucketExtra = [];   // for boundary computation
        $bucketApplied = []; // for UI display
        foreach ($bucketSelections as $key => $label) {
            if (!$label) continue;
            // Recompute boundaries over the universe WITHOUT the current bucket (others still apply)
            $boundaries = SegFundFilter::bucketBoundaries($this->pdo, SegFundFilter::BUCKET_COLS[$key], $built['has'] ? substr($whereSql, 6) : '');
            $resolved = SegFundFilter::resolveBucket($key, $label, $boundaries);
            if (!$resolved) continue;
            $col = $resolved['col'];
            $lo  = $resolved['lo'];
            $hi  = $resolved['hi'];
            $ph  = ':' . $key . '_lo';
            $ph2 = ':' . $key . '_hi';
            $clause = "({$col} >= {$ph} AND {$col} <= {$ph2})";
            $bucketExtra[] = $clause;
            $params[$ph]  = $lo;
            $params[$ph2] = $hi;
            $bucketApplied[$key] = [
                'col' => $col, 'lo' => $lo, 'hi' => $hi, 'label' => $label, 'boundaries' => $boundaries,
            ];
        }
        if ($bucketExtra) {
            $whereSql = $whereSql
                ? $whereSql . ' AND ' . implode(' AND ', $bucketExtra)
                : 'WHERE ' . implode(' AND ', $bucketExtra);
        }

        $sql = "SELECT id, fund_name, carrier, category, series, mer,
                       risk_rating, death_benefit_pct, maturity_benefit_pct,
                       return_1yr, return_3yr, return_5yr, return_10yr, ytd_pct
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
        $seriesList = $this->pdo->query("SELECT DISTINCT series FROM seg_funds WHERE is_active = 1 AND series IS NOT NULL ORDER BY series")->fetchAll(PDO::FETCH_COLUMN);

        // Stats
        $totalActive = $this->pdo->query("SELECT COUNT(*) FROM seg_funds WHERE is_active = 1")->fetchColumn();
        $totalCarriers = count($carriers);

        // Bucket boundaries for all four return cols (universe = full active; UI shows labels)
        $bucketLabels = [];
        foreach (SegFundFilter::BUCKET_COLS as $key => $col) {
            $bucketLabels[$key] = SegFundFilter::bucketBoundaries($this->pdo, $col, '');
        }

        return [
            'funds' => $funds,
            'carriers' => $carriers,
            'categories' => $categories,
            'seriesList' => $seriesList,
            'filter_carrier' => $carrier,
            'filter_category' => $category,
            'filter_series' => $series,
            'search' => $search,
            'filter_risk_rating' => $risk_rating,
            'filter_death_pct'   => $death_pct,
            'filter_mat_pct'     => $mat_pct,
            'filter_bucket_1y'   => $bucket_1y,
            'filter_bucket_5y'   => $bucket_5y,
            'filter_bucket_10y'  => $bucket_10y,
            'filter_bucket_ytd'  => $bucket_ytd,
            'bucket_labels'      => $bucketLabels,
            'bucket_applied'     => $bucketApplied,
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

    /**
     * GET /?action=seg_fund_lira — LIRA/LRSP seg-fund screener.
     * Ranks equity seg funds for retirement-account use: 10y/5y returns,
     * max-drawdown risk, dedupes to one series per (carrier, fund), then
     * aggregates to a carrier score across CA / US / INTL geographies.
     *
     * @param string $horizon '10y' (default) or '5y' — controls which return
     *                        column is used for ranking and which minimum
     *                        track-record is required.
     */
    public function liraScreener(int $age = 52, float $principal = 200000.0, string $horizon = '10y'): array {
        $returnCol = $horizon === '5y' ? 's.ret_5y' : 's.ret_10y';
        $horizonLabel = $horizon === '5y' ? '5-Year' : '10-Year';

        // Geography buckets: all equity seg funds, then bucket by category_raw
        $sql = "
            SELECT
                c.name AS carrier,
                c.carrier_id,
                f.fund_id,
                s.series_id,
                s.fund_name,
                s.series_code,
                s.mer,
                m.category_raw,
                m.max_drawdown,
                m.volatility_rating,
                $returnCol AS ret_horizon,
                s.ret_5y,
                s.ret_10y
            FROM seg_fund_screen s
            JOIN seg_fund_metrics m ON s.series_id = m.series_id
            JOIN funds f ON s.fund_id = f.fund_id
            JOIN carriers c ON f.carrier_id = c.carrier_id
            WHERE s.eligible = 1
              AND s.base_class = 1
              AND $returnCol IS NOT NULL AND $returnCol > 0
              AND m.max_drawdown IS NOT NULL AND m.max_drawdown > 0
              AND m.category = 'Equity'
        ";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute();
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // Bucket by geography using category_raw heuristics
        $buckets = ['CA' => [], 'US' => [], 'INTL' => []];
        foreach ($rows as $r) {
            $cat = strtolower($r['category_raw'] ?? '');
            if (str_contains($cat, 'canadian')) {
                $buckets['CA'][] = $r;
            } elseif (str_contains($cat, 'u.s.') || preg_match('/\bus\b/', $cat)) {
                $buckets['US'][] = $r;
            } elseif (str_contains($cat, 'international') || str_contains($cat, 'foreign') ||
                       str_contains($cat, 'global') || str_contains($cat, 'european') ||
                       str_contains($cat, 'emerging')) {
                $buckets['INTL'][] = $r;
            } else {
                // Unmapped equity defaults to INTL for diversification
                $buckets['INTL'][] = $r;
            }
        }

        // Dedupe: keep the highest risk-adjusted (ret_horizon / max_drawdown) per (carrier, fund)
        $ranked = ['CA' => [], 'US' => [], 'INTL' => []];
        foreach ($buckets as $geo => $list) {
            $best = [];
            foreach ($list as $r) {
                $key = $r['carrier'] . '||' . $r['fund_name'];
                $ra = $r['max_drawdown'] > 0 ? $r['ret_horizon'] / $r['max_drawdown'] : 0;
                $r['risk_adj'] = round($ra, 3);
                $r['return_label'] = $horizonLabel;
                if (!isset($best[$key]) || $r['risk_adj'] > $best[$key]['risk_adj']) {
                    $best[$key] = $r;
                }
            }
            usort($best, fn($a, $b) => $b['risk_adj'] <=> $a['risk_adj']);
            $ranked[$geo] = array_values($best);
        }

        // Aggregate per carrier: requires all 3 geographies, score = mean of top-fund RA
        $carriers = [];
        foreach (array_merge($ranked['CA'], $ranked['US'], $ranked['INTL']) as $r) {
            $c = $r['carrier'];
            if (!isset($carriers[$c])) $carriers[$c] = ['CA'=>null,'US'=>null,'INTL'=>null];
        }
        foreach ($ranked as $geo => $list) {
            foreach ($list as $r) {
                $c = $r['carrier'];
                if ($carriers[$c][$geo] === null) $carriers[$c][$geo] = $r;
            }
        }
        $carrierScores = [];
        foreach ($carriers as $name => $geoPicks) {
            if ($geoPicks['CA'] && $geoPicks['US'] && $geoPicks['INTL']) {
                $avgRa = ($geoPicks['CA']['risk_adj'] + $geoPicks['US']['risk_adj'] + $geoPicks['INTL']['risk_adj']) / 3;
                $avgMer = ($geoPicks['CA']['mer'] + $geoPicks['US']['mer'] + $geoPicks['INTL']['mer']) / 3;
                $carrierScores[] = [
                    'carrier' => $name,
                    'avg_risk_adj' => round($avgRa, 3),
                    'avg_mer' => round($avgMer, 2),
                    'ca' => $geoPicks['CA'],
                    'us' => $geoPicks['US'],
                    'intl' => $geoPicks['INTL'],
                ];
            }
        }
        usort($carrierScores, fn($a, $b) => $b['avg_risk_adj'] <=> $a['avg_risk_adj']);

        return [
            'ranked' => $ranked,
            'carriers' => $carrierScores,
            'age' => $age,
            'principal' => $principal,
            'allocation' => ['CA' => 0.60, 'US' => 0.25, 'INTL' => 0.15],
            'runway' => 10,
            'horizon' => $horizon,
            'horizon_label' => $horizonLabel,
        ];
    }
}
