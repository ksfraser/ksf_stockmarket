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
     * GET /?action=detail&symbol=XXX — Enhanced single symbol detail page.
     */
    public function detail(string $symbol): array {
        $symbol = strtoupper(trim($symbol));

        // Latest price info - try .TO suffix for Canadian symbols
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
            // Try alternate symbol format
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
            // Use alternate symbol for subsequent queries
            if ($latest) $symbol = $altSym;
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
        // Only try alternate suffix if symbol doesn't already have it
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
        
        // If no fundamentals, try .TO suffix for Canadian symbols (only if symbol doesn't already have it)
        if (!$fundamentals && preg_match('/^[A-Z]/', $symbol) && !str_ends_with($symbol, '.TO')) {
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

        return compact(
            'symbol', 'latest', 'history', 'indicators', 'indHistory',
            'fundamentals', 'portfolio', 'dividendSafety', 'dividends',
            'analystRatings', 'analystTargets', 'news', 'optionsData',
            'buffettScore', 'perf'
        );
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
            
            // If no match, try .TO suffix for Canadian symbols (only if symbol doesn't already have it)
            if (empty($result) && preg_match('/^[A-Z]/', $symbol) && !str_ends_with($symbol, '.TO')) {
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

            // Annualized P&L (years held) — only calculate for positions held 30+ days
            $entryDate = $h['entry_date'] ?? null;
            if ($entryDate) {
                $daysHeld = (new DateTime())->diff(new DateTime($entryDate))->days;
                $yearsHeld = $daysHeld / 365.25;
                // Only annualize if held 30+ days to avoid explosion with tiny time periods
                $annualizedPnlPct = $daysHeld >= 30 ? ((pow($currentValue / $costTotal, 1 / $yearsHeld)) - 1) * 100 : null;
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
        // (approximate: use average holding period, only if 30+ day average)
        $totalDays = 0;
        $count = 0;
        foreach ($holdings as $h) {  // not &$h, we don't modify here
            if ($h['days_held'] >= 30) {
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
        
        // If no match, try .TO suffix for Canadian symbols (only if symbol doesn't already have it)
        if (!$row && preg_match('/^[A-Z]/', $symbol) && !str_ends_with($symbol, '.TO')) {
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
                'market_value' => $h['shares'] * $currentPrice,
                'trailing_stop_pct' => $trailingStopPct,
                'trailing_stop_price' => $trailingStopPrice,
                'stop_loss_pct' => $stopLossPct,
                'stop_loss_price' => $stopLossPrice,
                'atr_14' => $atr14,
                'atr_multiplier' => $atrMultiplier,
                'atr_stop_price' => $atrStopPrice,
                'effective_stop_price' => $effectiveStopPrice,
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
     * POST /?action=refresh_prices — Trigger price data refresh from yfinance.
     * Can refresh all symbols or specific ones via ?symbol=XXX&days=N query params.
     */
    public function refreshPrices(string $symbol = '', int $days = 5): array {
        $symbols = [];
        
        if ($symbol) {
            // Refresh specific symbol
            $symbols = [strtoupper(trim($symbol))];
        } else {
            // Get all active symbols from symbol_master
            $stmt = $this->pdo->query("SELECT symbol FROM symbol_master WHERE is_active = 1 OR is_active IS NULL");
            $symbols = array_column($stmt->fetchAll(), 'symbol');
            
            // Also get symbols currently in portfolio
            $stmt = $this->pdo->query("SELECT DISTINCT symbol FROM portfolio");
            $portfolioSymbols = array_column($stmt->fetchAll(), 'symbol');
            $symbols = array_unique(array_merge($symbols, $portfolioSymbols));
        }
        
        $refreshed = [];
        $errors = [];
        
        foreach ($symbols as $sym) {
            $yfSym = $this->normalizeSymbolForYfinance($sym);
            $result = $this->fetchPriceFromYfinance($sym, $yfSym, $days);
            if ($result['success']) {
                $refreshed[] = $sym;
            } else {
                $errors[] = $sym . ($result['error'] ? ': ' . $result['error'] : '');
            }
        }
        
        return [
            'success' => true,
            'refreshed_count' => count($refreshed),
            'refreshed_symbols' => $refreshed,
            'errors' => $errors,
            'message' => count($refreshed) . " symbols refreshed. " . count($errors) . " errors.",
        ];
    }
    
    /**
     * Normalize symbol for yfinance lookup (add .TO for TSX stocks).
     */
    private function normalizeSymbolForYfinance(string $symbol): string {
        if (strpos($symbol, '.') !== false) return $symbol;
        $nonTsx = ['CEF', 'RGLD', 'BPF.UN', 'SRV.UN', 'KEG.UN', 'IEV', 'SPEU', 'UL', 'PZA', 'RUS', 'CDZ', 'FEZ'];
        return in_array($symbol, $nonTsx) ? $symbol : $symbol . '.TO';
    }
    
    /**
     * Fetch price data for a single symbol from yfinance and update DB.
     */
    private function fetchPriceFromYfinance(string $symbol, string $yfSymbol, int $days = 5): array {
        $script = '/home/ksf_stockmarket/ksf_stockmarket/python/daily_pipeline.py';
        if (!file_exists($script)) {
            return ['success' => false, 'error' => 'Fetch script not found'];
        }
        
        // Use daily_pipeline.py with MariaDB backend
        $cmd = sprintf(
            'DB_BACKEND=mysql /usr/bin/python3 %s --mode daily 2>&1',
            escapeshellarg($script)
        );
        
        $output = shell_exec($cmd);
        
        if (strpos($output, 'new price rows') !== false || strpos($output, 'fetched') !== false) {
            return ['success' => true, 'output' => $output];
        }
        
        return ['success' => false, 'error' => 'No data returned', 'output' => $output];
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
                   latest.close as current_price
            FROM portfolio p
            LEFT JOIN (
                SELECT sp1.symbol, sp1.close
                FROM stockprices sp1
                INNER JOIN (SELECT symbol, MAX(price_date) as max_date FROM stockprices GROUP BY symbol) sp2 ON sp1.symbol = sp2.symbol AND sp1.price_date = sp2.max_date
            ) latest ON p.symbol = latest.symbol
            {$accountWhere}
            GROUP BY p.symbol
            HAVING SUM(p.shares) > 0
            ORDER BY p.symbol
        ");
        return $stmt->fetchAll();
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
     * Calculate exit signal risk score based on InvestorsObserver 18 warning signs.
     * Higher score = higher risk = more reasons to sell.
     */
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
}
