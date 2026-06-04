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
$protectedRoutes = ['portfolio', 'transactions', 'detail', 'indicators', 'my_dashboard', 'settings', 'alerts_status', 'upload'];
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
        $data = array_merge($data, $ctrl->listSymbols($_GET['filter'] ?? 'all', $_GET['search'] ?? ''));
        $pageTitle = 'Symbol Admin';
        $template = 'admin_symbols';
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
    default:
        $ctrl = new DashboardController();
        $data = array_merge($data, $ctrl->overview());
        $template = 'overview';
}

require '/var/www/stockmarket-app/templates/layout.php';
