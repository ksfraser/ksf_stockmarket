<?php
/**
 * StockFilter — WHERE clause builder + dynamic bucketing for the All Symbols list.
 *
 * Mirrors SegFundFilter (src/Util/SegFundFilter.php) for the stock side:
 *  - Column-range IN filters (price change windows, score ranges, fundamentals thresholds)
 *  - NTILE(5) live quintile buckets for bucketing columns (price change, scores, ratios)
 *  - label→range resolver so templates show real data range for each bucket option
 *  - Label → pretty-display helper (no HTML escaping; templates/rendering layer owns that)
 *
 * Filter pillars (BR-11, FR-12 stock side):
 *  1. Price change vs 1Q/2Q/4Q(1A)/2A/3A/5A/10A  — precomputed in
 *     stock_performance_windows (scripts/refresh_perf_windows.php, nightly);
 *     falls back to runtime CTE from stockprices when the table is stale.
 *  2. Score filters — lipper_scores.composite_score (peer-relative), plus
 *     Zacks rank/composite/VGM grades stored in fundamentals.zacks_*
 *     (populated by ZacksRankPopulator / scripts/import_zacks_screens.php --rank).
 *     These are SQL-filterable in this version (no per-symbol PHP computation).
 *  3. Fundamental attribute filters from the `fundamentals` table (yfinance daily fetch):
 *     P/E (trailing/forward), PEG, ROE, ROA, revenue growth, EPS growth, gross/operating/
 *     profit/net margins, debt/equity, current ratio, FCF/share, FCF yield, dividend yield,
 *     book value/share, insider %, institutional %, beta, market cap, avg volume, relative volume
 *
 * Data sources (verified against actual schema — see ARCHITECTURE.md stock filter section):
 *  - stockprices (sp)         : OHLCV time series — close + price_date only; NO active /
 *                               avg_volume / relative_volume columns. Price-change windows
 *                               (perf_1q..perf_10a) are precomputed into stock_performance_windows
 *                               by scripts/refresh_perf_windows.php (Hermes arch §3); this filter
 *                               engine consumes that table (alias wp) and a runtime CTE fallback.
 *  - symbol_master (sm)      : symbol→name/exchange/sector/industry; is_active (tinyint, default 1)
 *                               is the active flag — NOT stockprices.active (which does not exist).
 *  - fundamentals (f)        : yfinance daily fetch (17,111 rows). 24+ filterable numeric columns:
 *                               trailing_pe(2211), forward_pe(913), peg_ratio(475), roe(13232),
 *                               roa(13402), gross_margin(9579), operating_margin(9786), profit_margin(13285),
 *                               revenue_growth(9739), earnings_growth(1415), debt_to_equity(12773),
 *                               current_ratio(2118), dividend_yield(1856), insider_percent(2123),
 *                               institutional_percent(2309), beta(2303), book_value(2175), market_cap(11411),
 *                               fcf_per_share(1386), price_to_book(2307), price_to_sales(2021),
 *                               zacks_roi(1281), zacks_net_profit_margin(981), shares_outstanding(12344).
 *                               NOTE: fcf_yield is NOT a column — would need runtime computation
 *                               (free_cash_flow / market_cap). Current filter engine does NOT expose it.
 *  - lipper_scores (lp)      : peer-relative scores (7,482 rows): composite_score, preservation_score,
 *                               consistent_score, sector_rank_pct, sharpe_3y, sortino_3y, ret_1y/3y/5y/10y, ytd.
 *  - zacks_broker_recommendations (zr): action column (Buy/Hold/Sell) for recommendation filtering.
 *  - watchlist_symbols (wl)  : per-user watchlist membership
 *
 * Columns that DO NOT EXIST in this schema (filter engine must NOT reference them):
 *  - stockprices.active, stockprices.avg_volume, stockprices.relative_volume
 *  - evalsummary.totalscore, evalsummary.llm_recommendation, evalsummary.human_recommendation
 *                               (evalsummary has 1 row; only consensus_signal/consensus_strength exist)
 *  - evaluation_scores as a general stock score table (only 2 rows; eval_type/domain/score/grade)
 *  - f.fcf_yield (not a column — compute as free_cash_flow / market_cap if needed)
 *
 * Price-change window computation:
 *  The filter emits WHERE clauses referencing perf_1q, perf_2q, ... perf_10a columns.
 *  These live in stock_performance_windows (fresh per-refresh); the controller joins
 *  that table as `wp` (with CURDATE/latest as_of), or builds a runtime CTE fallback.
 */

declare(strict_types=1);

namespace Ksf\StockMarket\Util;

use PDO;

class StockFilter
{
    private PDO $db;

    public function __construct()
    {
        $this->db = \Database::get();
    }

    // ----------------------------------------------------------------------
    //  Market-cap shorthand parser
    // ----------------------------------------------------------------------

