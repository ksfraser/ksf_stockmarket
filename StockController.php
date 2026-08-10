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

        // Latest price info
        $stmt = $this->pdo->prepare("
            SELECT sp.*, sm.name, sm.exchange, sm.sector, sm.industry
            FROM stockprices sp
            LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
            WHERE sp.symbol = :sym
            ORDER BY sp.price_date DESC LIMIT 1
        ");
        $stmt->execute([':sym' => $symbol]);
        $latest = $stmt->fetch();

        // If no price, try .TO suffix for Canadian symbols
        if (!$latest && preg_match('/^[A-Z]/', $symbol)) {
            $altSym = $symbol . '.TO';
            $stmt = $this->pdo->prepare("
                SELECT sp.*, sm.name, sm.exchange, sm.sector, sm.industry
                FROM stockprices sp
                LEFT JOIN symbol_master sm ON sp.symbol = sm.symbol
                WHERE sp.symbol = :sym
                ORDER BY sp.price_date DESC LIMIT 1
            ");
            $stmt->execute([':sym' => $altSym]);
            $latest = $stmt->fetch();
            if ($latest) {
                $symbol = $altSym;
            }
        }

        if (!$latest) {
            return ['error' => 'Symbol not found', 'symbol' => $symbol];
        }

        // Previous close
        $stmt = $this->pdo->prepare("SELECT close FROM stockprices WHERE symbol = :sym AND price_date < :d ORDER BY price_date DESC LIMIT 1");
        $stmt->execute([':sym' => $symbol, ':d' => $latest['price_date']]);
        $latest['prev_close'] = $stmt->fetchColumn();

        // 250 days history
        $stmt = $this->pdo->prepare("SELECT price_date, open, high, low, close, volume FROM stockprices WHERE symbol = :sym ORDER BY price_date DESC LIMIT 250");
        $stmt->execute([':sym' => $symbol]);
        $history = array_reverse($stmt->fetchAll());

        // Indicators: latest + 60 days for charts — check both symbol formats
        $indHistory = [];
        $indicators = [];

        // Check if this is a TSX symbol (has .TO variant) and which has more data
        $hasTO = str_ends_with($symbol, '.TO');
        $baseSym = $hasTO ? substr($symbol, 0, -3) : $symbol;
        $altSym = $hasTO ? null : $symbol . '.TO';

        $stmt = $this->pdo->prepare("SELECT COUNT(*) FROM indicators_json WHERE symbol = :sym");
        $stmt->execute([':sym' => $symbol]);
        $mainCount = $stmt->fetchColumn();

        $altCount = 0;
        if ($altSym) {
            $stmt = $this->pdo->prepare("SELECT COUNT(*) FROM indicators_json WHERE symbol = :sym");
            $stmt->execute([':sym' => $altSym]);
            $altCount = $stmt->fetchColumn();
        }

        // Prefer the format with more data
        $preferredSym = ($altCount > $mainCount && $altSym) ? $altSym : $symbol;

        $indSql = "SELECT price_date, data FROM indicators_json WHERE symbol = :sym ORDER BY price_date DESC LIMIT 60";
        $stmt = $this->pdo->prepare($indSql);
        $stmt->execute([':sym' => $preferredSym]);
        $indRows = array_reverse($stmt->fetchAll());

        // Update symbol for consistency (use the format we're querying)
        $symbol = $preferredSym;

        foreach ($indRows as $i => $row) {
            $d = json_decode($row['data'], true);
            $d['price_date'] = $row['price_date'];
            $indHistory[] = $d;
        }
        if ($indHistory) $indicators = end($indHistory);

        // Fundamentals — try alternate symbol formats (.TO for Canadian stocks)
        $fundamentals = [];
        $stmt = $this->pdo->prepare("SELECT * FROM fundamentals WHERE symbol = :sym ORDER BY fetch_date DESC LIMIT 1");
        $stmt->execute([':sym' => $symbol]);
        $fundamentals = $stmt->fetch() ?: [];
        
        // If no fundamentals, try .TO suffix for Canadian symbols
        if (!$fundamentals && (substr($symbol, 0, 1) >= 'A' && substr($symbol, 0, 1) <= 'Z')) {
            $stmt = $this->pdo->prepare("SELECT * FROM fundamentals WHERE symbol = :sym ORDER BY fetch_date DESC LIMIT 1");
            $stmt->execute([':sym' => $symbol . '.TO']);
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

        // News
        $news = $this->getTableData('symbol_news', $symbol, 'date DESC', 10);

        // Options snapshot
        $opts = $this->getTableData('options_snapshot', $symbol, 'fetch_date DESC', 1);
        $optionsData = $opts[0] ?? [];

        // Buffett quality score (pass close price since it's in stockprices, not indicators)
        $closePrice = $latest['close'] ?? 0;
        $buffettScore = $this->calcBuffettScore($fundamentals, $indicators, $closePrice);

        // Performance
        $perf = $this->calcPerformance($symbol);
        
        // Exit signal risk assessment (InvestorsObserver 18 warning signs)
        $exitSignals = $this->calcExitSignals($fundamentals, $indicators, $closePrice);

        // Markov regime analysis
        $regime = $this->getRegimeAnalysis($symbol);

        // Ensure template gets both naming conventions (snake_case for template, camelCase for JS)
        $result = compact(
            'symbol', 'latest', 'history', 'indicators', 'indHistory',
            'fundamentals', 'portfolio', 'dividendSafety', 'dividends',
            'analystRatings', 'analystTargets', 'news', 'optionsData',
            'buffettScore', 'perf', 'regime', 'exitSignals'
        );
        // Alias keys for template (expects snake_case)
        $result['dividend_safety'] = $result['dividendSafety'] ?? [];
        $result['analyst_targets'] = $result['analystTargets'] ?? [];
        $result['options'] = $result['optionsData'] ?? [];
        $result['exit_signals'] = $result['exitSignals'] ?? [];
        return $result;
    }

    /**
     * Helper: get rows from a table (graceful if table doesn't exist).
     * Tries .TO suffix for Canadian symbols if no direct match.
     */
    private function getTableData(string $table, string $symbol, string $order = 'date DESC', int $limit = 10): array {
        try {
            $sql = "SELECT * FROM {$table} WHERE symbol = :sym ORDER BY {$order} LIMIT :lim";
            $stmt = $this->pdo->prepare($sql);
            $stmt->bindValue(':sym', $symbol);
            $stmt->bindValue(':lim', $limit, PDO::PARAM_INT);
            $stmt->execute();
            $result = $stmt->fetchAll();
            
            // If no match, try .TO suffix for Canadian symbols
            if (empty($result) && preg_match('/^[A-Z]/', $symbol)) {
                $stmt = $this->pdo->prepare($sql);
                $stmt->bindValue(':sym', $symbol . '.TO');
                $stmt->bindValue(':lim', $limit, PDO::PARAM_INT);
                $stmt->execute();
                $result = $stmt->fetchAll();
            }
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
     * Calculate exit signal risk score based on InvestorsObserver 18 warning signs.
     * Higher score = higher risk = more reasons to sell.
     */
    private function calcExitSignals(array $f, array $ind, float $closePrice = 0): array {
        if (!$closePrice || $closePrice <= 0) {
            return ['composite_exit_risk' => 0.5, 'insufficient_data' => true];
        }
        
        $signals = [];
        $weights = [];
        $cfg = $this->getExitSignalConfig();
        
        // 1. Technical: Trailing stop breach (ATR-based)
        if (!empty($ind['atr_14']) && !empty($ind['high_60'])) {
            $atrMult = $cfg['trailing_stop_atr_mult_core'] ?? 3.0;
            $highestHigh = $ind['high_60']; // current day's 60-day highest high
            $trailingStop = $highestHigh - ($atrMult * $ind['atr_14']);
            $signals['trailing_stop_breach'] = ($closePrice < $trailingStop) ? 1.0 : 0.0;
            $weights['trailing_stop_breach'] = 0.20;
        }
        
        // 2. Technical: RSI overbought
        if (!empty($ind['rsi_14'])) {
            $rsiExit = $cfg['rsi_exit_above'] ?? 65;
            $signals['rsi_overbought'] = ($ind['rsi_14'] > $rsiExit) ? 1.0 : 0.0;
            $weights['rsi_overbought'] = 0.10;
        }
        
        // 3. Technical: Price vs 200d MA breakdown
        if (!empty($ind['sma_200']) && $ind['sma_200'] > 0) {
            $ma200Threshold = $cfg['price_vs_ma200_exit_below'] ?? 0.95;
            $vsMA200 = $closePrice / $ind['sma_200'];
            $signals['ma200_breakdown'] = ($vsMA200 < $ma200Threshold) ? 1.0 : 0.0;
            $weights['ma200_breakdown'] = 0.15;
        }
        
        // 4. Technical: Bollinger Band upper touch
        if (!empty($ind['bb_20_2_0_upper']) && !empty($ind['bb_20_2_0_lower'])) {
            $bbUpper = $ind['bb_20_2_0_upper'];
            $bbLower = $ind['bb_20_2_0_lower'];
            $bbMid = ($bbUpper + $bbLower) / 2;
            $bbPosition = ($bbUpper != $bbLower) ? ($closePrice - $bbLower) / ($bbUpper - $bbLower) : 0.5;
            $signals['bb_upper_touch'] = ($bbPosition > 0.95) ? 1.0 : 0.0;
            $weights['bb_upper_touch'] = 0.10;
        }
        
        // 5. Fundamental: ROE deterioration
        $roeThreshold = $cfg['exit_on_roe_drop_below'] ?? 0.10;
        if (!empty($f['roe'])) {
            $signals['roe_deterioration'] = ($f['roe'] < $roeThreshold) ? 1.0 : 0.0;
            $weights['roe_deterioration'] = 0.10;
        }
        
        // 6. Fundamental: Debt/Equity rise
        $deThreshold = $cfg['exit_on_debt_equity_above'] ?? 0.60;
        if (!empty($f['debt_to_equity'])) {
            $signals['debt_equity_rise'] = ($f['debt_to_equity'] > $deThreshold) ? 1.0 : 0.0;
            $weights['debt_equity_rise'] = 0.10;
        }
        
        // 7. Fundamental: FCF negative
        if (($cfg['exit_on_fcf_negative'] ?? true) && isset($f['free_cash_flow'])) {
            $signals['fcf_negative'] = ($f['free_cash_flow'] < 0) ? 1.0 : 0.0;
            $weights['fcf_negative'] = 0.10;
        }
        
        // 8. Fundamental: Earnings drop > 20%
        $epsDropThreshold = $cfg['exit_if_earnings_drop_pct'] ?? 0.20;
        if (!empty($f['eps_quarterly']) && is_array($f['eps_quarterly']) && count($f['eps_quarterly']) >= 2) {
            $epsQ = $f['eps_quarterly'];
            $epsDrop = ($epsQ[0] - $epsQ[1]) / abs($epsQ[0]);
            $signals['earnings_drop'] = ($epsDrop > $epsDropThreshold) ? 1.0 : 0.0;
            $weights['earnings_drop'] = 0.10;
        }
        
        // 9. Fundamental: Dividend cut
        if (($cfg['exit_on_dividend_cut'] ?? true) && !empty($f['dividend_history']) && is_array($f['dividend_history']) && count($f['dividend_history']) >= 2) {
            $divHist = $f['dividend_history'];
            $divCut = ($divHist[0] < $divHist[1]) ? 1.0 : 0.0;
            $signals['dividend_cut'] = $divCut;
            $weights['dividend_cut'] = 0.08;
        }
        
        // 10. Valuation: Yield on cost too low
        $yocThreshold = $cfg['min_yield_on_cost_exit'] ?? 0.015;
        if (!empty($f['yield_on_cost'])) {
            $signals['yield_on_cost_low'] = ($f['yield_on_cost'] < $yocThreshold) ? 1.0 : 0.0;
            $weights['yield_on_cost_low'] = 0.05;
        }
        
        // 11. Valuation: P/E extreme
        $maxPe = $cfg['max_pe_core'] ?? 25.0;
        if (!empty($f['trailing_pe'])) {
            $signals['pe_extreme'] = ($f['trailing_pe'] > $maxPe) ? 1.0 : 0.0;
            $weights['pe_extreme'] = 0.08;
        }
        
        // 12. Insider selling (placeholder - would need insider_trades table query)
        if (($cfg['exit_on_insider_selling_pct'] ?? 0.50) > 0) {
            $insiderSellRatio = $this->getInsiderSellRatio($f['symbol'] ?? '');
            if ($insiderSellRatio !== null) {
                $signals['insider_selling'] = ($insiderSellRatio > 0.50) ? 1.0 : 0.0;
                $weights['insider_selling'] = 0.08;
            }
        }
        
        // 13. Corporate events (placeholder)
        if ($cfg['flag_corporate_events'] ?? true) {
            $signals['corporate_event_risk'] = 0.0; // would query corporate_events table
            $weights['corporate_event_risk'] = 0.05;
        }
        
        // 14. Sector relative strength (placeholder - would need sector ETF data)
        $sectorRelThreshold = $cfg['sector_relative_strength_min'] ?? -0.10;
        $signals['sector_underperformance'] = 0.0; // would compare to XIC.TO or sector ETF
        $weights['sector_underperformance'] = 0.08;
        
        // 15. FCF yield too low
        $fcfYieldThreshold = $cfg['min_fcf_yield'] ?? 0.02;
        if (!empty($f['free_cash_flow']) && !empty($f['market_cap'])) {
            $fcfYield = $f['free_cash_flow'] / $f['market_cap'];
            $signals['fcf_yield_low'] = ($fcfYield < $fcfYieldThreshold) ? 1.0 : 0.0;
            $weights['fcf_yield_low'] = 0.05;
        }
        
        // 16. Debt/EBITDA too high
        $deEbitdaThreshold = $cfg['max_debt_to_ebitda'] ?? 4.0;
        if (!empty($f['debt_to_ebitda'])) {
            $signals['debt_ebitda_high'] = ($f['debt_to_ebitda'] > $deEbitdaThreshold) ? 1.0 : 0.0;
            $weights['debt_ebitda_high'] = 0.05;
        }
        
        // Composite exit risk score
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
    
    private function getExitSignalConfig(): array {
        // Load from config.yaml or return defaults
        $cfgPath = __DIR__ . '/../config.yaml';
        if (file_exists($cfgPath)) {
            $config = yaml_parse_file($cfgPath);
            return $config['signals']['exit_signals'] ?? [];
        }
        return [];
    }
    
    private function getInsiderSellRatio(string $symbol): ?float {
        try {
            $stmt = $this->pdo->prepare("
                SELECT 
                    SUM(CASE WHEN transaction_type IN ('S', 'Sale', 'Sell') THEN 1 ELSE 0 END) as sells,
                    COUNT(*) as total
                FROM insider_trades
                WHERE symbol = ? AND filing_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            ");
            $stmt->execute([$symbol]);
            $row = $stmt->fetch();
            if ($row && $row['total'] > 0) {
                return $row['sells'] / $row['total'];
            }
        } catch (Exception $e) {
            // table may not exist or query may fail
        }
        return null;
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
        error_log("PORTFOLIO SQL returned " . count($holdings) . " rows for user_id " . ($user_id ?: 'all'));
        foreach ($holdings as $i => $h) {
            error_log("  row $i: symbol={$h['symbol']} shares={$h['shares']}");
        }

        $fctrl = new FundamentalsController();

        $totalCost = 0;
        $totalValue = 0;
        foreach ($holdings as &$h) {
            error_log("PORTFOLIO loop: symbol={$h['symbol']} shares={$h['shares']}");
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

        error_log("PORTFOLIO after loop: " . count($holdings) . " holdings");
        foreach ($holdings as $i => $h) {
            error_log("  after row $i: symbol={$h['symbol']} shares={$h['shares']}");
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
     * Tries .TO suffix for Canadian symbols if no direct match.
     */
    private function getLatestIndicators(string $symbol): array {
        $stmt = $this->pdo->prepare("
            SELECT data FROM indicators_json
            WHERE symbol = :sym
            ORDER BY price_date DESC LIMIT 1
        ");
        $stmt->execute([':sym' => $symbol]);
        $row = $stmt->fetch();
        
        // If no match, try .TO suffix for Canadian symbols
        if (!$row && preg_match('/^[A-Z]/', $symbol)) {
            $stmt = $this->pdo->prepare("
                SELECT data FROM indicators_json
                WHERE symbol = :sym
                ORDER BY price_date DESC LIMIT 1
            ");
            $stmt->execute([':sym' => $symbol . '.TO']);
            $row = $stmt->fetch();
        }
        
        if (!$row) return [];
        return json_decode($row['data'] ?: $row[0], true) ?: [];
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
    
    /**
     * GET /?action=refresh_price&symbol=SU.TO — Trigger price refresh for one symbol.
     */
    public function refreshPrice(string $symbol): array {
        $symbol = strtoupper(trim($symbol));
        if (!preg_match('/^[A-Z][A-Z0-9\.\-]*$/', $symbol)) {
            $_SESSION['flash_error'] = 'Invalid symbol.';
            header('Location: ?action=overview');
            exit;
        }

        $script = __DIR__ . '/../../../../python/fetch_prices.py';
        if (!file_exists($script)) {
            $_SESSION['flash_error'] = 'Price fetcher not found.';
            header('Location: ?action=detail&symbol=' . urlencode($symbol));
            exit;
        }

        $fullHistory = isset($_GET['full_history']) && $_GET['full_history'] == '1';
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
            $_SESSION['flash_error'] = 'Price refresh error: ' . $e->getMessage();
        }

        header('Location: ?action=detail&symbol=' . urlencode($symbol));
        exit;
    }

    /**
     * GET /?action=screener — Display TradingView screener results.
     */
    public function screener(string $preset = 'dividend_stocks'): array {
        // Available presets with markets
        $presets = [
            'dividend_stocks' => ['label' => 'Dividend Stocks (Yield >3%)', 'market' => 'america'],
            'quality_compounder' => ['label' => 'Quality Compunders', 'market' => 'america'],
            'value_stocks' => ['label' => 'Value Stocks (P/E <15)', 'market' => 'america'],
            'canadian_dividends' => ['label' => 'Canadian Dividends (Yield >3%)', 'market' => 'canada'],
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
        
        return [
            'preset_name' => $preset,
            'preset_label' => $presets[$preset]['label'],
            'presets' => $presets,
            'screener_results' => $results,
        ];
    }
}
