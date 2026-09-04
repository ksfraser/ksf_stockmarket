<?php
/**
 * Front controller — routes all requests.
 */

// App root: auto-detect for VPS / shared hosting / flat deploy
$APP_ROOT = getenv('APP_ROOT');
if (!$APP_ROOT) {
    if (is_dir(__DIR__ . '/app/src/Controller')) {
        $APP_ROOT = realpath(__DIR__ . '/app');
    } elseif (is_dir(__DIR__ . '/src/Controller')) {
        $APP_ROOT = __DIR__;
    } else {
        $APP_ROOT = '/var/www/stockmarket-app';
    }
}

// Start session early for auth
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Autoload — PSR-4 style for App namespace
spl_autoload_register(function ($class) {
    // App\ namespace → src/
    if (strpos($class, 'App\\') === 0) {
        $relative = str_replace('App\\', '', $class);
        $file = $GLOBALS['APP_ROOT'] . '/src/' . str_replace('\\', '/', $relative) . '.php';
        if (file_exists($file)) { require_once $file; return; }
    }
    // Legacy controller/model/util paths
    $paths = [
        $GLOBALS['APP_ROOT'] . '/src/Controller/' . $class . '.php',
        $GLOBALS['APP_ROOT'] . '/src/Model/' . $class . '.php',
        $GLOBALS['APP_ROOT'] . '/src/Util/' . $class . '.php',
    ];
    foreach ($paths as $p) {
        if (file_exists($p)) { require_once $p; return; }
    }
});

// Helpers
require_once $GLOBALS['APP_ROOT'] . '/src/View/helpers.php';

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');
ini_set('error_log', $GLOBALS['APP_ROOT'] . '/logs/php_errors.log');

$action = $_GET['action'] ?? 'overview';

// Redirect actions with trailing slash to canonical version
if (is_string($action) && str_ends_with($action, '/')) {
    $canonical = rtrim($action, '/');
    $query = $_GET;
    $query['action'] = $canonical;
    $qs = http_build_query($query);
    header('Location: ?' . $qs);
    exit;
}

// Check auth status
$currentUser = AuthController::checkSession();
$userId = $currentUser ? (int) $currentUser['id'] : null;

// JSON API endpoints (public)
if ($action === 'api_chart' && isset($_GET['symbol'])) {
    header('Content-Type: application/json');
    $ctrl = new StockController();
    echo json_encode($ctrl->chartData($_GET['symbol'], (int)($_GET['days'] ?? 250)));
    exit;
}

