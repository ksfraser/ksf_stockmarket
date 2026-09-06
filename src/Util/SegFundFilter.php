<?php
/**
 * SegFundFilter — encapsulates filter spec parsing, bucket boundary computation,
 * and WHERE-clause building for the seg_funds list (BR-11, FR-11).
 *
 * Bucket ranges are computed from the LIVE active universe via NTILE(5). The bucket
 * labels in the UI are EXAMPLE values; the actual numeric ranges move with the data.
 */
class SegFundFilter {
    /** Allowed risk ratings (must match the ENUM in seg_funds). */
    public const RISK_RATINGS = ['Low', 'Low-Med', 'Medium', 'Med-High', 'High'];

    /** Allowed return columns for bucketing. */
    public const BUCKET_COLS = [
        'bucket_1y'  => 'return_1yr',
        'bucket_5y'  => 'return_5yr',
        'bucket_10y' => 'return_10yr',
        'bucket_ytd' => 'ytd_pct',
    ];

    /**
     * Build a WHERE clause + bound params from a filter spec.
     * Returns ['where' => SQL string with leading 'WHERE', 'params' => assoc array, 'has' => bool].
     */
    public static function buildWhere(array $f, bool $includeBaseActive = true): array {
        $where = [];
        $params = [];

        if ($includeBaseActive) {
            $where[] = 'is_active = 1';
        }

        if (!empty($f['carrier'])) {
            $where[] = 'carrier = :carrier';
            $params[':carrier'] = $f['carrier'];
        }
        if (!empty($f['category'])) {
            $where[] = 'category = :category';
            $params[':category'] = $f['category'];
        }
        if (!empty($f['series'])) {
            $where[] = 'series = :series';
            $params[':series'] = $f['series'];
        }
        if (!empty($f['search'])) {
            $where[] = '(fund_name LIKE :search1 OR carrier LIKE :search2)';
            $params[':search1'] = '%' . $f['search'] . '%';
            $params[':search2'] = '%' . $f['search'] . '%';
        }

        // Risk rating — multi-value IN clause
        if (!empty($f['risk_rating']) && is_array($f['risk_rating'])) {
            $ph = [];
            $i = 0;
            foreach ($f['risk_rating'] as $r) {
                if (in_array($r, self::RISK_RATINGS, true)) {
                    $key = ":risk_{$i}";
                    $ph[] = $key;
                    $params[$key] = $r;
                    $i++;
                }
            }
            if ($ph) {
                $where[] = 'risk_rating IN (' . implode(',', $ph) . ')';
            }
        }

        // Death benefit % — multi-value IN clause
        if (!empty($f['death_pct']) && is_array($f['death_pct'])) {
            $ph = [];
            $i = 0;
            foreach ($f['death_pct'] as $v) {
                $v = (int)$v;
                if ($v > 0) {
                    $key = ":death_{$i}";
                    $ph[] = $key;
                    $params[$key] = $v;
                    $i++;
                }
            }
            if ($ph) {
                $where[] = 'death_benefit_pct IN (' . implode(',', $ph) . ')';
            }
        }

        // Maturity benefit % — multi-value IN clause
        if (!empty($f['mat_pct']) && is_array($f['mat_pct'])) {
            $ph = [];
            $i = 0;
            foreach ($f['mat_pct'] as $v) {
                $v = (int)$v;
                if ($v > 0) {
                    $key = ":mat_{$i}";
                    $ph[] = $key;
                    $params[$key] = $v;
                    $i++;
                }
            }
            if ($ph) {
                $where[] = 'maturity_benefit_pct IN (' . implode(',', $ph) . ')';
            }
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';
        return ['where' => $whereSql, 'params' => $params, 'has' => (bool)$where];
    }

    /**
     * Compute 5-bucket boundaries for a return column, given an active-universe WHERE.
     * Returns: [['q'=>1,'min'=>x,'max'=>y,'count'=>n], ...]
     * Buckets are 1..5 (NTILE). Pass `$col` as the SQL column name (e.g. 'return_5yr').
     * Pass `$extraWhere` as a raw SQL fragment to scope the universe (e.g. the
     *   other filters applied so far). Always includes `is_active = 1`.
     */
    public static function bucketBoundaries(PDO $pdo, string $col, string $extraWhere = ''): array {
        $col = preg_replace('/[^a-z0-9_]/', '', $col);  // whitelist
        $sql = "
            WITH ranked AS (
              SELECT $col AS v,
                     NTILE(5) OVER (ORDER BY $col ASC) AS q
              FROM seg_funds
              WHERE is_active = 1 AND $col IS NOT NULL
              " . ($extraWhere ? "AND $extraWhere" : '') . "
            )
            SELECT q, MIN(v) AS lo, MAX(v) AS hi, COUNT(*) AS n
            FROM ranked
            GROUP BY q
            ORDER BY q
        ";
        try {
            $rows = $pdo->query($sql)->fetchAll(PDO::FETCH_ASSOC);
        } catch (Throwable $e) {
            return [];
        }
        return $rows;
    }

    /**
     * For a given bucket request (e.g. 'bucket_5y' => '10-15'), resolve the numeric range
     * from the boundaries. Returns ['lo' => float, 'hi' => float, 'col' => 'return_5yr']
     * or null if the bucket label can't be resolved.
     */
    public static function resolveBucket(string $paramKey, string $label, array $boundaries): ?array {
        if (!isset(self::BUCKET_COLS[$paramKey])) return null;
        $col = self::BUCKET_COLS[$paramKey];
        $q = self::labelToQuintile($label);
        if ($q === null) return null;
        foreach ($boundaries as $b) {
            if ((int)$b['q'] === $q) {
                return [
                    'col' => $col,
                    'lo'  => (float)$b['lo'],
                    'hi'  => (float)$b['hi'],
                ];
            }
        }
        return null;
    }

    /** Map a UI bucket label to its quintile (1..5). Default: ordinal in label. */
    public static function labelToQuintile(string $label): ?int {
        // Accept either a numeric label like "1".."5" or a position like "Q1"/"q5"
        if (preg_match('/^[Qq]?([1-5])$/', trim($label), $m)) {
            return (int)$m[1];
        }
        return null;
    }
}
