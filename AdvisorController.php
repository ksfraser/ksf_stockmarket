<?php
/**
 * AdvisorController — Risk gate + research brief router for the paper-trading firm.
 *
 * Responsibilities:
 *  1. preTradeGate() — enforce risk_thresholds.json before any trade is placed
 *  2. researchBrief() — serve latest research briefs (internal + external)
 *  3. riskThresholds() — read current thresholds (read-only for agents; Board only)
 */
class AdvisorController {
    private $pdo;
    /** @var SymbolResolver */
    private $resolver;
    /** @var array */
    private $thresholds;

    public function __construct() {
        $this->pdo = Database::get();
        $this->resolver = new SymbolResolver($this->pdo);
        $this->thresholds = $this->loadThresholds();
    }

    /* ======================================================================
     * RISK THRESHOLDS
     * ====================================================================== */

    private function loadThresholds(): array {
        $path = dirname(__DIR__, 2) . '/config/risk_thresholds.json';
        if (!is_file($path)) {
            return [
                'sharpe_minimum' => 1.5,
                'max_drawdown_pct' => 15.0,
                'paper_trading_default' => true,
                'live_trading_requires_board_approval' => true,
                'strategy_gates' => [
                    'min_backtest_months' => 6,
                    'min_paper_trades' => 30,
                    'min_win_rate_pct' => 40.0,
                    'max_position_pct_of_portfolio' => 10.0,
                    'require_atr_confirmation' => true,
                    'require_eval_signal' => true,
                    'min_eval_consensus' => 2,
                ],
            ];
        }
        $json = file_get_contents($path);
        return json_decode($json, true) ?: [];
    }

    /**
     * GET /?action=advisor&view=thresholds
     */
    public function thresholdsView(): array {
        return [
            'pageTitle' => 'Risk Thresholds',
            'template' => 'advisor_thresholds',
            'thresholds' => $this->thresholds,
            'readonly' => true, // Board only via manual edit
        ];
    }

    /* ======================================================================
     * RESEARCH BRIEFS
     * ====================================================================== */

    /**
     * GET /?action=advisor&view=research — latest briefs.
     */
    public function researchBriefView(): array {
        $mode = $_GET['mode'] ?? 'all'; // internal, external, all
        $category = $_GET['category'] ?? 'all';
        $limit = (int)($_GET['limit'] ?? 20);

        $sql = "SELECT * FROM research_briefs WHERE brief_date = :today";
        $params = [':today' => date('Y-m-d')];

        if ($mode !== 'all') {
            $sql .= " AND mode = :mode";
            $params[':mode'] = $mode;
        }
        if ($category !== 'all') {
            $sql .= " AND category = :cat";
            $params[':cat'] = $category;
        }
        $sql .= " ORDER BY created_at DESC LIMIT " . max(1, min(200, $limit));
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        $briefs = $stmt->fetchAll();

        // Decode JSON fields
        foreach ($briefs as &$b) {
            $b['scores'] = json_decode($b['scores'] ?? '[]', true) ?: [];
            $b['raw_data'] = json_decode($b['raw_data'] ?? '[]', true) ?: [];
        }

        return [
            'pageTitle' => 'Research Briefs',
            'template' => 'advisor_research',
            'briefs' => $briefs,
            'mode' => $mode,
            'category' => $category,
        ];
    }

    /* ======================================================================
     * PRE-TRADE GATE
     * ====================================================================== */

