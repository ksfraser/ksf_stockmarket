<?php
/**
 * Front controller — routes all requests.
 */

// Start session early for auth
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Autoload — PSR-4 style for App namespace
spl_autoload_register(function ($class) {
    // App\ namespace → src/
    if (strpos($class, 'App\\') === 0) {
        $relative = str_replace('App\\', '', $class);
        $file = '/var/www/stockmarket-app/src/' . str_replace('\\', '/', $relative) . '.php';
        if (file_exists($file)) { require_once $file; return; }
    }
    // Legacy controller/model paths
    $paths = [
        '/var/www/stockmarket-app/src/Controller/' . $class . '.php',
        '/var/www/stockmarket-app/src/Model/' . $class . '.php',
    ];
    foreach ($paths as $p) {
        if (file_exists($p)) { require_once $p; return; }
    }
});

// Helpers
require_once '/var/www/stockmarket-app/src/View/helpers.php';

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
    $d = $ctrl->screener($_GET['preset'] ?? 'dividend_stocks');
    $presetLabel = $d['preset_label'] ?? 'Screener';
    $results = $d['screener_results'] ?? [];
    if (empty($results)) {
        echo '<p class="text-muted">No screener results found. Cron job runs daily at 6:30 AM.</p>';
        exit;
    }
    ?>
    <p style="margin-top:12px;font-size:0.85em;color:var(--text3);">
        Showing <?php echo count($results); ?> results for <?php echo htmlspecialchars($presetLabel); ?>.
        <a href="?action=screener&preset=<?php echo urlencode($d['preset_name'] ?? 'dividend_stocks'); ?>" style="color:var(--accent);">Refresh</a>
    </p>
    <div style="overflow-x:auto;">
        <table>
            <thead>
                <tr>
                    <th>Symbol</th><th>Name</th><th class="r">Price</th><th class="r">Change %</th>
                    <th class="r">1Y Perf</th><th class="r">Yield %</th><th class="r">P/E</th>
                    <th class="r">ROE %</th><th class="r">Gross Margin %</th><th>Sector</th>
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
                    <td class="r"><?php echo ($d['preset_name'] ?? '') === 'dividend_stocks' ? number_format($m['dividends_yield_current'] ?? 0, 2) . '%' : '-'; ?></td>
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
        require '/var/www/stockmarket-app/templates/layout.php';
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
    require '/var/www/stockmarket-app/templates/layout.php';
    exit;
}

// Routes requiring authentication (portfolio, transactions, personal data)
$protectedRoutes = ['portfolio', 'transactions', 'detail', 'indicators', 'my_dashboard', 'settings', 'alerts_status', 'upload', 'stop_orders', 'broker_stops', 'admin_settings', 'shared_with_me'];
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
        $data['symbols'] = $ctrl->listSymbols($_GET['search'] ?? '', $_GET['exchange'] ?? '', $_GET['sort'] ?? 'symbol', $_GET['dir'] ?? 'ASC');
        $pageTitle = 'All Symbols';
        $template = 'list';
        break;
    case 'detail':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->detail($_GET['symbol'] ?? ''));
        $pageTitle = htmlspecialchars($_GET['symbol'] ?? '') . ' - Detail';
        $template = 'detail';
        break;
    case 'portfolio':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->portfolio($_GET['account'] ?? 'all'));
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
        require_once '/var/www/stockmarket-app/src/Controller/BrokerStopController.php';
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
        $data = array_merge($data, $ctrl->listSymbols($_GET['filter'] ?? 'all', $_GET['search'] ?? ''));
        $data = array_merge($data, ['watchlistSymbols' => $ctrl->listWatchlistSymbols()]);
        $pageTitle = 'Symbol Admin';
        $template = 'admin_symbols';
        break;
    case 'admin_settings':
        require_once '/var/www/stockmarket-app/src/Controller/AdminSettingsController.php';
        $ctrl = new AdminSettingsController();
        $data = array_merge($data, $ctrl->index());
        $pageTitle = 'Admin Settings';
        $template = 'admin_settings';
        break;
    case 'indicators':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->detail($_GET['symbol'] ?? ''));
        $pageTitle = htmlspecialchars($_GET['symbol'] ?? '') . ' - Indicators';
        $template = 'indicators';
        break;
    case 'transactions':
        require_once '/var/www/stockmarket-app/src/Controller/TransactionController.php';
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
    case 'screener':
        $ctrl = new StockController();
        $data = array_merge($data, $ctrl->screener($_GET['preset'] ?? 'dividend_stocks'));
        $pageTitle = 'Stock Screener - TradingView';
        $template = 'screener';
        break;
    case 'upload':
        require_once '/var/www/stockmarket-app/src/Controller/DocumentUploadController.php';
        $ctrl = new DocumentUploadController();
        $data = array_merge($data, $ctrl->handle());
        $pageTitle = $data['pageTitle'] ?? 'Upload Documents';
        $template = $data['template'] ?? 'upload';
        break;
    case 'export':
        require_once '/var/www/stockmarket-app/src/Controller/ExportController.php';
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
        require_once '/var/www/stockmarket-app/src/Controller/AlertsController.php';
        $ctrl = new AlertsController();
        $data = array_merge($data, $ctrl->index());
        $pageTitle = 'Alerts & Cron Status';
        $template = 'alerts_status';
        break;
    case 'stablecoin':
        require_once '/var/www/stockmarket-app/src/Service/StablecoinYieldTracker.php';
        $tracker = new StablecoinYieldTracker();
        $data['positions'] = $tracker->getPositions($userId ?? 1);
        $pageTitle = 'Stablecoin Yields';
        $template = 'stablecoin';
        break;
    case 'forex':
        require_once '/var/www/stockmarket-app/src/Service/ForexTracker.php';
        $tracker = new ForexTracker();
        $data['pairs'] = $tracker->getForexPairs();
        $pageTitle = 'Forex';
        $template = 'forex';
        break;
    case 'futures':
        require_once '/var/www/stockmarket-app/src/Service/FuturesTracker.php';
        $tracker = new FuturesTracker();
        $data['futures'] = $tracker->getFuturesSymbols();
        $pageTitle = 'Futures';
        $template = 'futures';
        break;
    case 'risk':
        require_once '/var/www/stockmarket-app/src/Controller/RiskController.php';
        $ctrl = new RiskController();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $data['gate_result'] = $ctrl->preTradeGate($_POST);
        } else {
            $data['audit'] = $ctrl->portfolioAudit($userId ?? 1);
        }
        $pageTitle = 'Risk Manager';
        $template = 'risk';
        break;
    case 'seg_funds':
        require_once '/var/www/html/stockmarket/src/Controller/SegFundsController.php';
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
        require_once '/var/www/html/stockmarket/src/Controller/SegFundsController.php';
        $ctrl = new SegFundsController();
        $data = array_merge($data, $ctrl->detail((int)($_GET['id'] ?? 0)));
        $pageTitle = 'Fund Detail';
        $template = 'seg_fund_detail';
        break;
    case 'shared_with_me':
        if (!$userId) {
            header('Location: ?action=login');
            exit;
        }
        require_once '/var/www/stockmarket-app/src/Controller/SharedWithMeController.php';
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

require '/var/www/stockmarket-app/templates/layout.php';