    /**
     * Convert market-cap shorthand tags to numeric range (in dollars).
     * Handles: '100M-500M', '1B+', '10B+', '500M-', 'all', etc.
     * Also handles raw numeric ranges like '1000000000-5000000000'.
     *
     * @param string $tag
     * @return array{lo: float|null, hi: float|null}|null   null = no restriction ('all')
     */
    public static function parseMarketCapRange(string $tag): ?array
    {
        $tag = trim($tag);
        if ($tag === 'all' || $tag === '') {
            return null;
        }

        // '1B+' → >= 1,000,000,000
        if (preg_match('/^(\d+(?:\.\d+)?)\s*([BMK])\+$/i', $tag, $m)) {
            $val = self::parseMarketCapValue($m[1], $m[2]);
            if ($val !== null) {
                return ['lo' => $val, 'hi' => null];
            }
        }

        // '100M-500M' → between 100M and 500M
        if (preg_match('/^(\d+(?:\.\d+)?)\s*([BMK])\s*-\s*(\d+(?:\.\d+)?)\s*([BMK])$/i', $tag, $m)) {
            $lo = self::parseMarketCapValue($m[1], $m[2]);
            $hi = self::parseMarketCapValue($m[3], $m[4]);
            if ($lo !== null && $hi !== null) {
                return ['lo' => $lo, 'hi' => $hi];
            }
        }

        // '500M-' → <= 500M
        if (preg_match('/^(\d+(?:\.\d+)?)\s*([BMK])\s*-$/i', $tag, $m)) {
            $val = self::parseMarketCapValue($m[1], $m[2]);
            if ($val !== null) {
                return ['lo' => null, 'hi' => $val];
            }
        }

        // plain numeric: '1000000000-5000000000' or '1000000000+'
        if (preg_match('/^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$/', $tag, $m)) {
            return ['lo' => (float)$m[1], 'hi' => (float)$m[2]];
        }
        if (preg_match('/^(-?\d+(?:\.\d+)?)\+$/', $tag, $m)) {
            return ['lo' => (float)$m[1], 'hi' => null];
        }

        return null; // unknown → caller returns 1=0
    }

    /**
     * Parse a single market-cap value with suffix (e.g. '1.5B', '500M', '10K').
     */
    private static function parseMarketCapValue(string $num, string $suffix): ?float
    {
        $val = (float)$num;
        $suffix = strtoupper(trim($suffix));
        return match ($suffix) {
            'B' => $val * 1_000_000_000,
            'M' => $val * 1_000_000,
            'K' => $val * 1_000,
            default => $val,
        };
    }

    // ----------------------------------------------------------------------
    //  Bucketing helpers (mirror SegFundFilter::bucketBoundaries / resolveBucket)
    // ----------------------------------------------------------------------

    /**
     * Compute live NTILE(5) bucket boundary labels for a bucketing column.
     *
     * @param string $bucketCol   column name (unqualified)
     * @param string $fromTable   SQL source to SELECT distinct values from
     * @return array<string, array{min: float, max: float}>  Q1..Q5 => [min,max]
     */
    public function bucketBoundaries(string $bucketCol, string $fromTable): array
    {
        $sql = "SELECT MIN({$bucketCol}) AS lo, MAX({$bucketCol}) AS hi
                FROM (SELECT DISTINCT {$bucketCol} AS v FROM {$fromTable} WHERE {$bucketCol} IS NOT NULL) x";
        try {
            $row = $this->db->query($sql)->fetch();
        } catch (\PDOException $_) {
            return [];
        }
        if (!$row || ($row['lo'] === null && $row['hi'] === null)) {
            return [];
        }
        $lo = (float)($row['lo'] ?? 0);
        $hi = (float)($row['hi'] ?? 0);
        if ($lo == $hi) {
            return array_fill_keys(['Q1','Q2','Q3','Q4','Q5'], ['min' => $lo, 'max' => $hi]);
        }
        $step = ($hi - $lo) / 5.0;
        return [
            'Q1' => ['min' => $lo,                 'max' => $lo + $step],
            'Q2' => ['min' => $lo + $step,         'max' => $lo + 2 * $step],
            'Q3' => ['min' => $lo + 2 * $step,     'max' => $lo + 3 * $step],
            'Q4' => ['min' => $lo + 3 * $step,     'max' => $lo + 4 * $step],
            'Q5' => ['min' => $lo + 4 * $step,     'max' => $hi],
        ];
    }

    /**
     * Resolve a single bucket label to its inclusive range for WHERE clause building.
     */
    public function resolveBucket(string $bucketCol, string $label, string $fromTable): ?array
    {
        $bounds = $this->bucketBoundaries($bucketCol, $fromTable);
        return $bounds[$label] ?? null;
    }