    /**
     * POST /?action=advisor&view=gate — JSON API.
     *
     * Expected JSON body:
     *   { symbol, direction, entry_price, stop_price, account_type, strategy_name }
     *
     * Returns:
     *   { verdict: APPROVED|BLOCKED, checks: [...], position_size: float }
     */
    public function preTradeGate(array $post = []): array {
        $symbol = strtoupper(trim($post['symbol'] ?? ''));
        $symbol = $this->resolver->resolve($symbol);
        $direction = strtoupper($post['direction'] ?? 'BUY');
        $entryPrice = (float)($post['entry_price'] ?? 0);
        $stopPrice = isset($post['stop_price']) ? (float)$post['stop_price'] : null;
        $accountType = strtoupper($post['account_type'] ?? 'TFSA');
        $strategy = strtolower(trim($post['strategy_name'] ?? ''));

        $checks = [];

        // 1. Symbol valid
        $stmt = $this->pdo->prepare("SELECT COUNT(*) FROM symbol_master WHERE symbol = :s");
        $stmt->execute([':s' => $symbol]);
        $symbolValid = (int)$stmt->fetchColumn() > 0;
        $checks[] = [
            'name' => 'Symbol valid',
            'result' => $symbolValid ? 'PASS' : 'BLOCK',
            'detail' => $symbolValid ? $symbol : 'Unknown symbol',
        ];

        // 2. Account type allowed
        $allowedAccounts = ['TFSA', 'RRSP', 'MARGIN'];
        $acctAllowed = in_array($accountType, $allowedAccounts, true);
        $checks[] = [
            'name' => 'Account type enabled',
            'result' => $acctAllowed ? 'PASS' : 'BLOCK',
            'detail' => $accountType,
        ];

        // 3. Paper trading default
        $paperDefault = (bool)($this->thresholds['paper_trading_default'] ?? true);
        $liveApproved = !$paperDefault || (bool)($this->thresholds['live_trading_requires_board_approval'] ?? true) === false;
        $checks[] = [
            'name' => 'Trading mode',
            'result' => $paperDefault ? 'PASS (paper)' : ($liveApproved ? 'PASS (live)' : 'BLOCK (live not approved)'),
            'detail' => $paperDefault ? 'Paper trading' : 'Live trading',
        ];

        // 4. Strategy gates
        $gates = $this->thresholds['strategy_gates'] ?? [];
        if ($strategy && $gates) {
            // Check backtest history
            $stmt = $this->pdo->prepare("
                SELECT backtest_months, paper_trades, win_rate_pct, sharpe_ratio, max_drawdown_pct
                FROM strategy_registry
                WHERE name = :name
                LIMIT 1
            ");
            $stmt->execute([':name' => $strategy]);
            $reg = $stmt->fetch();

            if ($reg) {
                $monthsOk = (int)$reg['backtest_months'] >= (int)($gates['min_backtest_months'] ?? 6);
                $checks[] = [
                    'name' => 'Backtest history',
                    'result' => $monthsOk ? 'PASS' : 'BLOCK',
                    'detail' => $reg['backtest_months'] . ' months >= ' . ($gates['min_backtest_months'] ?? 6),
                ];

                $tradesOk = (int)$reg['paper_trades'] >= (int)($gates['min_paper_trades'] ?? 30);
                $checks[] = [
                    'name' => 'Paper trade count',
                    'result' => $tradesOk ? 'PASS' : 'BLOCK',
                    'detail' => $reg['paper_trades'] . ' >= ' . ($gates['min_paper_trades'] ?? 30),
                ];

                $winOk = (float)$reg['win_rate_pct'] >= (float)($gates['min_win_rate_pct'] ?? 40);
                $checks[] = [
                    'name' => 'Win rate',
                    'result' => $winOk ? 'PASS' : 'BLOCK',
                    'detail' => ($reg['win_rate_pct'] ?? 0) . '% >= ' . ($gates['min_win_rate_pct'] ?? 40) . '%',
                ];

                $sharpeOk = (float)$reg['sharpe_ratio'] >= (float)($this->thresholds['sharpe_minimum'] ?? 1.5);
                $checks[] = [
                    'name' => 'Sharpe ratio',
                    'result' => $sharpeOk ? 'PASS' : 'BLOCK',
                    'detail' => ($reg['sharpe_ratio'] ?? 0) . ' >= ' . ($this->thresholds['sharpe_minimum'] ?? 1.5),
                ];

                $ddOk = (float)$reg['max_drawdown_pct'] <= (float)($this->thresholds['max_drawdown_pct'] ?? 15);
                $checks[] = [
                    'name' => 'Max drawdown',
                    'result' => $ddOk ? 'PASS' : 'BLOCK',
                    'detail' => ($reg['max_drawdown_pct'] ?? 0) . '% <= ' . ($this->thresholds['max_drawdown_pct'] ?? 15) . '%',
                ];
            } else {
                $checks[] = [
                    'name' => 'Strategy registered',
                    'result' => 'BLOCK',
                    'detail' => 'Strategy not found in registry',
                ];
            }
        }

        // 5. ATR confirmation
        if (!empty($gates['require_atr_confirmation'])) {
            $stmt = $this->pdo->prepare("
                SELECT atr_multiple, bounce_back_rate, n_drops
                FROM atr_stop_optimization
                WHERE symbol = :s AND recommended = 1
                LIMIT 1
            ");
            $stmt->execute([':s' => $symbol]);
            $atr = $stmt->fetch();
            $atrOk = (bool)$atr;
            $checks[] = [
                'name' => 'ATR confirmation',
                'result' => $atrOk ? 'PASS' : 'WARN',
                'detail' => $atrOk
                    ? "recommended stop={$atr['atr_multiple']}x  bounce-back=" . number_format((float)$atr['bounce_back_rate'] * 100, 1) . "%  (n=" . (int)$atr['n_drops'] . ")"
                    : 'No ATR data',
            ];
        }

        // 6. Evaluation signal
        if (!empty($gates['require_eval_signal'])) {
            $stmt = $this->pdo->prepare("
                SELECT consensus_signal, consensus_strength
                FROM evalsummary
                WHERE symbol = :s
                ORDER BY price_date DESC
                LIMIT 1
            ");
            $stmt->execute([':s' => $symbol]);
            $ev = $stmt->fetch();
            $signalOk = $ev && (int)$ev['consensus_signal'] === ($direction === 'BUY' ? 1 : 2);
            $checks[] = [
                'name' => 'Eval consensus',
                'result' => $signalOk ? 'PASS' : 'WARN',
                'detail' => $ev
                    ? "signal=" . ($ev['consensus_signal'] ?? '?') . " strength=" . ($ev['consensus_strength'] ?? '?')
                    : 'No eval data',
            ];
        }

        // 7. Position size cap
        $maxPositionPct = (float)($gates['max_position_pct_of_portfolio'] ?? 10);
        // Simplified: use entry_price * 100 shares as position value
        $positionValue = $entryPrice * 100;
        $accountBalance = (float)($post['account_balance'] ?? 100000);
        $positionPct = $accountBalance > 0 ? ($positionValue / $accountBalance) * 100 : 0;
        $sizeOk = $positionPct <= $maxPositionPct;
        $checks[] = [
            'name' => 'Position size',
            'result' => $sizeOk ? 'PASS' : 'WARN',
            'detail' => number_format($positionPct, 1) . '% <= ' . $maxPositionPct . '%',
        ];

        // Verdict: any BLOCK => BLOCKED; any WARN => REVIEW; else APPROVED
        $hasBlock = false;
        $hasWarn = false;
        foreach ($checks as $c) {
            if ($c['result'] === 'BLOCK') $hasBlock = true;
            if (str_starts_with($c['result'], 'WARN')) $hasWarn = true;
        }

        if ($hasBlock) {
            $verdict = 'BLOCKED';
            $positionSize = 0;
        } elseif ($hasWarn) {
            $verdict = 'REVIEW';
            $positionSize = $positionValue;
        } else {
            $verdict = 'APPROVED';
            $positionSize = $positionValue;
        }

        return [
            'checks' => $checks,
            'verdict' => $verdict,
            'position_size' => $positionSize,
            'symbol' => $symbol,
            'direction' => $direction,
            'entry_price' => $entryPrice,
            'stop_price' => $stopPrice,
            'account_type' => $accountType,
            'strategy' => $strategy,
            'paper_default' => $paperDefault,
        ];
    }
}
