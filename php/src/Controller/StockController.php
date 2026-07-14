<?php
/**
 * StockController — handles all stock-related pages.
 */
class StockController {
    private $pdo;
    /** @var SymbolResolver */
    private $resolver;

    public function __construct() {
        $this->pdo = Database::get();
        $this->resolver = new SymbolResolver($this->pdo);
    }

    /**
     * GET /?action=list — List all symbols with latest price.
     */
    public function listSymbols(string $search = '', string $exchange = '', string $sortBy = 'symbol', string $sortDir = 'ASC', int $page = 1, int $perPage = 200): array {
        $allowedSort = ['symbol','close','volume','change_pct','price_date'];
        if (!in_array($sortBy, $allowedSort)) $sortBy = 'symbol';
        $sortDir = strtoupper($sortDir) === 'DESC' ? 'DESC' : 'ASC';

        $where = [];
        $params = [];

        if ($search) {
            $where[] = "(sp.symbol LIKE :search1 OR sm.name LIKE :search2)";
            $params[':search1'] = '%' . $search . '%';
            $params[':search2'] = '%' . $search . '%';
        }
        if ($exchange) {
            $where[] = "sm.exchange = :exchange";
            $params[':exchange'] = $exchange;
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        // Total matching symbols
        $countSql = "SELECT COUNT(DISTINCT sp.symbol)
                     FROM stockprices sp
                     LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
                     {$whereSql}";
        $stmt = $this->pdo->prepare($countSql);
        $stmt->execute($params);
        $totalAll = (int)$stmt->fetchColumn();

        $page = max(1, $page);
        $perPage = in_array($perPage, [50, 100, 250, 500, 1000]) ? $perPage : 200;
        $offset = ($page - 1) * $perPage;
        $totalPages = max(1, (int)ceil($totalAll / $perPage));
        if ($page > $totalPages) {
            $page = $totalPages;
            $offset = ($page - 1) * $perPage;
        }

        // Get latest price for each symbol
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
                LIMIT {$perPage} OFFSET {$offset}";

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

        return [
            'symbols'     => $rows,
            'search'      => $search,
            'exchange'    => $exchange,
            'sortBy'      => $sortBy,
            'sortDir'     => $sortDir,
            'page'        => $page,
            'per_page'    => $perPage,
            'total_all'   => $totalAll,
            'total_pages' => $totalPages,
        ];
    }

    /**
     * GET /?action=detail&symbol=XXX — Enhanced single symbol detail page.
     */
    public function detail(string $symbol): array {
        $symbol = strtoupper(trim($symbol));
        $resolved = $this->resolver->resolve($symbol);
        // For DB lookups prefer the resolved form, but keep original as fallback
        $candidates = $this->resolver->candidates($symbol);

        // Latest price info — try candidates in order
        $latest = null;
        foreach ($candidates as $candidate) {
            $stmt = $this->pdo->prepare("
                SELECT sp.*, sm.name, sm.exchange, sm.sector, sm.industry
                FROM stockprices sp
                LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
                WHERE sp.symbol = :sym
                ORDER BY sp.price_date DESC LIMIT 1
            ");
            $stmt->execute([':sym' => $candidate]);
            $latest = $stmt->fetch();
            if ($latest) {
                $symbol = $candidate;
                break;
            }
        }

        if (!$latest) {
            return ['error' => 'Symbol not found', 'symbol' => $symbol];
        }

        // Previous close
        $stmt = $this->pdo->prepare("SELECT close FROM stockprices WHERE symbol = :sym AND price_date < :d ORDER BY price_date DESC LIMIT 1");
        $stmt->execute([':sym' => $symbol, ':d' => $latest['price_date']]);
        $latest['prev_close'] = $stmt->fetchColumn();

        // 2 years history — enough to cover dividend ex-dates for the Recent Dividends table
        $stmt = $this->pdo->prepare("SELECT price_date, open, high, low, close, volume FROM stockprices WHERE symbol = :sym ORDER BY price_date DESC LIMIT 730");
        $stmt->execute([':sym' => $symbol]);
        $history = array_reverse($stmt->fetchAll());

        // Indicators: latest + 60 days for charts — prefer the resolved symbol
        $this->refreshIndicatorsJsonIfStale($resolved);
        $indHistory = [];
        $indicators = [];

        $indSql = "SELECT price_date, data FROM indicators_json WHERE symbol = :sym ORDER BY price_date DESC LIMIT 60";
        $stmt = $this->pdo->prepare($indSql);
        $stmt->execute([':sym' => $resolved]);
        $indRows = array_reverse($stmt->fetchAll());

        if (empty($indRows) && $resolved !== $symbol) {
            // Fallback to input symbol if resolved form has no data yet
            $stmt->execute([':sym' => $symbol]);
            $indRows = array_reverse($stmt->fetchAll());
        }

        foreach ($indRows as $i => $row) {
            $d = json_decode($row['data'], true);
            $d['price_date'] = $row['price_date'];
            $indHistory[] = $d;
        }
        if ($indHistory) $indicators = end($indHistory);

        // Fundamentals — use resolved symbol first, fallback to original
        $stmt = $this->pdo->prepare("SELECT * FROM fundamentals WHERE symbol = :sym ORDER BY fetch_date DESC LIMIT 1");
        $stmt->execute([':sym' => $resolved]);
        $fundamentals = $stmt->fetch() ?: [];
        if (empty($fundamentals) && $resolved !== $symbol) {
            $stmt->execute([':sym' => $symbol]);
            $fundamentals = $stmt->fetch() ?: [];
        }

        // Portfolio position
        $stmt = $this->pdo->prepare("SELECT * FROM portfolio WHERE symbol = :sym");
        $stmt->execute([':sym' => $symbol]);
        $portfolio = $stmt->fetch();

        // Dividend data
        $fctrl = new FundamentalsController();
        $dividendSafety = $fctrl->getDividendSafety($symbol);
        $dividends = $fctrl->getDividends($symbol);

        // Calculate current dividend yield (annual dividend / current price)
        $closePrice = $latest['close'] ?? 0;
        $annualDivPerShare = $fundamentals['dividend_rate'] ?? 0;
        $fundamentals['current_div_yield'] = $closePrice > 0 ? ($annualDivPerShare / $closePrice) * 100 : null;

        // Analyst data (tables may not exist yet — graceful fallback)
        $analystRatings = $this->getTableData('analyst_ratings', $symbol, 'date DESC', 20);
        $analystTargets = [];
        foreach ($analystRatings as $r) {
            if (!empty($r['price_target'])) {
                $analystTargets[] = ['date' => $r['date'], 'price_target' => $r['price_target'], 'firm' => $r['firm'] ?? '', 'analyst_name' => $r['analyst_name'] ?? ''];
            }
        }

        // Analyst recommendations
        $recommendations = $this->getTableData('analyst_recommendations', $symbol, 'rec_date DESC', 30);

        // News — use news_feeds table populated by news_monitor.py, fallback to symbol_news
        $news = [];
        try {
            $sql = "SELECT title, url, source, published AS date, summary FROM news_feeds WHERE symbol_filter = :sym ORDER BY published DESC LIMIT 10";
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute([':sym' => $symbol]);
            $news = $stmt->fetchAll();
        } catch (\Exception $e) {
            $news = [];
        }
        if (empty($news)) {
            $news = $this->getTableData('symbol_news', $symbol, 'date DESC', 10);
        }
        // Enrich news with LLM processed summaries
        $newsProcessed = [];
        foreach ($news as $n) {
            $url = $n['url'] ?? '';
            $date = $n['date'] ?? '';
            // Try to find a processed record by matching title or url roughly
            // We map by source_id if we can infer it, otherwise we'll just do a best-effort join
            // For now, we'll fetch by symbol + nearby date
            try {
                $stmt = $this->pdo->prepare("
                    SELECT np.summary, np.classification, np.sentiment, np.recommendation, np.confidence
                    FROM news_processed np
                    WHERE np.symbol = :sym
                      AND np.processed_at >= DATE_SUB(:dt, INTERVAL 7 DAY)
                    ORDER BY np.processed_at DESC
                    LIMIT 10
                ");
                $stmt->execute([':sym' => $symbol, ':dt' => $date]);
                $matched = $stmt->fetchAll();
                $n['processed'] = $matched ? $matched[0] : null;
            } catch (\Exception $e) {
                $n['processed'] = null;
            }
            $newsProcessed[] = $n;
        }
        $news = $newsProcessed;

        // Options snapshot
        $opts = $this->getTableData('options_snapshot', $symbol, 'fetch_date DESC', 1);
        $optionsData = $opts[0] ?? [];

        // Holders
        $holders = ['major' => [], 'institutional' => []];
        try {
            $stmt = $this->pdo->prepare("SELECT holder_name, shares, percent_held, value FROM holders WHERE symbol = :sym AND holder_type = 'major' AND fetch_date = CURDATE() ORDER BY shares DESC");
            $stmt->execute([':sym' => $symbol]);
            $holders['major'] = $stmt->fetchAll();
        } catch (\Exception $e) {}
        try {
            $stmt = $this->pdo->prepare("SELECT holder_name, shares, percent_held, value FROM holders WHERE symbol = :sym AND holder_type = 'institutional' AND fetch_date = CURDATE() ORDER BY shares DESC");
            $stmt->execute([':sym' => $symbol]);
            $holders['institutional'] = $stmt->fetchAll();
        } catch (\Exception $e) {}

        // Financial statements
        $financials = [];
        foreach (['income', 'balance', 'cashflow'] as $stmtType) {
            $financials[$stmtType] = ['annual' => [], 'quarterly' => []];
            foreach (['annual', 'quarterly'] as $period) {
                try {
                    $stmt = $this->pdo->prepare("SELECT fiscal_date, raw_data FROM financial_statements WHERE symbol = :sym AND statement_type = :stmt AND period_type = :period ORDER BY fiscal_date DESC LIMIT 8");
                    $stmt->execute([':sym' => $symbol, ':stmt' => $stmtType, ':period' => $period]);
                    $financials[$stmtType][$period] = $stmt->fetchAll();
                } catch (\Exception $e) {}
            }
        }

        // Analyst estimates
        $estimates = [];
        foreach (['earnings', 'revenue'] as $estType) {
            $estimates[$estType] = [];
            try {
                $stmt = $this->pdo->prepare("SELECT period, low_estimate, high_estimate, avg_estimate, num_analysts FROM analyst_estimates WHERE symbol = :sym AND estimate_type = :est ORDER BY period DESC LIMIT 6");
                $stmt->execute([':sym' => $symbol, ':est' => $estType]);
                $estimates[$estType] = $stmt->fetchAll();
            } catch (\Exception $e) {}
        }

        // Buffett quality score (pass close price since it's in stockprices, not indicators)
        $closePrice = $latest['close'] ?? 0;
        $buffettScore = $this->calcBuffettScore($fundamentals, $indicators, $closePrice);

        // Zacks-style composite score
        $zacksScore = $this->calcZacksStyleScore($fundamentals, $indicators, $closePrice);

        // Performance
        $perf = $this->calcPerformance($symbol);
        
        // Markov regime analysis
        $regime = $this->getRegimeAnalysis($symbol);

        // Exit signal risk assessment
        $closePrice = $latest['close'] ?? 0;
        $exitSignals = $this->calcExitSignals($fundamentals, $indicators, $closePrice);

        // VectorVest 5-point checklist (detail-page lightweight version)
        $vectorVest = $this->calcVectorVest($history, $fundamentals, $latest, $indicators);

        $result = compact(
            'symbol', 'latest', 'history', 'indicators', 'indHistory',
            'fundamentals', 'portfolio', 'dividendSafety', 'dividends',
            'analystRatings', 'analystTargets', 'news', 'optionsData',
            'buffettScore', 'zacksScore', 'perf', 'regime', 'exitSignals',
            'recommendations', 'holders', 'financials', 'estimates',
            'vectorVest'
        );
        $result['analyst_ratings'] = $result['analystRatings'];
        $result['analyst_targets'] = $result['analystTargets'];
        $result['buffett_score'] = $result['buffettScore'];
        $result['zacks_score'] = $result['zacksScore'] ?? [];
        $result['options'] = $result['optionsData'];
        $result['ind_history'] = $result['indHistory'];
        $result['dividend_safety'] = $result['dividendSafety'];
        $result['exit_signals'] = $result['exitSignals'] ?? [];
        $result['vectorvest'] = $result['vectorVest'] ?? [];
        return $result;
    }

    public function calcExitSignals(array $f, array $ind, float $closePrice = 0): array {
        if (!$closePrice || $closePrice <= 0) {
            return ['composite_exit_risk' => 0.5, 'insufficient_data' => true];
        }
        
        $signals = [];
        $weights = [];
        $cfg = $this->getExitSignalConfig();
        
        if (!empty($ind['atr_14']) && !empty($ind['high_60'])) {
            $atrMult = $cfg['trailing_stop_atr_mult_core'] ?? 3.0;
            $highestHigh = $ind['high_60'];
            $trailingStop = $highestHigh - ($atrMult * $ind['atr_14']);
            $signals['trailing_stop_breach'] = ($closePrice < $trailingStop) ? 1.0 : 0.0;
            $weights['trailing_stop_breach'] = 0.20;
        }
        
        if (!empty($ind['rsi_14'])) {
            $rsiExit = $cfg['rsi_exit_above'] ?? 65;
            $signals['rsi_overbought'] = ($ind['rsi_14'] > $rsiExit) ? 1.0 : 0.0;
            $weights['rsi_overbought'] = 0.10;
        }
        
        if (!empty($ind['sma_200']) && $ind['sma_200'] > 0) {
            $ma200Threshold = $cfg['price_vs_ma200_exit_below'] ?? 0.95;
            $vsMA200 = $closePrice / $ind['sma_200'];
            $signals['ma200_breakdown'] = ($vsMA200 < $ma200Threshold) ? 1.0 : 0.0;
            $weights['ma200_breakdown'] = 0.15;
        }
        
        if (!empty($ind['bb_20_2_0_upper']) && !empty($ind['bb_20_2_0_lower'])) {
            $bbUpper = $ind['bb_20_2_0_upper'];
            $bbLower = $ind['bb_20_2_0_lower'];
            $bbMid = ($bbUpper + $bbLower) / 2;
            $bbPosition = ($bbUpper != $bbLower) ? ($closePrice - $bbLower) / ($bbUpper - $bbLower) : 0.5;
            $signals['bb_upper_touch'] = ($bbPosition > 0.95) ? 1.0 : 0.0;
            $weights['bb_upper_touch'] = 0.10;
        }
        
        if (!empty($f['roe'])) {
            $signals['roe_deterioration'] = ($f['roe'] < ($cfg['exit_on_roe_drop_below'] ?? 0.10)) ? 1.0 : 0.0;
            $weights['roe_deterioration'] = 0.10;
        }
        
        if (!empty($f['debt_to_equity'])) {
            $signals['debt_equity_rise'] = ($f['debt_to_equity'] > ($cfg['exit_on_debt_equity_above'] ?? 0.60)) ? 1.0 : 0.0;
            $weights['debt_equity_rise'] = 0.10;
        }
        
        if (($cfg['exit_on_fcf_negative'] ?? true) && isset($f['free_cash_flow'])) {
            $signals['fcf_negative'] = ($f['free_cash_flow'] < 0) ? 1.0 : 0.0;
            $weights['fcf_negative'] = 0.10;
        }
        
        if (!empty($f['trailing_pe'])) {
            $signals['pe_extreme'] = ($f['trailing_pe'] > ($cfg['max_pe_core'] ?? 25.0)) ? 1.0 : 0.0;
            $weights['pe_extreme'] = 0.08;
        }
        
        if (!empty($f['market_cap']) && !empty($f['free_cash_flow'])) {
            $fcfYieldThreshold = $cfg['min_fcf_yield_exit_signals'] ?? 0.02;
            $fcfYield = $f['free_cash_flow'] / $f['market_cap'];
            $signals['fcf_yield_low'] = ($fcfYield < $fcfYieldThreshold) ? 1.0 : 0.0;
            $weights['fcf_yield_low'] = 0.05;
        }
        
        if (!empty($ind['close_7d_ago'])) {
            $signals['price_drop_7d'] = ($closePrice < 0.95 * $ind['close_7d_ago']) ? 1.0 : 0.0;
            $weights['price_drop_7d'] = 0.15;
        }
        
        if (!empty($f['insider_ownership']) && $f['insider_ownership'] < 0.10) {
            $signals['insider_selling'] = 1.0;
            $weights['insider_selling'] = 0.05;
        }
        
        if (!empty($f['trailing_pe']) && !empty($f['earnings_quarterly_growth'])
            && $f['trailing_pe'] > 40 && $f['earnings_quarterly_growth'] < 0) {
            $signals['corporate_event_risk'] = 1.0;
            $weights['corporate_event_risk'] = 0.05;
        }
        
        if (!empty($ind['sma_200']) && $ind['sma_200'] > 0) {
            $signals['sector_underperformance'] = ($closePrice < $ind['sma_200']) ? 1.0 : 0.0;
            $weights['sector_underperformance'] = 0.08;
        }
        
        if (!empty($f['earnings_quarterly_growth'])) {
            $signals['earnings_drop'] = ($f['earnings_quarterly_growth'] < 0) ? 1.0 : 0.0;
            $weights['earnings_drop'] = 0.08;
        }
        
        if (!empty($f['dividend_rate']) && !empty($f['market_cap'])) {
            $signals['dividend_cut_signal'] = ($f['dividend_rate'] <= 0) ? 1.0 : 0.0;
            $weights['dividend_cut_signal'] = 0.08;
        }
        
        if (!empty($f['dividend_rate']) && !empty($f['market_cap']) && $f['market_cap'] > 0) {
            $yieldOnCost = $f['dividend_rate'] / $f['market_cap'];
            $signals['yield_on_cost_low'] = ($yieldOnCost < 0.01) ? 1.0 : 0.0;
            $weights['yield_on_cost_low'] = 0.05;
        }
        
        if (!empty($f['total_debt']) && !empty($f['ebitda']) && $f['ebitda'] > 0) {
            $signals['debt_ebitda_high'] = ($f['total_debt'] / $f['ebitda'] > 3) ? 1.0 : 0.0;
            $weights['debt_ebitda_high'] = 0.08;
        }
        
        if (!empty($f['free_cash_flow']) && !empty($f['total_cash']) && !empty($f['total_debt'])) {
            $signals['cash_burn'] = ($f['free_cash_flow'] < 0 && $f['total_cash'] < $f['total_debt']) ? 1.0 : 0.0;
            $weights['cash_burn'] = 0.08;
        }
        
        $totalWeight = array_sum($weights);
        if ($totalWeight > 0) {
            $composite = 0;
            foreach ($weights as $signal => $weight) {
                $composite += ($signals[$signal] ?? 0) * $weight;
            }
            $composite = $composite / $totalWeight;
        } else {
            $composite = 0.5;
        }
        
        return [
            'composite_exit_risk' => round($composite, 3),
            'individual_signals' => array_map(fn($v) => round($v, 3), $signals),
            'signal_weights' => array_map(fn($v) => round($v, 3), $weights),
            'n_signals_triggered' => array_sum(array_map(fn($v) => $v > 0 ? 1 : 0, $signals)),
            'n_signals_total' => count($signals)
        ];
    }
    
    public function getExitSignalConfig(): array {
        $cfgPath = __DIR__ . '/../config.yaml';
        if (file_exists($cfgPath)) {
            $config = yaml_parse_file($cfgPath);
            return $config['signals']['exit_signals'] ?? [];
        }
        return [];
    }

    /**
     * Helper: get rows from a table (graceful if table doesn't exist).
     * Uses resolver so Canadian symbols hit the canonical DB symbol.
     */
    private function getTableData(string $table, string $symbol, string $order = 'date DESC', int $limit = 10): array {
        try {
            $resolved = $this->resolver->resolve($symbol);
            $sql = "SELECT * FROM {$table} WHERE symbol = :sym ORDER BY {$order} LIMIT :lim";
            $stmt = $this->pdo->prepare($sql);
            $stmt->bindValue(':sym', $resolved);
            $stmt->bindValue(':lim', $limit, PDO::PARAM_INT);
            $stmt->execute();
            $result = $stmt->fetchAll();
            return $result;
        } catch (\Exception $e) {
            return [];
        }
    }

    /**
     * Compute Buffett quality score from fundamentals.
     * "Great Company at a Fair Price" — focuses on business fundamentals (moat, financials).
     * Price-related checks moved to separate valuation assessment.
     */
    private function calcBuffettScore(array $f, array $ind, float $closePrice = 0): array {
        $checks = [];
        $score = 0;
        $maxScore = 100;

        $tests = [
            ['ROE > 15%',    fn() => ($f['roe'] ?? 0) > 0.15,  15],
            ['D/E < 0.5',    fn() => ($f['debt_to_equity'] ?? 99) < 0.5, 15],
            ['Margin > 10%', fn() => ($f['profit_margin'] ?? 0) > 0.10, 10],
            ['Positive FCF', fn() => ($f['free_cash_flow'] ?? 0) > 0, 15],
            ['Payout < 60%', fn() => ($f['payout_ratio'] ?? 0) > 0 && ($f['payout_ratio'] ?? 1) < 0.60, 10],
            ['Rev Growth+',  fn() => ($f['revenue_growth'] ?? 0) > 0, 10],
            ['CR > 1.5',     fn() => ($f['current_ratio'] ?? 0) > 1.5, 10],
            ['Beta < 1.2',   fn() => ($f['beta'] ?? 99) > 0 && ($f['beta'] ?? 99) < 1.2, 5],
            ['P/E < 25x',    fn() => ($f['trailing_pe'] ?? 100) > 0 && ($f['trailing_pe'] ?? 100) < 25, 5],
        ];
        foreach ($tests as [$name, $test, $pts]) {
            $passed = $test();
            $checks[$name] = $passed;
            if ($passed) $score += $pts;
        }

        return ['total' => $score, 'score' => $score, 'max' => $maxScore, 'checks' => $checks];
    }

    /**
     * Compute VectorVest 5-point checklist for a single symbol on the detail page.
     *
     * Criteria (same logic as the Python vectorvest_screener advisor):
     *  1. Smooth & steady uptrend — linear-regression slope > 0 and R² >= 0.55 on ~1y closes.
     *  2. Price rising — close > close 20 trading days ago.
     *  3. Earnings rising — forward_eps > 0 or earnings_growth > 0 or trailing_eps > 0.
     *  4. Market on your side — requires SPY benchmark; skipped on detail page.
     *  5. Follow-through — today close > today open AND today close > yesterday close.
     */
    private function calcVectorVest(array $history, array $f, array $latest, array $ind): array
    {
        $checks = [];
        $passCount = 0;

        // Need enough history for regression
        $closes = array_column($history, 'close');
        $n = count($closes);

        // 1) Smooth uptrend (use up to 250 closes ~= 1y)
        if ($n >= 60) {
            $sample = array_slice($closes, -250);
            [$slope, $r2] = $this->linearRegression($sample);
            $smooth = $slope > 0 && $r2 >= 0.55;
            $checks['smooth_uptrend'] = [
                'passed' => $smooth,
                'label' => 'Smooth Uptrend',
                'detail' => "R²=" . round($r2, 2) . ($smooth ? " ✓" : " ✗"),
            ];
            if ($smooth) $passCount++;
        } else {
            $checks['smooth_uptrend'] = ['passed' => false, 'label' => 'Smooth Uptrend', 'detail' => 'insufficient data'];
        }

        // 2) Price rising — close > close 20 days ago
        if ($n > 20) {
            $priceRising = end($closes) > $closes[$n - 21];
            $checks['price_rising'] = [
                'passed' => $priceRising,
                'label' => 'Price Rising (20d)',
                'detail' => $priceRising ? 'close > 20d ago ✓' : 'close < 20d ago ✗',
            ];
            if ($priceRising) $passCount++;
        } else {
            $checks['price_rising'] = ['passed' => false, 'label' => 'Price Rising', 'detail' => 'insufficient data'];
        }

        // 3) Earnings rising
        $earningsRising = false;
        foreach (['forward_eps', 'earnings_growth'] as $k) {
            if (isset($f[$k]) && $f[$k] !== null && $f[$k] !== '' && (float)$f[$k] > 0) {
                $earningsRising = true;
                break;
            }
        }
        if (!$earningsRising && isset($f['trailing_eps']) && $f['trailing_eps'] > 0) {
            $earningsRising = true;
        }
        $checks['earnings_rising'] = [
            'passed' => $earningsRising,
            'label' => 'Earnings Rising',
            'detail' => $earningsRising ? 'positive eps/growth ✓' : 'no positive earnings ✗',
        ];
        if ($earningsRising) $passCount++;

        // 4) Market on your side — needs SPY benchmark; omitted here
        $checks['market_ok'] = [
            'passed' => null,
            'label' => 'Market Trend (SPY)',
            'detail' => 'N/A on detail page',
        ];

        // 5) Follow-through — close > open AND close > yesterday close
        $followThrough = false;
        if (!empty($latest['close']) && !empty($latest['open']) && $n >= 2) {
            $c = (float)$latest['close'];
            $o = (float)$latest['open'];
            $yC = (float)$closes[$n - 2];
            $followThrough = $c > $o && $c > $yC;
        }
        $checks['follow_through'] = [
            'passed' => $followThrough,
            'label' => 'Follow-Through',
            'detail' => $followThrough ? 'close > open & > yday ✓' : 'no follow-through ✗',
        ];
        if ($followThrough) $passCount++;

        $score = $passCount * 20; // 5/5 = 100
        $passed = $passCount >= 4;

        return [
            'checks' => $checks,
            'pass_count' => $passCount,
            'max' => 5,
            'score' => $score,
            'passed' => $passed,
            'note' => 'Market trend check requires screener run with SPY data',
        ];
    }

    /** Ordinary least-squares: returns [slope, r2]. */
    private function linearRegression(array $y): array
    {
        $n = count($y);
        if ($n < 2) return [0.0, 0.0];
        $x = range(0, $n - 1);
        $sx = array_sum($x);
        $sy = array_sum($y);
        $sxy = 0;
        $sxx = 0;
        for ($i = 0; $i < $n; $i++) {
            $sxy += $x[$i] * $y[$i];
            $sxx += $x[$i] * $x[$i];
        }
        $den = $n * $sxx - $sx * $sx;
        if ($den == 0) return [0.0, 0.0];
        $slope = ($n * $sxy - $sx * $sy) / $den;
        $intercept = ($sy - $slope * $sx) / $n;
        $ssRes = 0;
        $ssTot = 0;
        $meanY = $sy / $n;
        for ($i = 0; $i < $n; $i++) {
            $ssRes += ($y[$i] - ($slope * $x[$i] + $intercept)) ** 2;
            $ssTot += ($y[$i] - $meanY) ** 2;
        }
        $r2 = $ssTot > 0 ? 1 - $ssRes / $ssTot : 0.0;
        return [(float)$slope, (float)$r2];
    }

    /**
     * Compute a Zacks-style composite score using available fundamentals + indicators.
     * Grades: A=90-100, B=80-89, C=70-79, D=60-69, F=<60
     * Rank: 1=Strong Buy, 2=Buy, 3=Hold, 4=Sell, 5=Strong Sell
     */
    public function calcZacksStyleScore(array $f, array $ind, float $closePrice = 0): array {
        $checks = [];
        $maxScore = 100;

        $hasFundamental = false;
        foreach (['trailing_pe','price_to_book','free_cash_flow','market_cap','debt_to_equity','earnings_growth','revenue_growth','roe','forward_pe','peg_ratio','price_to_sales','book_value','total_revenue'] as $k) {
            if (isset($f[$k]) && $f[$k] !== null && $f[$k] !== '') {
                $hasFundamental = true;
                break;
            }
        }
        if (!$hasFundamental) {
            return [
                'rank' => null,
                'rank_text' => 'N/A',
                'composite' => null,
                'value_grade' => 'N/A',
                'growth_grade' => 'N/A',
                'momentum_grade' => 'N/A',
                'vgm_grade' => 'N/A',
                'value_pct' => null,
                'growth_pct' => null,
                'momentum_pct' => null,
                'vgm_pct' => null,
                'checks' => ['Fundamental data not available'],
            ];
        }

        // Value (40 points): low PE, low PB, high FCF yield, manageable debt
        $valueScore = 0;
        $maxValue = 0;
        if (!empty($f['trailing_pe']) && $f['trailing_pe'] > 0) {
            $pe = (float)$f['trailing_pe'];
            $checks['P/E < 20x'] = $pe < 20;
            $maxValue += 10;
            if ($pe < 15) $valueScore += 10;
            elseif ($pe < 20) $valueScore += 7;
            elseif ($pe < 30) $valueScore += 4;
        }
        if (!empty($f['price_to_book']) && $f['price_to_book'] > 0) {
            $pb = (float)$f['price_to_book'];
            $checks['P/B < 2.0'] = $pb < 2.0;
            $maxValue += 10;
            if ($pb < 1.0) $valueScore += 10;
            elseif ($pb < 2.0) $valueScore += 7;
            elseif ($pb < 3.0) $valueScore += 4;
        }
        if (!empty($f['free_cash_flow']) && !empty($f['market_cap']) && $f['market_cap'] > 0) {
            $fcfYield = (float)$f['free_cash_flow'] / (float)$f['market_cap'];
            $checks['FCF Yield > 3%'] = $fcfYield > 0.03;
            $maxValue += 10;
            if ($fcfYield > 0.06) $valueScore += 10;
            elseif ($fcfYield > 0.03) $valueScore += 7;
            elseif ($fcfYield > 0.01) $valueScore += 4;
        }
        if (!empty($f['debt_to_equity'])) {
            $de = (float)$f['debt_to_equity'];
            $checks['D/E < 0.8'] = $de < 0.8;
            $maxValue += 10;
            if ($de < 0.3) $valueScore += 10;
            elseif ($de < 0.8) $valueScore += 7;
            elseif ($de < 1.5) $valueScore += 4;
        }
        $valuePct = $maxValue > 0 ? min(100, ($valueScore / $maxValue) * 100) : 0;
        $valueGrade = $valuePct >= 90 ? 'A' : ($valuePct >= 80 ? 'B' : ($valuePct >= 70 ? 'C' : ($valuePct >= 60 ? 'D' : 'F')));

        // Growth (30 points): EPS growth, revenue growth
        $growthScore = 0;
        $maxGrowth = 0;
        if (!empty($f['earnings_growth'])) {
            $eg = (float)$f['earnings_growth'];
            $checks['EPS Growth > 10%'] = $eg > 0.10;
            $maxGrowth += 15;
            if ($eg > 0.20) $growthScore += 15;
            elseif ($eg > 0.10) $growthScore += 10;
            elseif ($eg > 0) $growthScore += 5;
        }
        if (!empty($f['revenue_growth'])) {
            $rg = (float)$f['revenue_growth'];
            $checks['Revenue Growth > 5%'] = $rg > 0.05;
            $maxGrowth += 15;
            if ($rg > 0.15) $growthScore += 15;
            elseif ($rg > 0.05) $growthScore += 10;
            elseif ($rg > 0) $growthScore += 5;
        }
        $growthPct = $maxGrowth > 0 ? min(100, ($growthScore / $maxGrowth) * 100) : 0;
        $growthGrade = $growthPct >= 90 ? 'A' : ($growthPct >= 80 ? 'B' : ($growthPct >= 70 ? 'C' : ($growthPct >= 60 ? 'D' : 'F')));

        // Momentum (20 points): price vs SMA200, RSI not overbought
        $momentumScore = 0;
        if (!empty($ind['sma_200']) && $ind['sma_200'] > 0 && $closePrice > 0) {
            $vsSMA = $closePrice / (float)$ind['sma_200'];
            $checks['Price > SMA200'] = $vsSMA > 1.0;
            if ($vsSMA > 1.05) $momentumScore += 10;
            elseif ($vsSMA > 1.0) $momentumScore += 7;
            elseif ($vsSMA > 0.95) $momentumScore += 4;
        }
        if (!empty($ind['rsi_14'])) {
            $rsi = (float)$ind['rsi_14'];
            $checks['RSI 30-65'] = $rsi >= 30 && $rsi <= 65;
            if ($rsi >= 40 && $rsi <= 60) $momentumScore += 10;
            elseif ($rsi >= 30 && $rsi <= 70) $momentumScore += 6;
            elseif ($rsi >= 20 && $rsi <= 80) $momentumScore += 3;
        }
        $momentumPct = min(100, ($momentumScore / 20) * 100);
        $momentumGrade = $momentumPct >= 90 ? 'A' : ($momentumPct >= 80 ? 'B' : ($momentumPct >= 70 ? 'C' : ($momentumPct >= 60 ? 'D' : 'F')));

        // VGM composite
        $vgmPct = ($valuePct + $growthPct + $momentumPct) / 3;
        $vgmGrade = $vgmPct >= 90 ? 'A' : ($vgmPct >= 80 ? 'B' : ($vgmPct >= 70 ? 'C' : ($vgmPct >= 60 ? 'D' : 'F')));

        // Zacks Rank 1-5 from weighted composite
        $composite = ($valuePct * 0.40) + ($growthPct * 0.30) + ($momentumPct * 0.20) + ($vgmPct * 0.10);
        $rank = 5;
        if ($composite >= 90) $rank = 1;
        elseif ($composite >= 80) $rank = 2;
        elseif ($composite >= 70) $rank = 3;
        elseif ($composite >= 60) $rank = 4;

        $rankText = ['1' => 'Strong Buy', '2' => 'Buy', '3' => 'Hold', '4' => 'Sell', '5' => 'Strong Sell'][$rank];

        return [
            'rank' => $rank,
            'rank_text' => $rankText,
            'composite' => round($composite, 1),
            'value_grade' => $valueGrade,
            'growth_grade' => $growthGrade,
            'momentum_grade' => $momentumGrade,
            'vgm_grade' => $vgmGrade,
            'value_pct' => round($valuePct, 1),
            'growth_pct' => round($growthPct, 1),
            'momentum_pct' => round($momentumPct, 1),
            'vgm_pct' => round($vgmPct, 1),
            'checks' => $checks,
        ];
    }

    /**
     * GET /?action=portfolio — Portfolio holdings.
     */
    public function portfolio(string $account_filter = 'all', int $user_id = 0): array {
        // Build account filter
        $where = '';
        if ($account_filter !== 'all') {
            $where = "WHERE p.account_type = " . $this->pdo->quote($account_filter);
        }

        // Aggregate across accounts: each symbol appears once with total shares & weighted cost basis
        $accountJoin = '';
        $accountWhere = '';
        $userCondition = '';
        $params = [];
        if ($account_filter !== 'all') {
            $af = $this->pdo->quote($account_filter);
            $accountWhere = "WHERE p.account_type = $af";
        }
        if ($user_id > 0) {
            $userCondition = $accountWhere ? "AND p.user_id = :uid" : "WHERE p.user_id = :uid";
            $params[':uid'] = $user_id;
        }

        $sql = "
            SELECT p.symbol,
                   GROUP_CONCAT(DISTINCT p.account_type ORDER BY p.account_type) as accounts,
                   SUM(p.shares) as shares,
                   SUM(p.shares * p.cost_basis) / NULLIF(SUM(p.shares), 0) as cost_basis,
                   MIN(p.entry_date) as entry_date,
                   AVG(p.trailing_stop_pct) as trailing_stop_pct,
                   AVG(p.stop_loss_pct) as stop_loss_pct,
                   p.strategy,
                   AVG(p.atr_multiplier) as atr_multiplier,
                   latest.close as current_price,
                   latest.volume as current_volume,
                   latest.price_date as price_date
            FROM portfolio p
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close, sp1.volume, sp1.price_date
                FROM stockprices sp1
                INNER JOIN (
                    SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol
                ) sp2 ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON COALESCE(p.price_symbol, p.symbol) = latest.symbol
            $userCondition
            GROUP BY p.symbol
            ORDER BY p.symbol
        ";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        $holdings = $stmt->fetchAll();

        $fctrl = new FundamentalsController();

        $totalCost = 0;
        $totalValue = 0;
        foreach ($holdings as &$h) {
            $symbol = $h['symbol'];
            $currentPrice = $h['current_price'] ?? 0;
            $costTotal = $h['shares'] * $h['cost_basis'];
            $currentValue = $h['shares'] * $currentPrice;
            $pnl = $currentValue - $costTotal;
            $pnlPct = $costTotal > 0 ? ($pnl / $costTotal) * 100 : 0;

            // Annualized P&L (years held)
            $entryDate = $h['entry_date'] ?? null;
            if ($entryDate) {
                $daysHeld = max(1, (new DateTime())->diff(new DateTime($entryDate))->days);
                $yearsHeld = $daysHeld / 365.25;
                $annualizedPnlPct = $yearsHeld > 0 ? ((pow($currentValue / $costTotal, 1 / $yearsHeld)) - 1) * 100 : 0;
            } else {
                $daysHeld = null;
                $annualizedPnlPct = null;
            }

            // Fundamentals
            $fund = $fctrl->getSymbol($symbol);
            $pe = $fund['trailing_pe'] ?? null;
            $divYield = $fund['dividend_yield'] ?? null;

            // Cost-basis dividend yield (annual income / cost)
            $annualDivPerShare = ($fund['dividend_rate'] ?? 0);
            $costBasisDivYield = $h['cost_basis'] > 0 ? ($annualDivPerShare / $h['cost_basis']) * 100 : null;
            $currentDivYield = $currentPrice > 0 ? ($annualDivPerShare / $currentPrice) * 100 : null;

            // Dividend safety
            $divSafety = $fctrl->getDividendSafety($symbol);

            // Indicators for stop calculations
            $indicators = $this->getLatestIndicators($symbol);
            $atr14 = $indicators['atr_14'] ?? null;
            $sma200 = $indicators['sma_200'] ?? null;

            // Stop calculations
            $trailingStopPct = $h['trailing_stop_pct'] ?? 0.10;  // default 10%
            $stopLossPct = $h['stop_loss_pct'] ?? 0.15;            // default 15%
            $trailingStopPrice = $currentPrice > 0 ? $currentPrice * (1 - $trailingStopPct) : 0;
            $stopLossPrice = $h['cost_basis'] * (1 - $stopLossPct);
            // Effective stop = max(trailing, stop_loss) — trailing overrides when higher
            $effectiveStopPrice = max($trailingStopPrice, $stopLossPrice);
            $stopStatus = $currentPrice > 0 ? ($effectiveStopPrice >= $currentPrice ? 'breach' : ($effectiveStopPrice >= $currentPrice * 0.98 ? 'warning' : 'safe')) : 'na';

            // Strategy details
            $strategy = $h['strategy'] ?? 'Trailing Stop';
            $atrMultiplier = $h['atr_multiplier'] ?? 2.0;

            $h['cost_total'] = $costTotal;
            $h['current_value'] = $currentValue;
            $h['pnl'] = $pnl;
            $h['pnl_pct'] = $pnlPct;
            $h['annualized_pnl_pct'] = $annualizedPnlPct;
            $h['days_held'] = $daysHeld;
            $h['fundamentals'] = $fund;
            $h['pe'] = $pe;
            $h['div_yield'] = $divYield;
            $h['annual_div_per_share'] = $annualDivPerShare;
            $h['cost_basis_div_yield'] = $costBasisDivYield;
            $h['current_div_yield'] = $currentDivYield;
            $h['dividend_safety'] = $divSafety;
            $h['atr_14'] = $atr14;
            $h['sma_200'] = $sma200;
            $h['trailing_stop_pct'] = $trailingStopPct;
            $h['trailing_stop_price'] = $trailingStopPrice;
            $h['stop_loss_pct'] = $stopLossPct;
            $h['stop_loss_price'] = $stopLossPrice;
            $h['effective_stop_price'] = $effectiveStopPrice;
            $h['stop_status'] = $stopStatus;
            $h['strategy'] = $strategy;
            $h['atr_multiplier'] = $atrMultiplier;

            $totalCost += $costTotal;
            $totalValue += $currentValue;
        }

        $totalPnl = $totalValue - $totalCost;
        $totalPnlPct = $totalCost > 0 ? ($totalPnl / $totalCost) * 100 : 0;

        // Annualized total
        // (approximate: use average holding period)
        $totalDays = 0;
        $count = 0;
        foreach ($holdings as $h) {  // not &$h, we don't modify here
            if ($h['days_held']) {
                $totalDays += $h['days_held'];
                $count++;
            }
        }
        $avgYears = $count > 0 ? ($totalDays / $count) / 365.25 : 0;
        $totalAnnualizedPnlPct = $avgYears > 0 && $totalCost > 0 ? ((pow($totalValue / $totalCost, 1 / $avgYears)) - 1) * 100 : 0;

        return [
            'holdings' => $holdings,
            'total_cost' => $totalCost,
            'total_value' => $totalValue,
            'total_pnl' => $totalPnl,
            'total_pnl_pct' => $totalPnlPct,
            'total_annualized_pnl_pct' => $totalAnnualizedPnlPct,
            'account_filter' => $account_filter,
            'account_types' => array_unique(array_column($holdings, 'account_type')),
        ];
    }

    /**
     * Get latest technical indicators for a symbol (for stop calculations).
     * Uses resolver so Canadian symbols hit the canonical DB symbol.
     */
    private function getLatestIndicators(string $symbol): array {
        $this->refreshIndicatorsJsonIfStale($symbol);
        $resolved = $this->resolver->resolve($symbol);
        $stmt = $this->pdo->prepare("
            SELECT data FROM indicators_json
            WHERE symbol = :sym
            ORDER BY price_date DESC LIMIT 1
        ");
        $stmt->execute([':sym' => $resolved]);
        $row = $stmt->fetch();
        
        if (!$row) return [];
        return json_decode($row['data'] ?: $row[0], true) ?: [];
    }

    private function refreshIndicatorsJsonIfStale(string $symbol): void {
        $resolved = $this->resolver->resolve($symbol);
        $stmt = $this->pdo->prepare("
            SELECT updated_date FROM indicators_json
            WHERE symbol = :sym
            ORDER BY price_date DESC LIMIT 1
        ");
        $stmt->execute([':sym' => $resolved]);
        $row = $stmt->fetch();

        $today = date('Y-m-d');
        $last = $row ? substr($row['updated_date'], 0, 10) : '';
        if ($last !== $today) {
            $this->refreshIndicatorsJson($resolved);
            if ($resolved !== $symbol) {
                $this->refreshIndicatorsJson($symbol);
            }
        }
    }

    private function refreshIndicatorsJson(string $symbol): void {
        $stmt = $this->pdo->prepare("
            SELECT * FROM indicators WHERE symbol = :sym ORDER BY price_date DESC LIMIT 1
        ");
        $stmt->execute([':sym' => $symbol]);
        $row = $stmt->fetch();
        if (!$row) return;

        $data = $row;
        unset($data['id'], $data['symbol'], $data['price_date']);
        $pdate = $row['price_date'];

        $up = $this->pdo->prepare("
            INSERT INTO indicators_json (symbol, price_date, data)
            VALUES (:sym, :pdate, :data)
            ON DUPLICATE KEY UPDATE data = :data, updated_date = NOW()
        ");
        $up->execute([
            ':sym' => $symbol,
            ':pdate' => $pdate,
            ':data' => json_encode($data),
        ]);
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

    /**
     * GET /?action=stop_orders — List stop loss / trailing stop orders with prices.
     */
    public function stopOrders(string $account_filter = 'all'): array {
        $holdings = $this->getHoldingsWithPrices($account_filter);
        $orders = [];

        foreach ($holdings as $h) {
            $symbol = $h['symbol'];
            $currentPrice = $h['current_price'] ?? 0;
            
            // Skip if no current price
            if (!$currentPrice) continue;

            // Get ATR for ATR-based stops
            $indicators = $this->getLatestIndicators($symbol);
            $atr14 = $indicators['atr_14'] ?? null;

            // Calculate stop prices
            $trailingStopPct = $h['trailing_stop_pct'] ?? 0.10;
            $stopLossPct = $h['stop_loss_pct'] ?? 0.15;
            $atrMultiplier = $h['atr_multiplier'] ?? 2.0;

            $trailingStopPrice = $currentPrice > 0 ? $currentPrice * (1 - $trailingStopPct) : 0;
            $stopLossPrice = $h['cost_basis'] * (1 - $stopLossPct);
            $atrStopPrice = $atr14 ? $currentPrice - ($atr14 * $atrMultiplier) : null;

            // Effective stop = max of trailing and stop_loss
            $effectiveStopPrice = max($trailingStopPrice, $stopLossPrice);

            // Determine stop status
            if ($effectiveStopPrice >= $currentPrice) {
                $stopStatus = 'breach';
            } elseif ($effectiveStopPrice >= $currentPrice * 0.98) {
                $stopStatus = 'warning';
            } else {
                $stopStatus = 'safe';
            }

            $orders[] = [
                'symbol' => $symbol,
                'accounts' => $h['accounts'],
                'shares' => $h['shares'],
                'cost_basis' => $h['cost_basis'],
                'current_price' => $currentPrice,
                'price_date' => $h['price_date'],
                'market_value' => $h['shares'] * $currentPrice,
                'trailing_stop_pct' => $trailingStopPct,
                'trailing_stop_price' => $trailingStopPrice,
                'stop_loss_pct' => $stopLossPct,
                'stop_loss_price' => $stopLossPrice,
                'atr_14' => $atr14,
                'atr_multiplier' => $atrMultiplier,
                'atr_stop_price' => $atrStopPrice,
                'effective_stop_price' => max($effectiveStopPrice, $atrStopPrice ?: 0),
                'stop_status' => $stopStatus,
                'strategy' => $h['strategy'] ?? 'Trailing Stop',
            ];
        }

        return [
            'pageTitle' => 'Stop Orders',
            'template' => 'stop_orders',
            'orders' => $orders,
            'total_orders' => count($orders),
            'account_filter' => $account_filter,
            'account_types' => array_unique(array_merge(...array_map(fn($o) => explode(',', $o['accounts']), $orders))),
        ];
    }

    /**
     * Helper: Get holdings with current prices (extracted from portfolio method).
     */
    private function getHoldingsWithPrices(string $account_filter = 'all'): array {
        $accountWhere = '';
        if ($account_filter !== 'all') {
            $af = $this->pdo->quote($account_filter);
            $accountWhere = "WHERE p.account_type = $af";
        }
        
        $stmt = $this->pdo->query("
            SELECT p.symbol,
                   GROUP_CONCAT(DISTINCT p.account_type ORDER BY p.account_type) as accounts,
                   SUM(p.shares) as shares,
                   SUM(p.shares * p.cost_basis) / NULLIF(SUM(p.shares), 0) as cost_basis,
                   AVG(p.trailing_stop_pct) as trailing_stop_pct,
                   AVG(p.stop_loss_pct) as stop_loss_pct,
                   p.strategy,
                   AVG(p.atr_multiplier) as atr_multiplier,
                   latest.close as current_price,
                   latest.price_date as price_date
            FROM portfolio p
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close, sp1.price_date
                FROM stockprices sp1
                INNER JOIN (
                    SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol
                ) sp2 ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON p.symbol = latest.symbol
            {$accountWhere}
            GROUP BY p.symbol
            HAVING SUM(p.shares) > 0
            ORDER BY p.symbol
        ");
        return $stmt->fetchAll();
    }
    
    /**
     * Markov regime analysis — compute transition matrix from price data.
     */
    private function getRegimeAnalysis(string $symbol): array {
        // Get 252 days of close prices
        $stmt = $this->pdo->prepare("SELECT price_date, close FROM stockprices WHERE symbol = :sym ORDER BY price_date DESC LIMIT 252");
        $stmt->execute([':sym' => $symbol]);
        $rows = array_reverse($stmt->fetchAll());
        
        if (count($rows) < 252) {
            return ['current_regime' => null, 'transition_matrix' => [], 'stationary_distribution' => []];
        }
        
        // Compute regimes (20-day rolling return threshold 5%)
        $closes = array_column($rows, 'close');
        $regimes = [];
        
        for ($i = 20; $i < count($closes); $i++) {
            $windowReturn = ($closes[$i] - $closes[$i - 20]) / $closes[$i - 20];
            if ($windowReturn > 0.05) {
                $regimes[] = 2; // Bull
            } elseif ($windowReturn < -0.05) {
                $regimes[] = 0; // Bear
            } else {
                $regimes[] = 1; // Sideways
            }
        }
        
        if (empty($regimes)) {
            return ['current_regime' => null, 'transition_matrix' => [], 'stationary_distribution' => []];
        }
        
        // Build 3x3 transition matrix
        $matrix = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
        for ($i = 1; $i < count($regimes); $i++) {
            $from = $regimes[$i - 1];
            $to = $regimes[$i];
            $matrix[$from][$to]++;
        }
        
        // Convert to probabilities
        $transitionMatrix = [];
        $stateLabels = ['Bear', 'Sideways', 'Bull'];
        foreach ([0, 1, 2] as $from) {
            $rowSum = array_sum($matrix[$from]);
            if ($rowSum > 0) {
                foreach ([0, 1, 2] as $to) {
                    $transitionMatrix[$stateLabels[$from]][$stateLabels[$to]] = round($matrix[$from][$to] / $rowSum, 4);
                }
            }
        }
        
        // Compute stationary distribution (eigendecomposition)
        // For 3x3 matrix, use power iteration
        $pi = [0.33, 0.33, 0.34]; // Initial guess
        $P = $transitionMatrix;
        
        // Convert to numeric matrix for calculation
        $Pnum = [
            [(float)($P['Bear']['Bear'] ?? 0), (float)($P['Bear']['Sideways'] ?? 0), (float)($P['Bear']['Bull'] ?? 0)],
            [(float)($P['Sideways']['Bear'] ?? 0), (float)($P['Sideways']['Sideways'] ?? 0), (float)($P['Sideways']['Bull'] ?? 0)],
            [(float)($P['Bull']['Bear'] ?? 0), (float)($P['Bull']['Sideways'] ?? 0), (float)($P['Bull']['Bull'] ?? 0)]
        ];
        
        // 50 iterations of P^n
        for ($iter = 0; $iter < 50; $iter++) {
            $newPi = [0, 0, 0];
            foreach ([0, 1, 2] as $to) {
                foreach ([0, 1, 2] as $from) {
                    $newPi[$to] += $pi[$from] * $Pnum[$from][$to];
                }
            }
            $pi = $newPi;
        }
        
        $stationary = [
            'Bear' => round($pi[0], 4),
            'Sideways' => round($pi[1], 4),
            'Bull' => round($pi[2], 4)
        ];
        return [
            'current_regime' => $stateLabels[end($regimes)],
            'transition_matrix' => $transitionMatrix,
            'stationary_distribution' => $stationary
        ];
    }

    private function runPythonRefresh(string $symbol, ?bool $fullHistory, ?int $days): void
    {
        $workerUrl = rtrim((string) ($_ENV['PYTHON_WORKER_URL'] ?? ''), '/');
        if ($workerUrl === '') {
            throw new RuntimeException('PYTHON_WORKER_URL is not configured for Python update.');
        }

        $payload = [
            'symbol' => $symbol,
            'full_history' => $fullHistory ? 1 : 0,
            'days' => $days,
        ];

        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $workerUrl . '/worker/refresh_prices',
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($payload),
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_TIMEOUT => 90,
        ]);
        $raw = curl_exec($ch);
        if ($raw === false) {
            $err = curl_error($ch);
            curl_close($ch);
            throw new RuntimeException('Python worker request failed: ' . $err);
        }
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code < 200 || $code >= 300) {
            throw new RuntimeException('Python worker responded with status ' . $code . ': ' . substr((string) $raw, 0, 200));
        }
    }

    /**
     * GET /?action=refresh_price&symbol=SU.TO — Trigger price refresh for one symbol.
     */
    public function refreshPrice(string $symbol): array {
        $symbol = $this->resolver->resolve(strtoupper(trim($symbol)));
        if (!preg_match('/^[A-Z][A-Z0-9\\\\.\\\\-]*$/', $symbol)) {
            $_SESSION['flash_error'] = 'Invalid symbol.';
            header('Location: /stockmarket/?action=overview');
            exit;
        }

        $script = __DIR__ . '/../../../python/fetch_prices.py';
        if (!file_exists($script)) {
            $_SESSION['flash_error'] = 'Price fetcher not found.';
            header('Location: /stockmarket/?action=detail&symbol=' . urlencode($symbol));
            exit;
        }

        $fullHistory = isset($_REQUEST['full_history']) && $_REQUEST['full_history'] == '1';
        $startDate = null;

        if (!$fullHistory) {
            try {
                $stmt = $this->pdo->prepare("SELECT MAX(price_date) as last_date FROM stockprices WHERE symbol = :sym");
                $stmt->execute([':sym' => $symbol]);
                $lastDate = $stmt->fetchColumn();
                if ($lastDate) {
                    $last = new DateTime($lastDate);
                    $now = new DateTime();
                    $diff = $now->diff($last);
                    $daysSince = (int)$diff->format('%a');
                    if ($daysSince < 1) {
                        $daysSince = 1;
                    }
                    $startDate = (new DateTime("-$daysSince days"))->format('Y-m-d');
                    $_SESSION['flash_message'] = "Refreshing last {$daysSince} day(s) of data for {$symbol} (since {$lastDate}).";
                } else {
                    $fullHistory = true;
                    $_SESSION['flash_message'] = "No existing data found. Fetching full history for {$symbol}.";
                }
            } catch (Exception $e) {
                $fullHistory = true;
            }
        }

        $cmd = [
            PHP_BINARY,
            $script,
            '--symbols', $symbol,
        ];

        if ($fullHistory) {
            $cmd[] = '--full-history';
        } elseif ($daysSince > 0) {
            $cmd[] = '--days';
            $cmd[] = (string)$daysSince;
        }

        try {
            $proc = proc_open(
                $cmd,
                [['pipe', 'r'], ['pipe', 'w'], ['pipe', 'w']],
                $pipes,
                dirname($script),
                null,
                ['bypass_shell' => true]
            );
            if (is_resource($proc)) {
                fclose($pipes[0]);
                stream_set_blocking($pipes[1], false);
                stream_set_blocking($pipes[2], false);
                $stdout = stream_get_contents($pipes[1]);
                $stderr = stream_get_contents($pipes[2]);
                fclose($pipes[1]);
                fclose($pipes[2]);
                $rc = proc_close($proc);
                if ($rc === 0) {
                    // flash already set above
                } else {
                    $_SESSION['flash_error'] = "Price refresh failed for {$symbol}: " . substr($stderr ?: $stdout, 0, 200);
                }
            } else {
                $_SESSION['flash_error'] = 'Could not start price refresh process.';
            }
        } catch (Exception $e) {
            $this->runPythonRefresh($symbol, $fullHistory, $daysSince > 0 ? $daysSince : null);
            $_SESSION['flash_message'] = "Updated last " . ($daysSince > 0 ? $daysSince . ' day(s)' : 'window') . " of data for {$symbol}.";
        }

        $isAjax = !empty($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest';
        if ($isAjax) {
            header('Content-Type: application/json');
            echo json_encode([
                'success' => empty($_SESSION['flash_error']),
                'message' => $_SESSION['flash_message'] ?? '',
                'error' => $_SESSION['flash_error'] ?? '',
                'symbol' => $symbol,
            ]);
            exit;
        }

        header('Location: /stockmarket/?action=detail&symbol=' . urlencode($symbol));
        exit;
    }

    /**
     * GET/POST /?action=manual_ohlcv — Manual OHLCV entry + CSV import.
     */
    public function manualOhlcv(): array {
        $message = '';
        $error = '';
        $imported = 0;
        $skipped = 0;

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            // Single-row form submission
            if (!empty($_POST['single_symbol'])) {
                $rawSym = strtoupper(trim($_POST['single_symbol'] ?? ''));
                $sym = $this->resolver->resolve($rawSym);
                $row = [
                    'symbol' => $sym,
                    'date'   => trim($_POST['single_date'] ?? ''),
                    'open'   => $_POST['single_open'] !== '' ? (float)$_POST['single_open'] : null,
                    'high'   => $_POST['single_high'] !== '' ? (float)$_POST['single_high'] : null,
                    'low'    => $_POST['single_low'] !== '' ? (float)$_POST['single_low'] : null,
                    'close'  => $_POST['single_close'] !== '' ? (float)$_POST['single_close'] : null,
                    'volume' => $_POST['single_volume'] !== '' ? (int)$_POST['single_volume'] : null,
                    'adj_close' => $_POST['single_adj_close'] !== '' ? (float)$_POST['single_adj_close'] : null,
                    'dividend'  => $_POST['single_dividend'] !== '' ? (float)$_POST['single_dividend'] : 0,
                    'split_ratio' => $_POST['single_split'] !== '' ? (float)$_POST['single_split'] : 1,
                ];
                if (!preg_match('/^[A-Z][A-Z0-9\\.\\-]*$/', $sym) || !preg_match('/^\\d{4}-\\d{2}-\\d{2}$/', $row['date'])) {
                    $error = 'Invalid symbol or date (YYYY-MM-DD).';
                } else {
                    try {
                        $stmt = $this->pdo->prepare('INSERT IGNORE INTO stockprices (symbol,price_date,open,high,low,close,volume,adj_close,dividend,split_ratio) VALUES (:s,:d,:o,:h,:l,:c,:v,:a,:div,:split)');
                        $stmt->execute([
                            ':s' => $row['symbol'], ':d' => $row['date'],
                            ':o' => $row['open'], ':h' => $row['high'], ':l' => $row['low'],
                            ':c' => $row['close'], ':v' => $row['volume'], ':a' => $row['adj_close'] ?? $row['close'],
                            ':div' => $row['dividend'], ':split' => $row['split_ratio'],
                        ]);
                        if ($stmt->rowCount() > 0) {
                            $imported = 1;
                            $message = "Inserted 1 row for {$row['symbol']} on {$row['date']}.";
                        } else {
                            $skipped = 1;
                            $error = "Duplicate: {$row['symbol']} on {$row['date']} already exists.";
                        }
                    } catch (Exception $e) {
                        $error = 'DB error: ' . $e->getMessage();
                    }
                }
            }

            // CSV upload
            if (!empty($_FILES['csv_file']['tmp_name'])) {
                $handle = fopen($_FILES['csv_file']['tmp_name'], 'r');
                if ($handle) {
                    $headers = fgetcsv($handle);
                    $map = $this->mapCsvHeaders($headers);
                    if (!$map['symbol'] || !$map['date']) {
                        $error .= ($error ? ' | ' : '') . 'CSV must contain a symbol and date column.';
                    } else {
                        $batch = [];
                        while (($row = fgetcsv($handle)) !== false) {
                            if (count($row) < count($headers)) continue;
                            $data = [];
                            foreach ($headers as $idx => $h) {
                                $field = $map[$h] ?? null;
                                if ($field) $data[$field] = $row[$idx];
                            }
                            if (empty($data['symbol']) || empty($data['date'])) continue;
                            $data['symbol'] = strtoupper($data['symbol']);
                            $data['open']   = isset($data['open']) && $data['open'] !== '' ? (float)$data['open'] : null;
                            $data['high']   = isset($data['high']) && $data['high'] !== '' ? (float)$data['high'] : null;
                            $data['low']    = isset($data['low']) && $data['low'] !== '' ? (float)$data['low'] : null;
                            $data['close']  = isset($data['close']) && $data['close'] !== '' ? (float)$data['close'] : null;
                            $data['volume'] = isset($data['volume']) && $data['volume'] !== '' ? (int)$data['volume'] : null;
                            $data['adj_close'] = isset($data['adj_close']) && $data['adj_close'] !== '' ? (float)$data['adj_close'] : ($data['close'] ?? null);
                            $data['dividend']  = isset($data['dividend']) && $data['dividend'] !== '' ? (float)$data['dividend'] : 0;
                            $data['split_ratio'] = isset($data['split_ratio']) && $data['split_ratio'] !== '' ? (float)$data['split_ratio'] : 1;
                            if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $data['date'])) continue;
                            $batch[] = $data;
                        }
                        fclose($handle);
                        if ($batch) {
                            try {
                                $this->pdo->beginTransaction();
                                $stmt = $this->pdo->prepare('INSERT IGNORE INTO stockprices (symbol,price_date,open,high,low,close,volume,adj_close,dividend,split_ratio) VALUES (:s,:d,:o,:h,:l,:c,:v,:a,:div,:split)');
                                foreach ($batch as $r) {
                                    $stmt->execute([
                                        ':s' => $r['symbol'], ':d' => $r['date'],
                                        ':o' => $r['open'], ':h' => $r['high'], ':l' => $r['low'],
                                        ':c' => $r['close'], ':v' => $r['volume'], ':a' => $r['adj_close'],
                                        ':div' => $r['dividend'], ':split' => $r['split_ratio'],
                                    ]);
                                    if ($stmt->rowCount() > 0) $imported++;
                                    else $skipped++;
                                }
                                $this->pdo->commit();
                                $message .= ($message ? ' | ' : '') . "CSV imported: {$imported} rows inserted, {$skipped} duplicates skipped.";
                            } catch (Exception $e) {
                                $this->pdo->rollBack();
                                $error .= ($error ? ' | ' : '') . 'Import failed: ' . $e->getMessage();
                            }
                        }
                    }
                }
            }
        }

        return [
            'message' => $message,
            'error' => $error,
            'imported' => $imported,
            'skipped' => $skipped,
        ];
    }

    private function mapCsvHeaders(array $headers): array {
        $map = [];
        foreach ($headers as $h) {
            $h = strtolower(trim($h));
            if (!$h) continue;
            if (str_starts_with($h, 'adj') || $h === 'adjusted close' || $h === 'adj_close' || $h === 'adjclose') $map[$h] = 'adj_close';
            elseif (str_contains($h, 'split')) $map[$h] = 'split_ratio';
            elseif (str_contains($h, 'dividend') || $h === 'div') $map[$h] = 'dividend';
            elseif (str_contains($h, 'volume') || $h === 'vol') $map[$h] = 'volume';
            elseif (str_contains($h, 'open')) $map[$h] = 'open';
            elseif (str_contains($h, 'high')) $map[$h] = 'high';
            elseif (str_contains($h, 'low')) $map[$h] = 'low';
            elseif (str_contains($h, 'close') || $h === 'last') $map[$h] = 'close';
            elseif (str_contains($h, 'symbol') || str_contains($h, 'ticker') || $h === 'sym') $map[$h] = 'symbol';
            elseif (str_contains($h, 'date') || str_contains($h, 'time') || str_contains($h, 'day') || $h === 'datetime') $map[$h] = 'date';
        }
        return $map;
    }

    /**
     * GET /?action=screener — Display TradingView screener results.
     */
    public function screener(string $preset = 'dividend_stocks', ?string $sort = null, ?string $sector = null): array {
        // Available presets with markets
        $presets = [
            'dividend_stocks' => ['label' => 'Dividend Stocks (Yield >3%)', 'market' => 'america'],
            'quality_compounder' => ['label' => 'Quality Compunders', 'market' => 'america'],
            'value_stocks' => ['label' => 'Value Stocks (P/E <15)', 'market' => 'america'],
            'canadian_dividends' => ['label' => 'Canadian Dividends (Yield >3%)', 'market' => 'canada'],
            'low_cost_index_funds' => ['label' => 'Low-Cost Index Funds', 'market' => 'canada'],
            'buffett' => ['label' => 'Buffett Quality Score', 'market' => 'local'],
            'zacks' => ['label' => 'Zacks-Style Composite', 'market' => 'local'],
            'vectorvest' => ['label' => 'VectorVest Safe Stock', 'market' => 'local'],
            'exit_risk' => ['label' => 'Low Exit Risk', 'market' => 'local'],
        ];
        
        if (!isset($presets[$preset])) {
            $preset = 'dividend_stocks';
        }
        
        $market = $presets[$preset]['market'];
        
        // Get latest results from DB
        $stmt = $this->pdo->prepare("
            SELECT symbol, data, run_at, market
            FROM tradingview_screener_results 
            WHERE preset_name = :preset AND market = :market
            ORDER BY symbol
            LIMIT 100
        ");
        $stmt->execute([':preset' => $preset, ':market' => $market]);
        $results = $stmt->fetchAll();
        
        // Decode JSON data
        foreach ($results as &$r) {
            $r['metrics'] = json_decode($r['data'], true) ?: [];
        }

        // Threshold filter for rating-based presets
        $minScore = isset($_GET['min_score']) ? (float) $_GET['min_score'] : null;
        if ($minScore !== null && $minScore > 0) {
            $results = array_values(array_filter($results, function($r) use ($preset, $minScore) {
                $m = $r['metrics'] ?? [];
                if ($preset === 'exit_risk') {
                    $score = isset($m['composite_exit_risk']) ? ((float)$m['composite_exit_risk']) : null;
                    if ($score === null) return false;
                    // Invert: stored exit risk is 0-1; lower is better.
                    return ((1 - $score) * 100) >= $minScore;
                }
                $score = isset($m['score']) ? (float)$m['score'] : null;
                if ($score === null) return false;
                return $score >= $minScore;
            }));
        }

        // Override name from symbol_master when available
        $symbols = [];
        foreach ($results as $r) {
            $symbols[] = $r['symbol'];
        }
        if ($symbols) {
            $in = implode(',', array_fill(0, count($symbols), '?'));
            $stmt2 = $this->pdo->prepare("SELECT symbol, name FROM symbol_master WHERE symbol IN ($in)");
            $stmt2->execute($symbols);
            $names = [];
            while ($row = $stmt2->fetch(PDO::FETCH_ASSOC)) {
                $names[$row['symbol']] = $row['name'];
            }
            foreach ($results as &$r) {
                $sym = $r['symbol'];
                if (!empty($names[$sym])) {
                    $r['metrics']['name'] = $names[$sym];
                }
            }
            unset($r);
        }
        
        // Client-side sector filter
        if ($sector !== null && $sector !== '') {
            $results = array_values(array_filter($results, function($r) use ($sector) {
                $m = $r['metrics'] ?? [];
                return ($m['sector'] ?? '') === $sector;
            }));
        }
        
        // Client-side sort
        $allowedSort = [
            'symbol' => fn($a,$b)=>strcmp($a['symbol'],$b['symbol']),
            'name' => fn($a,$b)=>strcmp($a['metrics']['name']??'',$b['metrics']['name']??''),
            'close' => fn($a,$b)=>($a['metrics']['close']??0)<=>($b['metrics']['close']??0),
            'change' => fn($a,$b)=>($a['metrics']['change']??0)<=>($b['metrics']['change']??0),
            'Perf.Y' => fn($a,$b)=>($a['metrics']['Perf.Y']??0)<=>($b['metrics']['Perf.Y']??0),
            'dividends_yield_current' => fn($a,$b)=>($a['metrics']['dividends_yield_current']??0)<=>($b['metrics']['dividends_yield_current']??0),
            'price_earnings_ttm' => fn($a,$b)=>($a['metrics']['price_earnings_ttm']??0)<=>($b['metrics']['price_earnings_ttm']??0),
            'return_on_equity' => fn($a,$b)=>($a['metrics']['return_on_equity']??0)<=>($b['metrics']['return_on_equity']??0),
            'gross_margin_ttm' => fn($a,$b)=>($a['metrics']['gross_margin_ttm']??0)<=>($b['metrics']['gross_margin_ttm']??0),
            'sector' => fn($a,$b)=>strcmp($a['metrics']['sector']??'',$b['metrics']['sector']??''),
            'vv_pass_count' => fn($a,$b)=>($b['metrics']['pass_count']??0)<=>($a['metrics']['pass_count']??0),
            'vv_score' => fn($a,$b)=>($b['metrics']['score']??0)<=>($a['metrics']['score']??0),
        ];
        if ($sort !== null && isset($allowedSort[$sort])) {
            usort($results, $allowedSort[$sort]);
        }

        // Build unique sector list for filter dropdown
        $sectors = [];
        foreach ($results as $r) {
            $sec = $r['metrics']['sector'] ?? '';
            if ($sec !== '' && !in_array($sec, $sectors, true)) {
                $sectors[] = $sec;
            }
        }
        sort($sectors);
        
        return [
            'preset_name' => $preset,
            'preset_label' => $presets[$preset]['label'],
            'presets' => $presets,
            'screener_results' => $results,
            'sectors' => $sectors,
            'current_sector' => $sector ?? '',
            'current_sort' => $sort ?? '',
        ];
    }
}
