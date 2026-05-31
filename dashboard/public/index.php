<?php
/**
 * Front controller — routes all requests.
 */

require_once __DIR__ . '/../src/View/helpers.php';

// Autoload
spl_autoload_register(function ($class) {
    $paths = [
        __DIR__ . '/../src/Controller/' . $class . '.php',
        __DIR__ . '/../src/Model/' . $class . '.php',
    ];
    foreach ($paths as $p) {
        if (file_exists($p)) { require_once $p; return; }
    }
});

// Database config
if (!file_exists(__DIR__ . '/../config/database.php')) {
    // Write default config
    @mkdir(__DIR__ . '/../config', 0755, true);
    file_put_contents(__DIR__ . '/../config/database.php', '<?php
return [
    "host" => "ksfraser.ca",
    "database" => "ksfraser_stock_market",
    "username" => "ksfraser_stockmarket",
    "password" => "Zaqwsx9sm1@",
    "charset" => "utf8mb4",
];');
}

$action = $_GET['action'] ?? 'overview';

// JSON API endpoints
if ($action === 'api_chart' && isset($_GET['symbol'])) {
    header('Content-Type: application/json');
    $ctrl = new StockController();
    echo json_encode($ctrl->chartData($_GET['symbol'], (int)($_GET['days'] ?? 250)));
    exit;
}

// For HTML pages, route to controller
$pageTitle = 'Dashboard';
$template = 'overview';
$data = [];

switch ($action) {
    case 'overview':
        $ctrl = new DashboardController();
        $data = $ctrl->overview();
        $pageTitle = 'Dashboard';
        $template = 'overview';
        break;

    case 'list':
        $ctrl = new StockController();
        $data['symbols'] = $ctrl->listSymbols(
            $_GET['search'] ?? '',
            $_GET['exchange'] ?? '',
            $_GET['sort'] ?? 'symbol',
            $_GET['dir'] ?? 'ASC'
        );
        $pageTitle = 'All Symbols';
        $template = 'list';
        break;

    case 'detail':
        $ctrl = new StockController();
        $data = $ctrl->detail($_GET['symbol'] ?? '');
        $pageTitle = ($data['symbol'] ?? 'Unknown') . ' - Detail';
        $template = 'detail';
        break;

    case 'portfolio':
        $ctrl = new StockController();
        $data = $ctrl->portfolio();
        $pageTitle = 'Portfolio';
        $template = 'portfolio';
        break;

    case 'indicators':
        $ctrl = new StockController();
        $data = $ctrl->detail($_GET['symbol'] ?? '');
        $pageTitle = ($data['symbol'] ?? 'Unknown') . ' - Indicators';
        $template = 'indicators';
        break;

    default:
        $ctrl = new DashboardController();
        $data = $ctrl->overview();
        $template = 'overview';
}

// Render
require __DIR__ . '/../templates/layout.php';
