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
            $where[] = "(sp.symbol LIKE :search1 OR sm.name LIKE :search2)";
            $params[':search1'] = '%' . $search . '%';
            $params[':search2'] = '%' . $search . '%';
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
        $optionsData = $opts[0] ?: [];

        // Buffett quality score (pass close price since it's in stockprices, not indicators)
        $closePrice = $latest['close'] ?? 0;
        $buffettScore = $this->calcBuffettScore($fundamentals, $indicators, $closePrice);

        // Performance
        $perf = $this->calcPerformance($symbol);
        
        // Markov regime analysis
        $regime = $this->getRegimeAnalysis($symbol);

        return compact(
            'symbol', 'latest', 'history', 'indicators', 'indHistory',
            'fundamentals', 'portfolio', 'dividendSafety', 'dividends',
            'analystRatings', 'analystTargets', 'news', 'optionsData',
            'buffettScore', 'perf', 'regime'
        );
        // Ensure template gets both naming conventions
        $result = compact(
            'symbol', 'latest', 'history', 'indicators', 'indHistory',
            'fundamentals', 'portfolio', 'dividendSafety', 'dividends',
            'analystRatings', 'analystTargets', 'news', 'optionsData',
            'buffettScore', 'perf'
        );
        $result['analyst_targets'] = $result['analystTargets'];
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
     * GET /?action=portfolio — Portfolio holdings.
     */
    public function portfolio(string $account_filter = 'all'): array {
        // Build account filter
        $where = '';
        if ($account_filter !== 'all') {
            $where = "WHERE p.account_type = " . $this->pdo->quote($account_filter);
        }

        // Aggregate across accounts: each symbol appears once with total shares & weighted cost basis
        $accountJoin = '';
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
            ) latest ON p.symbol = latest.symbol
            {$accountWhere}
            GROUP BY p.symbol
            ORDER BY p.symbol
        ");
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