    /**
     * Friendly label for a bucket option, including the real data range.
     */
    public static function bucketLabel(string $label, float $min, float $max, string $unit = '%'): string
    {
        $fmtPct = fn(float $v) => ($v >= 0 ? '+' : '') . number_format($v, 2) . '%';
        $fmtX   = fn(float $v) => number_format($v, 2) . 'x';
        $fmtDlr = fn(float $v) => '$' . number_format($v, 0);
        $fmt    = match ($unit) {
            '%'  => $fmtPct,
            'x'  => $fmtX,
            '$'  => $fmtDlr,
            default => fn(float $v) => number_format($v, 2),
        };

        if ($label === 'Q1') {
            return "Q1 (lowest, {$fmt($min)}–{$fmt($max)})";
        }
        if ($label === 'Q5') {
            return "Q5 (highest, {$fmt($min)}–{$fmt($max)})";
        }
        return "{$label} ({$fmt($min)}–{$fmt($max)})";
    }

    // ----------------------------------------------------------------------
    //  WHERE builder
    // ----------------------------------------------------------------------

    /**
     * Build WHERE clause + params for the All Symbols filtered list.
     *
     * @param array $filters  keys:
     *   search                   string   — symbol/name search
     *   exchange                 string[] — exchange codes (NYSE, NASDAQ, TSX, ...)
     *   sector                   string[] — sector names
     *   perf_1q|perf_2q|...      string[] — price-change range tags (see _parseRangeTag)
     *   score_total              string[] — evalsummary.totalscore bucket/range tags
     *   score_lipper             string[] — lipper composite range tags
     *   recommendation           string[] — 'buy','hold','sell','strong_buy','strong_sell'
     *   pe_trailing|pe_forward|  string[] — fundamental attribute range tags (see below)
     *   peg_ratio|roe_pct|...    — OR market-cap shorthand ('1B+','100M-500M')
     *   market_cap               string[] — market cap shorthand (1B+, 100M-500M, etc.)
     *   avg_volume|rel_volume    string[] — volume range tags (numeric only)
     *   beta                     string[] — beta range tags (numeric only)
     *   insider_pct|inst_pct     string[] — ownership % range tags
     *   div_yield|fcf_yield      string[] — yield % range tags
     *   in_watchlist             bool     — only symbols in current user's watchlist
     *   combine                  string   — 'and' (default) or 'or' across top-level groups
     * @return array{where: string, params: array}
     */
    public function buildWhere(array $filters): array
    {
        $where = [];
        $params = [];

        // --- base filter: only active symbols with a latest price ---
        // symbol_master.is_active is the active flag (stockprices has no active column).
        $where[] = 'sm.is_active = 1';
        $where[] = 'latest.max_date IS NOT NULL';

        // --- text search (symbol/name) ---
        if (!empty($filters['search'])) {
            $where[] = '(sp.symbol LIKE :sf_search OR sm.name LIKE :sf_search2)';
            $params[':sf_search']  = '%' . $filters['search'] . '%';
            $params[':sf_search2'] = '%' . $filters['search'] . '%';
        }

        // --- price change windows (1Q/2Q/4Q/2A/3A/5A/10A) ---
        $changeCols = [
            'perf_1q'  => 'perf_1q',
            'perf_2q'  => 'perf_2q',
            'perf_4q'  => 'perf_4q',
            'perf_2a'  => 'perf_2a',
            'perf_3a'  => 'perf_3a',
            'perf_5a'  => 'perf_5a',
            'perf_10a' => 'perf_10a',
        ];
        foreach ($changeCols as $key => $colName) {
            if (empty($filters[$key]) || !is_array($filters[$key])) {
                continue;
            }
            $clause = $this->_rangeClauses($filters[$key], $colName, $params, "sf_{$key}_");
            if ($clause !== null) {
                $where[] = $clause;
            }
        }

        // --- score filters ---
        // evalsummary does NOT have totalscore/llm_recommendation/human_recommendation
        // (only 1 row total; columns are consensus_signal/consensus_strength/strategy_json).
        // Stock-level scores live in lipper_scores (peer-relative composite_score etc.) — use that.
        // Zacks-style scores are not stored in DB; the filter engine currently exposes lipper only.
        // Full Zacks-component filtering requires a precomputed scores table (see FR-13 stock side).
        if (!empty($filters['score_lipper']) && is_array($filters['score_lipper'])) {
            $clause = $this->_rangeClauses($filters['score_lipper'], 'lp.composite_score', $params, 'sf_score_lipper_');
            if ($clause !== null) {
                $where[] = $clause;
            }
        }

        // --- recommendation filter ---
        if (!empty($filters['recommendation']) && is_array($filters['recommendation'])) {
            $clause = $this->_recommendationClause($filters['recommendation'], $params);
            if ($clause !== null) {
                $where[] = $clause;
            }
        }

        // --- fundamental attribute filters ---
        $numericFundCols = [
            'pe_trailing'       => 'f.trailing_pe',
            'pe_forward'        => 'f.forward_pe',
            'peg_ratio'         => 'f.peg_ratio',
            'roe_pct'           => 'f.roe',
            'roa_pct'           => 'f.roa',
            'gross_margin'      => 'f.gross_margin',
            'operating_margin'  => 'f.operating_margin',
            'profit_margin'     => 'f.profit_margin',
            'revenue_growth'    => 'f.revenue_growth',
            'eps_growth'        => 'f.earnings_growth',
            'debt_to_equity'    => 'f.debt_to_equity',
            'current_ratio'     => 'f.current_ratio',
            'div_yield'         => 'f.dividend_yield',
            'insider_pct'       => 'f.insider_percent',
            'institutional_pct' => 'f.institutional_percent',
            'beta'              => 'f.beta',
            'book_value'        => 'f.book_value',
            // Zacks revision/coverage columns stored by the fundamental_data fetcher.
            'zacks_roi'              => 'f.zacks_roi',
            'zacks_net_profit_margin'=> 'f.zacks_net_profit_margin',
            'zacks_lt_debt_capital_pct'=> 'f.zacks_lt_debt_capital_pct',
            'zacks_eps_change_f1_4w' => 'f.zacks_eps_change_f1_4w',
            'zacks_eps_change_f2_4w' => 'f.zacks_eps_change_f2_4w',
            'zacks_price_change_52w' => 'f.zacks_price_change_52w',
            'zacks_num_analysts'     => 'f.zacks_num_analysts',
        ];
        foreach ($numericFundCols as $key => $colRef) {
            if (!empty($filters[$key]) && is_array($filters[$key])) {
                $clause = $this->_rangeClauses($filters[$key], $colRef, $params, "sf_{$key}_");
                if ($clause !== null) {
                    $where[] = $clause;
                }
            }
        }

        // --- Zacks score/rank filters (SQL-filterable via fundamentals.zacks_*) ---
        if (!empty($filters['zacks_rank']) && is_array($filters['zacks_rank'])) {
            $clause = $this->_rangeClauses($filters['zacks_rank'], 'f.zacks_rank', $params, 'sf_zrank_');
            if ($clause !== null) {
                $where[] = $clause;
            }
        }
        if (!empty($filters['zacks_composite']) && is_array($filters['zacks_composite'])) {
            $clause = $this->_rangeClauses($filters['zacks_composite'], 'f.zacks_composite', $params, 'sf_zcomp_');
            if ($clause !== null) {
                $where[] = $clause;
            }
        }
        // VGM grades are text (A/B/C/D/F) — only exact-match IN lists make sense.
        $gradeCols = [
            'zacks_value_grade'     => 'f.zacks_value_grade',
            'zacks_growth_grade'    => 'f.zacks_growth_grade',
            'zacks_momentum_grade'  => 'f.zacks_momentum_grade',
            'zacks_vgm_grade'       => 'f.zacks_vgm_grade',
        ];
        foreach ($gradeCols as $key => $colRef) {
            if (!empty($filters[$key]) && is_array($filters[$key])) {
                $where[] = $this->_inClause($colRef, array_map('strtoupper', $filters[$key]), $params, "sf_{$key}_");
            }
        }

        //    market_cap shorthand (handled specially)
        if (!empty($filters['market_cap']) && is_array($filters['market_cap'])) {
            $clauses = [];
            foreach ($filters['market_cap'] as $tag) {
                $parsed = self::parseMarketCapRange($tag);
                if ($parsed === null) {
                    continue;
                }
                $pref = 'sf_mcap_';
                if ($parsed['lo'] !== null && $parsed['hi'] !== null) {
                    $params[':'.$pref.'lo'] = $parsed['lo'];
                    $params[':'.$pref.'hi'] = $parsed['hi'];
                    $clauses[] = "f.market_cap >= :{$pref}lo AND f.market_cap <= :{$pref}hi";
                } elseif ($parsed['lo'] !== null) {
                    $params[':'.$pref.'lo'] = $parsed['lo'];
                    $clauses[] = "f.market_cap >= :{$pref}lo";
                } elseif ($parsed['hi'] !== null) {
                    $params[':'.$pref.'hi'] = $parsed['hi'];
                    $clauses[] = "f.market_cap <= :{$pref}hi";
                }
            }
            if ($clauses) {
                $where[] = '(' . implode(' OR ', $clauses) . ')';
            }
        }

        // --- volume filters ---
        // NOTE: stockprices does NOT have avg_volume or relative_volume columns.
        // stockprices has: close, open, high, low, volume, adj_close, dividend, split_ratio, currency.
        // Relative/volume-based filtering would require a precomputed volume table or runtime
        // computation from stockprices.volume. For now the filter engine does NOT expose volume filters.
        // To add: create a stock_volume_stats table (symbol, avg_volume_20d, relative_volume_today)
        // refreshed nightly, then add 'avg_volume' and 'rel_volume' to $numericFundCols above.

        // --- exchange filter ---
        if (!empty($filters['exchange']) && is_array($filters['exchange'])) {
            $where[] = $this->_inClause('sm.exchange', $filters['exchange'], $params, 'sf_ex_');
        }

        // --- sector filter ---
        if (!empty($filters['sector']) && is_array($filters['sector'])) {
            $where[] = $this->_inClause('sm.sector', $filters['sector'], $params, 'sf_sec_');
        }

        // --- watchlist membership ---
        if (!empty($filters['in_watchlist']) && (bool)$filters['in_watchlist']) {
            $where[] = 'wl.symbol IS NOT NULL';
        }

        // --- combination mode: AND (default) vs OR across top-level groups ---
        $combine = strtolower($filters['combine'] ?? 'and');
        if ($combine === 'or' && count($where) > 1) {
            $baseWhere = ['sm.is_active = 1', 'latest.max_date IS NOT NULL'];
            $filterWhere = array_values(array_diff($where, $baseWhere));
            if (!empty($filterWhere)) {
                $where = array_merge($baseWhere, ['(' . implode(' OR ', $filterWhere) . ')']);
            }
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';
        return ['where' => $whereSql, 'params' => $params];
    }

    // ----------------------------------------------------------------------
    //  Internal clause builders
    // ----------------------------------------------------------------------

    /**
     * Range-clause builder for a single column accepting multiple range/bucket tags.
     *
     * Supported tag syntax:
     *   - 'Q1'..'Q5'          → bucket (resolved at runtime from NTILE bounds)
     *   - '-10--5'           → between -10 and -5
     *   - '-5-0'             → between -5 and 0
     *   - '0-5'              → between 0 and 5
     *   - '5-10'             → between 5 and 10
     *   - '10+'              → >= 10
     *   - '-10-'             → <= -10  (trailing minus = "below negative threshold")
     *   - 'below-5'          → <= 5  (positive shorthand for "below threshold")
     *   - 'all' / ''         → no restriction
     *
     * @return string|null   null = no restriction (all), '1=0' = unrecognized tag
     */
    private function _rangeClauses(array $ranges, string $colName, array &$params, string $prefix): ?string
    {
        $clauses = [];
        foreach ($ranges as $i => $r) {
            $c = $this->_rangeClause($r, $colName, $params, $prefix, (int) $i);
            if ($c !== null) {
                $clauses[] = $c;
            }
        }
        return $clauses ? (count($clauses) > 1 ? '(' . implode(' OR ', $clauses) . ')' : $clauses[0]) : null;
    }

    /**
     * Parse a single range tag and return the WHERE clause fragment, or null for 'all'.
     *
     * @return string|null
     */
    private function _rangeClause(string $tag, string $colName, array &$params, string $prefix, int $idx = 0): ?string
    {
        $tag = trim($tag);
        if ($tag === '' || $tag === 'all') {
            return null;
        }

        // bucket label Q1..Q5
        if (preg_match('/^Q[1-5]$/i', $tag)) {
            $key = $prefix . 'bucket_' . strtoupper($tag);
            $params[$key] = ['label' => strtoupper($tag), 'col' => $colName];
            return "{$colName} >= :{$prefix}bucket_lo AND {$colName} <= :{$prefix}bucket_hi";
        }

        // bare number → exact equality (e.g. Zacks Rank '1'..'5')
        if (preg_match('/^\d+(?:\.\d+)?$/', $tag)) {
            $key = $prefix . 'eq' . $idx;
            $params[':' . $key] = (float)$tag;
            return "ABS({$colName} - :{$key}) < 0.0001";
        }

        // below-threshold shorthand: 'below-5' → <= 5
        if (preg_match('/^below-(\d+(?:\.\d+)?)$/i', $tag, $m)) {
            $key = $prefix . 'hi';
            $params[':'.$key] = (float)$m[1];
            return "{$colName} <= :{$key}";
        }

        // explicit range: [sign][digits]-[sign][digits]
        if (preg_match('/^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$/', $tag, $m)) {
            $plo = $prefix . 'lo';
            $phi  = $prefix . 'hi';
            $params[':'.$plo] = (float)$m[1];
            $params[':'.$phi] = (float)$m[2];
            return "{$colName} >= :{$plo} AND {$colName} <= :{$phi}";
        }

        // above threshold: [digits]+
        if (preg_match('/^(-?\d+(?:\.\d+)?)\+$/', $tag, $m)) {
            $key = $prefix . 'lo';
            $params[':'.$key] = (float)$m[1];
            return "{$colName} >= :{$key}";
        }

        // below negative threshold: -[digits] (e.g. '-10-' = "10% or more negative")
        if (preg_match('/^-(-?\d+(?:\.\d+)?)$/', $tag, $m)) {
            $key = $prefix . 'hi';
            $params[':'.$key] = (float)$m[1];
            return "{$colName} <= :{$key}";
        }

        // unrecognized
        return '1=0';
    }

    /**
     * Recommendation clause: recommends symbols that have a Zacks broker recommendation
     * action matching the requested values. Maps friendly labels to Zacks action values.
     *
     * The zacks_broker_recommendations table stores action as: Buy, Hold, Sell (and variants).
     * We map friendly labels → Zacks action strings.
     *
     * NOTE: evalsummary has only 1 row and no llm_recommendation/human_recommendation column,
     * so we cannot filter by evalsummary recommendation. Zacks broker recs are the available source.
     */
    private function _recommendationClause(array $recs, array &$params): ?string
    {
        if (empty($recs)) return null;
        $vals = [];
        foreach ($recs as $r) {
            $r = strtolower(trim($r));
            // Map friendly labels → Zacks action values (as stored in zr.action)
            $map = [
                'strong buy'     => 'Buy',
                'buy'            => 'Buy',
                'accumulate'     => 'Buy',
                'outperform'     => 'Buy',
                'hold'           => 'Hold',
                'neutral'        => 'Hold',
                'moderate sell'  => 'Sell',
                'sell'           => 'Sell',
                'strong sell'    => 'Sell',
                'underperform'   => 'Sell',
                'very bearish'   => 'Sell',
                'very bullish'   => 'Buy',
            ];
            $r = $map[$r] ?? $r;
            $key = 'sf_rec_' . md5($r);
            $params[':'.$key] = $r;
            $vals[] = ':' . $key;
        }
        if (empty($vals)) return null;
        return "(zr.action IN (" . implode(',', $vals) . "))";
    }

    /**
     * IN clause for exchange / sector filters.
     */
    private function _inClause(string $colRef, array $values, array &$params, string $prefix): string
    {
        $vals = [];
        foreach ($values as $i => $v) {
            $key = $prefix . 'v' . $i;
            $params[':' . $key] = (string)$v;
            $vals[] = ':' . $key;
        }
        return $colRef . ' IN (' . implode(',', $vals) . ')';
    }

    // ----------------------------------------------------------------------
    //  Filter options fetcher — drives the template filter controls
    // ----------------------------------------------------------------------

    /**
     * Return the set of available filter option labels + live exchange/sector lists.
     */
    public function filterOptions(): array
    {
        static $opts = null;
        if ($opts !== null) {
            return $opts;
        }

        $opts = [
            'change_windows' => [
                'perf_1q'  => ['label' => '1 Quarter (1Q)',     'col' => 'perf_1q'],
                'perf_2q'  => ['label' => '2 Quarters (2Q)',      'col' => 'perf_2q'],
                'perf_4q'  => ['label' => '4 Quarters (1 Year)', 'col' => 'perf_4q'],
                'perf_2a'  => ['label' => '2 Years (2A)',        'col' => 'perf_2a'],
                'perf_3a'  => ['label' => '3 Years (3A)',        'col' => 'perf_3a'],
                'perf_5a'  => ['label' => '5 Years (5A)',        'col' => 'perf_5a'],
                'perf_10a' => ['label' => '10 Years (10A)',      'col' => 'perf_10a'],
            ],
            'score_filters' => [
                // NOTE: evalsummary.totalscore does NOT exist (evalsummary has 1 row).
                // lipper_scores.composite_score (7,482 rows) is peer-relative.
                // Zacks rank/composite/grades ARE SQL-filterable — stored in fundamentals.zacks_*
                // (populated by ZacksRankPopulator; scripts/import_zacks_screens.php --rank).
                'score_lipper' => ['label' => 'Lipper Composite Score',       'col' => 'lp.composite_score'],
                'zacks_rank' => ['label' => 'Zacks Rank (1–5)',                'col' => 'f.zacks_rank'],
                'zacks_composite' => ['label' => 'Zacks Composite',            'col' => 'f.zacks_composite'],
            ],
            'fund_filters' => [
                // Fundamental attributes from the `fundamentals` table (yfinance daily fetch).
                // Counts shown are usable (non-null, non-zero) rows as of schema inventory.
                // NOTE: fcf_yield is NOT a column — compute as free_cash_flow / market_cap at runtime
                // if needed. avg_volume / rel_volume are NOT stockprices columns — stockprices has
                // only close/open/high/low/volume/adj_close/dividend/split_ratio/currency.
                'pe_trailing'       => ['label' => 'P/E (Trailing)',    'col' => 'f.trailing_pe',       'unit' => 'x',    'shorthand' => false],
                'pe_forward'        => ['label' => 'P/E (Forward)',     'col' => 'f.forward_pe',        'unit' => 'x',    'shorthand' => false],
                'peg_ratio'         => ['label' => 'PEG Ratio',         'col' => 'f.peg_ratio',         'unit' => 'x',    'shorthand' => false],
                'roe_pct'           => ['label' => 'ROE %',             'col' => 'f.roe',               'unit' => '%',    'shorthand' => false],
                'roa_pct'           => ['label' => 'ROA %',             'col' => 'f.roa',               'unit' => '%',    'shorthand' => false],
                'gross_margin'      => ['label' => 'Gross Margin %',    'col' => 'f.gross_margin',      'unit' => '%',    'shorthand' => false],
                'operating_margin'  => ['label' => 'Operating Margin %','col' => 'f.operating_margin',  'unit' => '%',    'shorthand' => false],
                'profit_margin'     => ['label' => 'Profit Margin %',   'col' => 'f.profit_margin',     'unit' => '%',    'shorthand' => false],
                'revenue_growth'    => ['label' => 'Revenue Growth %',   'col' => 'f.revenue_growth',    'unit' => '%',    'shorthand' => false],
                'eps_growth'        => ['label' => 'EPS Growth %',      'col' => 'f.earnings_growth',   'unit' => '%',    'shorthand' => false],
                'debt_to_equity'    => ['label' => 'Debt/Equity',       'col' => 'f.debt_to_equity',    'unit' => 'x',    'shorthand' => false],
                'current_ratio'     => ['label' => 'Current Ratio',     'col' => 'f.current_ratio',     'unit' => 'x',    'shorthand' => false],
                'div_yield'         => ['label' => 'Dividend Yield %',  'col' => 'f.dividend_yield',    'unit' => '%',    'shorthand' => false],
                'insider_pct'       => ['label' => 'Insider Own %',     'col' => 'f.insider_percent',   'unit' => '%',    'shorthand' => false],
                'institutional_pct' => ['label' => 'Institutional Own %','col'=>'f.institutional_percent','unit'=>'%',     'shorthand' => false],
                'beta'              => ['label' => 'Beta',              'col' => 'f.beta',              'unit' => 'x',    'shorthand' => false],
                'book_value'        => ['label' => 'Book Value/Share',  'col' => 'f.book_value',        'unit' => '$',    'shorthand' => false],
                'market_cap'        => ['label' => 'Market Cap',        'col' => 'f.market_cap',        'unit' => '$',    'shorthand' => true],
                // Zacks attributes available in fundamentals (stored by fundamental_data.py fetcher)
                'zacks_roi'              => ['label' => 'Zacks ROI',              'col' => 'f.zacks_roi',              'unit' => '%',    'shorthand' => false],
                'zacks_net_profit_margin'=> ['label' => 'Zacks Net Profit Margin', 'col' => 'f.zacks_net_profit_margin', 'unit' => '%', 'shorthand' => false],
                'zacks_lt_debt_capital_pct'=> ['label' => 'Zacks LT Debt / Capital %','col'=>'f.zacks_lt_debt_capital_pct','unit'=>'%','shorthand'=>false],
                'zacks_eps_change_f1_4w'   => ['label' => 'Zacks EPS Δ F1 (4W)',    'col' => 'f.zacks_eps_change_f1_4w', 'unit' => '%',  'shorthand' => false],
                'zacks_eps_change_f2_4w'   => ['label' => 'Zacks EPS Δ F2 (4W)',    'col' => 'f.zacks_eps_change_f2_4w', 'unit' => '%',  'shorthand' => false],
                'zacks_price_change_52w'   => ['label' => 'Zacks 52W Price Change %', 'col' => 'f.zacks_price_change_52w', 'unit' => '%', 'shorthand' => false],
                'zacks_num_analysts'       => ['label' => 'Zacks # Analysts',       'col' => 'f.zacks_num_analysts',     'unit' => '#',  'shorthand' => false],
                // Zacks VGM grades (A/B/C/D/F) — exact-match multi-select.
                'zacks_value_grade'       => ['label' => 'Zacks Value Grade',     'col' => 'f.zacks_value_grade',     'unit' => 'grade', 'shorthand' => false],
                'zacks_growth_grade'      => ['label' => 'Zacks Growth Grade',    'col' => 'f.zacks_growth_grade',    'unit' => 'grade', 'shorthand' => false],
                'zacks_momentum_grade'    => ['label' => 'Zacks Momentum Grade',  'col' => 'f.zacks_momentum_grade',  'unit' => 'grade', 'shorthand' => false],
                'zacks_vgm_grade'         => ['label' => 'Zacks VGM Grade',       'col' => 'f.zacks_vgm_grade',       'unit' => 'grade', 'shorthand' => false],
            ],
            'exchanges'       => [],
            'sectors'         => [],
            'recommendations' => [
                'strong_buy' => 'Strong Buy',
                'buy'        => 'Buy / Accumulate / Outperform',
                'hold'       => 'Hold / Neutral',
                'sell'       => 'Sell / Underperform',
                'strong_sell'=> 'Strong Sell',
            ],
        ];

        // exchanges / sectors pulled live from symbol_master
        try {
            $exchanges = $this->db->query(
                "SELECT DISTINCT exchange FROM symbol_master WHERE exchange IS NOT NULL AND exchange != '' ORDER BY exchange"
            )->fetchAll(\PDO::FETCH_COLUMN);
            $opts['exchanges'] = $exchanges ?: ['NYSE', 'NASDAQ', 'TSX'];
        } catch (\PDOException $_) {
            $opts['exchanges'] = ['NYSE', 'NASDAQ', 'TSX'];
        }
        try {
            $sectors = $this->db->query(
                "SELECT DISTINCT sector FROM symbol_master WHERE sector IS NOT NULL AND sector != '' ORDER BY sector"
            )->fetchAll(\PDO::FETCH_COLUMN);
            $opts['sectors'] = $sectors ?: [];
        } catch (\PDOException $_) {
            $opts['sectors'] = [];
        }

        return $opts;
    }

    /**
     * Resolve bucket placeholders in a WHERE clause by replacing them with real NTILE bounds.
     *
     * @param string $whereSql   raw WHERE clause (may contain bucket placeholders)
     * @param array  $params     params array (may contain bucket entries: ['label'=>...,'col'=>...])
     * @param string $colName    the column whose buckets are being resolved
     * @param string $fromTable  SQL source to compute NTILE bounds from
     * @return array{where: string, params: array}  with bucket placeholders replaced by real bounds
     */
    public function resolveBucketPlaceholders(string $whereSql, array $params, string $colName, string $fromTable): array
    {
        $changed = false;
        foreach ($params as $key => $val) {
            if (!is_array($val) || !isset($val['label'], $val['col']) || $val['col'] !== $colName) {
                continue;
            }
            $bounds = $this->resolveBucket($colName, $val['label'], $fromTable);
            if (!$bounds) {
                // column is empty — replace this filter with 1=0 so it matches nothing
                $whereSql = preg_replace(
                    '/' . preg_quote($colName, '/') . ' >= :' . preg_quote($key, '/') . ' AND ' . preg_quote($colName, '/') . ' <= :' . preg_quote($key, '/') . '/',
                    '1=0',
                    $whereSql
                );
                unset($params[$key]);
                $changed = true;
                continue;
            }

            $pref = $this->bucketPrefix($key);
            $loKey = $pref . 'lo';
            $hiKey = $pref . 'hi';
            $params[':'.$loKey] = $bounds['min'];
            $params[':'.$hiKey] = $bounds['max'];

            // Replace the old placeholder references with the new lo/hi keys
            $whereSql = str_replace(
                "{$colName} >= :{$key} AND {$colName} <= :{$key}",
                "{$colName} >= :{$loKey} AND {$colName} <= :{$hiKey}",
                $whereSql
            );
            unset($params[$key]);
            $changed = true;
        }

        if ($changed) {
            // Clean up any leftover bucket entries that weren't matched (defensive)
            foreach ($params as $key => $val) {
                if (is_array($val) && isset($val['label'])) {
                    unset($params[$key]);
                }
            }
        }

        return ['where' => $whereSql, 'params' => $params];
    }

    /**
     * Derive the lo/hi key prefix from a bucket placeholder key.
     * e.g. 'sf_perf_1q_bucket_Q3' → 'sf_perf_1q_bucket_'
     */
    private function bucketPrefix(string $key): string
    {
        // strip the trailing '_bucket_Q#' or '_bucket_label' part, keep trailing '_'
        return preg_replace('/(?:_bucket_[A-Z0-9]+)$/i', '', $key) . '_';
    }

    // ----------------------------------------------------------------------
    //  Filter stats — counts per bucket so templates can show (n=42) chips
    // ----------------------------------------------------------------------

    /**
     * For a given column, return the per-bucket count (Q1..Q5) computed via NTILE(5)
     * over the distinct non-null values.
     *
     * @param string $colName   column name (unqualified)
     * @param string $fromTable SQL source to compute stats from
     * @return array{q1:int,q2:int,q3:int,q4:int,q5:int,total:int}|null
     */
    public function bucketStats(string $colName, string $fromTable): ?array
    {
        try {
            $sql = "SELECT tile, COUNT(*) AS cnt FROM (
                        SELECT {$colName}, NTILE(5) OVER (ORDER BY {$colName}) AS tile
                        FROM (SELECT DISTINCT {$colName} AS v FROM {$fromTable} WHERE {$colName} IS NOT NULL) d
                    ) t GROUP BY tile ORDER BY tile";
            $rows = $this->db->query($sql)->fetchAll();
            $counts = ['q1' => 0, 'q2' => 0, 'q3' => 0, 'q4' => 0, 'q5' => 0];
            $total = 0;
            foreach ($rows as $r) {
                $tile = (int)$r['tile'];
                if ($tile >= 1 && $tile <= 5) {
                    $counts['q' . $tile] = (int)$r['cnt'];
                    $total += (int)$r['cnt'];
                }
            }
            return [
                'q1' => $counts['q1'], 'q2' => $counts['q2'],
                'q3' => $counts['q3'], 'q4' => $counts['q4'],
                'q5' => $counts['q5'], 'total' => $total,
            ];
        } catch (\PDOException $_) {
            return null;
        }
    }

    /**
     * Count of distinct symbols matching a given filter spec.
     *
     * @param array  $filters       filter spec (same shape as buildWhere)
     * @param string $fromTableSql the FROM clause source
     * @return int
     */
    public function filterCount(array $filters, string $fromTableSql): int
    {
        $where = $this->buildWhere($filters);
        // Resolve any bucket placeholders first
        // (The caller must have already resolved them for the columns that use buckets)
        $sql = "SELECT COUNT(DISTINCT symbol) FROM ({$fromTableSql}) x {$where['where']}";
        try {
            $stmt = $this->db->prepare($sql);
            foreach ($where['params'] as $k => $v) {
                if (is_array($v)) {
                    continue; // bucket placeholder — caller should have resolved
                }
                $stmt->bindValue($k, $v);
            }
            $stmt->execute();
            return (int)$stmt->fetchColumn();
        } catch (\PDOException $_) {
            return 0;
        }
    }
}