if ($action === 'api_screener') {
    $ctrl = new StockController();
    $d = $ctrl->screener(
        $_GET['preset'] ?? 'dividend_stocks',
        $_GET['sort'] ?? null,
        $_GET['sector'] ?? null
    );
    $presetLabel = $d['preset_label'] ?? 'Screener';
    $results = $d['screener_results'] ?? [];
    $sectors = $d['sectors'] ?? [];
    $currentSector = $d['current_sector'] ?? '';
    $currentSort = $d['current_sort'] ?? '';
    if (empty($results)) {
        echo '<p class="text-muted">No screener results found. Cron job runs daily at 6:30 AM.</p>';
        exit;
    }
    function apiScreenerSortLink(string $field, string $label, string $preset, string $currentSort, ?string $sector = null): string {
        $url = '?action=screener&preset=' . urlencode($preset) . '&sort=' . urlencode($field);
        if ($sector !== null && $sector !== '') {
            $url .= '&sector=' . urlencode($sector);
        }
        $arrow = '';
        if ($currentSort === $field) {
            $arrow = ' ▲';
        } elseif ($currentSort === $field . '_desc') {
            $arrow = ' ▼';
        }
        return '<a href="' . htmlspecialchars($url) . '" style="color:var(--text);text-decoration:none;">' . htmlspecialchars($label) . $arrow . '</a>';
    }
    ?><select id="screener-sector-temp" style="display:none">
        <option value="">All Sectors</option>
        <?php foreach ($sectors as $sec): ?>
            <option value="<?php echo htmlspecialchars($sec); ?>" <?php echo $currentSector === $sec ? 'selected' : ''; ?>><?php echo htmlspecialchars($sec); ?></option>
        <?php endforeach; ?>
    </select>
    <p style="margin-top:12px;font-size:0.85em;color:var(--text3);">
        Showing <?php echo count($results); ?> results for <?php echo htmlspecialchars($presetLabel); ?>.
        <a href="?action=screener&preset=<?php echo urlencode($d['preset_name'] ?? 'dividend_stocks'); ?>" style="color:var(--accent);">Refresh</a>
    </p>
    <div style="overflow-x:auto;">
        <table>
            <thead>
                <tr>
                    <th><?php echo apiScreenerSortLink('symbol', 'Symbol', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th><?php echo apiScreenerSortLink('name', 'Name', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th class="r"><?php echo apiScreenerSortLink('close', 'Price', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th class="r"><?php echo apiScreenerSortLink('change', 'Change %', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th class="r"><?php echo apiScreenerSortLink('Perf.Y', '1Y Perf', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th class="r"><?php echo apiScreenerSortLink('dividends_yield_current', 'Yield %', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th class="r"><?php echo apiScreenerSortLink('price_earnings_ttm', 'P/E', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th class="r"><?php echo apiScreenerSortLink('return_on_equity', 'ROE %', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th class="r"><?php echo apiScreenerSortLink('gross_margin_ttm', 'Gross Margin %', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                    <th><?php echo apiScreenerSortLink('sector', 'Sector', $d['preset_name'] ?? 'dividend_stocks', $currentSort, $currentSector); ?></th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($results as $r): $m = $r['metrics'] ?? []; ?>
                <tr>
                    <td><a href="?action=detail&symbol=<?php echo urlencode(str_replace(['NASDAQ:','NYSE:','TSE:','TSX:','NEO:'], '', $r['symbol'])); ?>">
                        <?php echo htmlspecialchars($r['symbol']); ?></a></td>
                    <td><?php echo htmlspecialchars($m['name'] ?? ''); ?></td>
                    <td class="r">$<?php echo number_format($m['close'] ?? 0, 2); ?></td>
                    <td class="r" style="color:<?php echo ($m['change'] ?? 0) >= 0 ? 'var(--green)' : 'var(--red)'; ?>">
                        <?php echo number_format($m['change'] ?? 0, 2); ?>
                    </td>
                    <td class="r"><?php echo number_format($m['Perf.Y'] ?? 0, 1); ?>%</td>
                    <td class="r"><?php echo $m['dividends_yield_current'] !== null && $m['dividends_yield_current'] !== '' ? number_format((float)$m['dividends_yield_current'], 2) . '%' : '-'; ?></td>
                    <td class="r"><?php echo number_format($m['price_earnings_ttm'] ?? 0, 1); ?></td>
                    <td class="r"><?php echo number_format($m['return_on_equity'] ?? 0, 1); ?>%</td>
                    <td class="r"><?php echo number_format($m['gross_margin_ttm'] ?? 0, 1); ?>%</td>
                    <td><?php echo htmlspecialchars($m['sector'] ?? ''); ?></td>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
    <?php
    exit;
}

// Auth routes (no login required)
if ($action === 'login') {
    $ctrl = new AuthController();
    $result = $ctrl->login();
    if (is_array($result)) {
        $pageTitle = $result['pageTitle'] ?? 'Login';
        $template = $result['template'] ?? 'login';
        $data = $result;
        require $GLOBALS['APP_ROOT'] . '/templates/layout.php';
    }
    exit;
}

if ($action === 'logout') {
    $ctrl = new AuthController();
    $ctrl->logout();
    exit;
}

if ($action === 'register') {
    $ctrl = new AuthController();
    $result = $ctrl->register();
    $pageTitle = 'Register';
    $template = 'register';
    $data = $result;
    require $GLOBALS['APP_ROOT'] . '/templates/layout.php';
    exit;
}

// Routes requiring authentication (portfolio, transactions, personal data)
$protectedRoutes = ['portfolio', 'transactions', 'detail', 'indicators', 'my_dashboard', 'settings', 'alerts_status', 'upload', 'stop_orders', 'broker_stops', 'admin_settings', 'shared_with_me', 'refresh_price', 'refresh_all_prices'];
if (in_array($action, $protectedRoutes, true) && !AuthController::checkSession()) {
    $_SESSION['redirect_after_login'] = $_SERVER['REQUEST_URI'];
    header('Location: ?action=login');
    exit;
}

// Route to controller
$pageTitle = 'Dashboard';
$template = 'overview';
$data = [];
$data['current_user'] = $currentUser;

switch ($action) {
    case 'overview':
        $ctrl = new DashboardController();
        $data = array_merge($data, $ctrl->overview());
        $pageTitle = 'Dashboard';
        $template = 'overview';
        break;
    case 'my_dashboard':
        $ctrl = new UserController();
        $data = array_merge($data, $ctrl->myDashboard());
        $pageTitle = 'My Dashboard';
        $template = 'my_dashboard';
        break;
    case 'settings':
        $ctrl = new UserController();
        $data = array_merge($data, $ctrl->settings());
        $pageTitle = 'Settings';
        $template = 'settings';
        break;
    case 'list':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->listSymbols($_GET['search'] ?? '', $_GET['exchange'] ?? '', $_GET['sort'] ?? 'symbol', $_GET['dir'] ?? 'ASC', (int)($_GET['page'] ?? 1), (int)($_GET['per_page'] ?? 200)));
        $pageTitle = 'All Symbols';
        $template = 'list';
        break;
    case 'detail':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->detail($_GET['symbol'] ?? ''));
        $pageTitle = htmlspecialchars($_GET['symbol'] ?? '') . ' - Detail';
        $template = 'detail';
        break;
    case 'refresh_price':
        $ctrl = new StockController();
        $sym = $_REQUEST['symbol'] ?? '';
        if ($sym) {
            $data = array_merge($data, $ctrl->refreshPrice($sym));
        } else {
            header('Location: ?action=overview');
            exit;
        }
        // refreshPrice handles its own redirect + exit
        break;
    case 'portfolio':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->portfolio($_GET['account'] ?? 'all', $currentUser['id']));
        $pageTitle = 'Portfolio';
        $template = 'portfolio';
        break;
    case 'stop_orders':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->stopOrders($_GET['account'] ?? 'all'));
        $pageTitle = 'Stop Orders';
        $template = 'stop_orders';
        break;
    case 'broker_stops':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/BrokerStopController.php';
        $ctrl = new BrokerStopController();
        
        // Handle form submissions
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $action = $_POST['action'] ?? '';
            if ($action === 'place') {
                $result = $ctrl->placeStop($_POST);
                $data['message'] = $result['success'] ?? '';
                $data['error'] = $result['error'] ?? '';
            } elseif ($action === 'trigger' && !empty($_POST['stop_id'])) {
                $result = $ctrl->markTriggered((int)$_POST['stop_id']);
                $data['message'] = $result['success'] ?? '';
                $data['error'] = $result['error'] ?? '';
            }
        }
        
        $data = array_merge($data, $ctrl->index($_GET['account'] ?? 'all'));
        $pageTitle = 'Broker Stop Orders';
        $template = 'broker_stops';
        break;
    case 'admin_symbols':
        $ctrl = new SymbolAdminController();
        $subaction = $_GET['subaction'] ?? 'list';
        if ($subaction === 'deactivate' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            $ctrl->setDeactivationReason($_POST['symbol'] ?? '', $_POST['reason'] ?? '');
            header('Location: ?action=admin_symbols&filter=inactive');
            exit;
        }
        if ($subaction === 'reactivate') {
            $ctrl->toggleActive($_GET['symbol'] ?? '');
            header('Location: ?action=admin_symbols');
            exit;
        }
        if ($subaction === 'save_mapping' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            $ctrl->saveExchangeMapping($_POST);
            header('Location: ?action=admin_symbols');
            exit;
        }
        if ($subaction === 'save_symbol' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            $ctrl->saveSymbol($_POST);
            header('Location: ?action=admin_symbols');
            exit;
        }
        if ($subaction === 'run_batch' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            $batch = $ctrl->runBatchCleanup();
            $filterList = $_GET['filter'] ?? 'all';
            if ($batch['status'] === 'started' || $batch['status'] === 'running') {
                $_SESSION['flash_message'] = $batch['message'];
            } elseif ($batch['status'] === 'error') {
                $_SESSION['flash_error'] = $batch['message'];
            }
            header('Location: ?action=admin_symbols&filter=' . urlencode($filterList));
            exit;
        }
        if ($subaction === 'view_batch_log') {
            $data = array_merge($data, ['batch_log' => $ctrl->viewBatchLog()]);
            $pageTitle = 'Batch Cleanup Log';
            $template = 'admin_batch_log';
        }
        if ($subaction === 'add_watchlist' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            $ctrl->addToWatchlist($_POST);
            $_SESSION['flash_message'] = 'Symbol added to watchlist.';
            header('Location: ?action=admin_symbols');
            exit;
        }
        if ($subaction === 'remove_watchlist' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            $ctrl->removeFromWatchlist($_POST['symbol'] ?? '');
            $_SESSION['flash_message'] = 'Symbol removed from watchlist.';
            header('Location: ?action=admin_symbols');
            exit;
        }
        $data = array_merge($data, $ctrl->listSymbols($_GET['filter'] ?? 'all', $_GET['search'] ?? '', (int)($_GET['page'] ?? 1), (int)($_GET['per_page'] ?? 500)));
        $data = array_merge($data, ['watchlistSymbols' => $ctrl->listWatchlistSymbols()]);
        $pageTitle = 'Symbol Admin';
        $template = 'admin_symbols';
        break;
    case 'admin_settings':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/AdminSettingsController.php';
        $ctrl = new AdminSettingsController();
        $data = array_merge($data, $ctrl->index());
        $pageTitle = 'Admin Settings';
        $template = 'admin_settings';
        break;
    case 'admin_setup_wizard':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/AdminSettingsController.php';
        $ctrl = new AdminSettingsController();
        $data = array_merge($data, ['settings' => $ctrl->getSettings(Database::get())]);
        $pageTitle = 'Setup Wizard';
        $template = 'admin_setup_wizard';
        break;
    case 'refresh_all_prices':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/AdminSettingsController.php';
        $ctrl = new AdminSettingsController();
        $data = array_merge($data, $ctrl->refreshAllPrices());
        // refreshAllPrices handles its own redirect + exit
        break;
    case 'indicators':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->detail($_GET['symbol'] ?? ''));
        $pageTitle = htmlspecialchars($_GET['symbol'] ?? '') . ' - Indicators';
        $template = 'indicators';
        break;
    case 'transactions':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/TransactionController.php';
        $ctrl = new TransactionController();

        // Handle delete action - only for manual_entry transactions
        if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'delete') {
            $result = $ctrl->deleteTransaction((int)($_POST['txn_id'] ?? 0), $userId);
            $_SESSION['flash_message'] = $result;
            // Preserve query params on redirect
            $qs = http_build_query(array_filter([
                'account' => $_GET['account'] ?? null,
                'symbol' => $_GET['symbol'] ?? null,
                'type' => $_GET['type'] ?? null,
                'date_from' => $_GET['date_from'] ?? null,
                'date_to' => $_GET['date_to'] ?? null
            ]));
            header('Location: ?action=transactions' . ($qs ? '&' . $qs : ''));
            exit;
        }

        // Handle edit action - for all transactions
        if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'edit') {
            $result = $ctrl->editTransaction($_POST, (int)($_POST['txn_id'] ?? 0), $userId);
            $_SESSION['flash_message'] = $result;
            // Preserve query params on redirect
            $qs = http_build_query(array_filter([
                'account' => $_GET['account'] ?? null,
                'symbol' => $_GET['symbol'] ?? null,
                'type' => $_GET['type'] ?? null,
                'date_from' => $_GET['date_from'] ?? null,
                'date_to' => $_GET['date_to'] ?? null
            ]));
            header('Location: ?action=transactions' . ($qs ? '&' . $qs : ''));
            exit;
        }

        // Handle record action
        if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'record') {
            $result = $ctrl->recordTransaction($_POST, $userId);
            $data['txn_result'] = $result;
            $data['txn_form'] = $_POST;
        }

        $data = array_merge($data, $ctrl->listTransactions(
            $_GET['account'] ?? '',
            $_GET['symbol'] ?? '',
            $_GET['type'] ?? '',
            $_GET['date_from'] ?? '',
            $_GET['date_to'] ?? ''
        ));
        // Validation: compare transactions to holdings
        $data = array_merge($data, $ctrl->validateHoldings());
        $pageTitle = 'Transactions';
        $template = 'transactions';
        break;
    case 'strategy_stock':
        $registry = \App\Strategy\StrategyFactory::create();
        $ctrl = new StrategyController($registry);
        $data = array_merge($data, $ctrl->stockSelection());
        $pageTitle = 'Stock Selection Strategies';
        $template = 'strategy_stock';
        break;
    case 'strategy_money':
        $registry = \App\Strategy\StrategyFactory::create();
        $ctrl = new StrategyController($registry);
        $data = array_merge($data, $ctrl->moneyManagement());
        $pageTitle = 'Money & Risk Management';
        $template = 'strategy_money';
        break;
case 'strategy_timing':
        $registry = \App\Strategy\StrategyFactory::create();
        $ctrl = new StrategyController($registry);
        $data = array_merge($data, $ctrl->timing());
        $pageTitle = 'Timing & Technical Strategies';
        $template = 'strategy_timing';
        break;
    case 'advisor_backtest':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/AdvisorBacktestController.php';
        $ctrl = new AdvisorBacktestController();
        $data = array_merge($data, $ctrl->leaderboard());
        $pageTitle = 'Advisor Backtest Performance';
        $template = 'advisor_backtest';
        break;
    case 'advisor_backtest_trades':
        $runId = (int)($_GET['run_id'] ?? 0);
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/AdvisorBacktestController.php';
        $ctrl = new AdvisorBacktestController();
        $data = array_merge($data, $ctrl->trades($runId));
        $pageTitle = 'Advisor Backtest Trades';
        $template = 'advisor_backtest_trades';
        break;
    case 'manual_ohlcv':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->manualOhlcv());
        $pageTitle = 'Manual OHLCV Import';
        $template = 'manual_ohlcv';
        break;
    case 'screener':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->screener(
            $_GET['preset'] ?? 'dividend_stocks',
            $_GET['sort'] ?? null,
            $_GET['sector'] ?? null
        ));
        $pageTitle = 'Stock Screener - TradingView';
        $template = 'screener';
        break;
    case 'upload':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/DocumentUploadController.php';
        $ctrl = new DocumentUploadController();
        $data = array_merge($data, $ctrl->handle());
        $pageTitle = $data['pageTitle'] ?? 'Upload Documents';
        $template = $data['template'] ?? 'upload';
        break;
    case 'export':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/ExportController.php';
        $ctrl = new ExportController();
        $result = $ctrl->handle();
        // If the controller returned raw OFX data, output it directly
        if (!empty($result['raw_output'])) {
            header('Content-Type: application/x-ofx');
            header('Content-Disposition: attachment; filename="' . $result['filename'] . '"');
            echo $result['ofx_data'];
            exit;
        }
        $data = array_merge($data, $result);
        $pageTitle = $data['pageTitle'] ?? 'Export Transactions';
        $template = $data['template'] ?? 'export';
        break;
    case 'alerts_status':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/AlertsController.php';
        $ctrl = new AlertsController();
        $data = array_merge($data, $ctrl->index());
        $pageTitle = 'Alerts & Cron Status';
        $template = 'alerts_status';
        break;
    case 'stablecoin':
        require_once $GLOBALS['APP_ROOT'] . '/src/Service/StablecoinYieldTracker.php';
        $tracker = new StablecoinYieldTracker();
        $data['positions'] = $tracker->getPositions($userId ?? 1);
        $pageTitle = 'Stablecoin Yields';
        $template = 'stablecoin';
        break;
    case 'forex':
        require_once $GLOBALS['APP_ROOT'] . '/src/Service/ForexTracker.php';
        $tracker = new ForexTracker();
        $data['pairs'] = $tracker->getForexPairs();
        $pageTitle = 'Forex';
        $template = 'forex';
        break;
    case 'futures':
        require_once $GLOBALS['APP_ROOT'] . '/src/Service/FuturesTracker.php';
        $tracker = new FuturesTracker();
        $data['futures'] = $tracker->getFuturesSymbols();
        $pageTitle = 'Futures';
        $template = 'futures';
        break;
    case 'risk':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/RiskController.php';
        $ctrl = new RiskController();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $data['gate_result'] = $ctrl->preTradeGate($_POST);
        } else {
            $data['audit'] = $ctrl->portfolioAudit($userId ?? 1);
        }
        $pageTitle = 'Risk Manager';
        $template = 'risk';
        break;
    case 'advisor':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/AdvisorController.php';
        $ctrl = new AdvisorController();
        $view = $_GET['view'] ?? 'research';
        if ($_SERVER['REQUEST_METHOD'] === 'POST' && $view === 'gate') {
            header('Content-Type: application/json');
            echo json_encode($ctrl->preTradeGate($_POST));
            exit;
        }
        if ($view === 'thresholds') {
            $data = array_merge($data, $ctrl->thresholdsView());
            $pageTitle = $data['pageTitle'];
            $template = $data['template'];
        } elseif ($view === 'research') {
            $data = array_merge($data, $ctrl->researchBriefView());
            $pageTitle = $data['pageTitle'];
            $template = $data['template'];
        } else {
            $data = array_merge($data, $ctrl->researchBriefView());
            $pageTitle = 'Advisor';
            $template = 'advisor_research';
        }
        break;
    case 'external_auth':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/ExternalAuthController.php';
        $ctrl = new ExternalAuthController();
        $view = $_GET['view'] ?? 'authorize';
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $data['message'] = $ctrl->saveApp();
            $pageTitle = 'External Auth';
            $template = 'external_auth_status';
        } elseif ($view === 'callback') {
            $data = array_merge($data, $ctrl->callback());
            $pageTitle = $data['pageTitle'];
            $template = $data['template'];
        } elseif ($view === 'revoke') {
            $ctrl->revoke();
        } else {
            $ctrl->authorize();
        }
        break;
    case 'seg_funds':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/SegFundsController.php';
        $ctrl = new SegFundsController();
        $data = array_merge($data, $ctrl->listFunds(
            $_GET['carrier'] ?? '',
            $_GET['category'] ?? '',
            $_GET['series'] ?? '',
            $_GET['search'] ?? '',
            $_GET['sort'] ?? 'fund_name',
            $_GET['dir'] ?? 'ASC'
        ));
        $pageTitle = 'Segregated Funds';
        $template = 'seg_funds';
        break;
    case 'seg_fund_detail':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/SegFundsController.php';
        $ctrl = new SegFundsController();
        $data = array_merge($data, $ctrl->detail((int)($_GET['id'] ?? 0)));
        $pageTitle = 'Fund Detail';
        $template = 'seg_fund_detail';
        break;
    case 'seg_fund_lira_5y':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/SegFundsController.php';
        $ctrl = new SegFundsController();
        $data = array_merge($data, $ctrl->liraScreener(
            (int)($_GET['age'] ?? 52),
            (float)($_GET['principal'] ?? 200000),
            '5y'
        ));
        if (!empty($_GET['format']) && $_GET['format'] === 'csv') {
            header('Content-Type: text/csv; charset=utf-8');
            header('Content-Disposition: attachment; filename="lira_screener_5y_' . date('Ymd') . '.csv"');
            $out = fopen('php://output', 'w');
            // Per-geography ranked funds
            foreach (['CA' => 'Canadian', 'US' => 'US', 'INTL' => 'International'] as $geo => $label) {
                fputcsv($out, ["=== 5-Year LIRA Screener — {$label} ==="]);
                fputcsv($out, ['Rank', 'Carrier', 'Fund Name', 'Series', 'MER (%)', '5Y Return (%)', 'Max Drawdown (%)', 'Risk-Adj Return', 'Category']);
                foreach (($data['ranked'][$geo] ?? []) as $i => $r) {
                    fputcsv($out, [
                        $i + 1,
                        $r['carrier'] ?? '',
                        $r['fund_name'] ?? '',
                        $r['series_code'] ?? '',
                        $r['mer'] ?? '',
                        $r['ret_horizon'] ?? '',
                        $r['max_drawdown'] ?? '',
                        $r['risk_adj'] ?? '',
                        $r['category_raw'] ?? '',
                    ]);
                }
                fputcsv($out, []);
            }
            // Carrier summary
            fputcsv($out, ["=== Carrier Summary (all 3 geographies) ==="]);
            fputcsv($out, ['Carrier', 'Avg Risk-Adj (5y)', 'Avg MER (%)', 'CA Pick', 'CA 5Y (%)', 'US Pick', 'US 5Y (%)', 'INTL Pick', 'INTL 5Y (%)']);
            foreach ($data['carriers'] ?? [] as $c) {
                fputcsv($out, [
                    $c['carrier'] ?? '',
                    $c['avg_risk_adj'] ?? '',
                    $c['avg_mer'] ?? '',
                    $c['ca']['fund_name'] ?? '',
                    $c['ca']['ret_horizon'] ?? '',
                    $c['us']['fund_name'] ?? '',
                    $c['us']['ret_horizon'] ?? '',
                    $c['intl']['fund_name'] ?? '',
                    $c['intl']['ret_horizon'] ?? '',
                ]);
            }
            fclose($out);
            exit;
        }
        $pageTitle = 'LIRA Screener — 5 Year';
        $template = 'seg_fund_lira_screener_5y';
        break;
    case 'seg_fund_lira':
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/SegFundsController.php';
        $ctrl = new SegFundsController();
        $data = array_merge($data, $ctrl->liraScreener(
            (int)($_GET['age'] ?? 52),
            (float)($_GET['principal'] ?? 200000),
            '10y'
        ));
        $pageTitle = 'LIRA Screener — 10 Year';
        $template = 'seg_fund_lira_screener';
        break;
    case 'shared_with_me':
        if (!$userId) {
            header('Location: ?action=login');
            exit;
        }
        require_once $GLOBALS['APP_ROOT'] . '/src/Controller/SharedWithMeController.php';
        $ctrl = new SharedWithMeController();
        $data = array_merge($data, $ctrl->index());
        $pageTitle = 'Shared with Me';
        $template = 'shared_with_me';
        break;
    default:
        $ctrl = new DashboardController();
        $data = array_merge($data, $ctrl->overview());
        $template = 'overview';
}

require $GLOBALS['APP_ROOT'] . '/templates/layout.php';
