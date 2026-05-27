<?php

declare(strict_types=1);

/**
 * Front Controller
 *
 * All web requests are routed through this file.
 * API requests (/api/*) are proxied to the Python Flask service.
 */

// Project root
define('ROOT_DIR', dirname(__DIR__));

// Load Composer autoloader
require_once ROOT_DIR . '/vendor/autoload.php';

// Bootstrap application
use Ksf\StockMarket\App;

$app = App::getInstance();
$app->bootstrap(ROOT_DIR);

// Simple router
$requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$requestMethod = $_SERVER['REQUEST_METHOD'];

// API routes → Python service
if (str_starts_with($requestUri, '/api/')) {
    forwardToPythonApi($requestUri, $requestMethod);
    exit;
}

// Health check
if ($requestUri === '/health') {
    header('Content-Type: application/json');
    echo json_encode([
        'status' => 'ok',
        'app' => $app->get('APP_NAME', 'KSF Stock Market'),
        'time' => date('c'),
    ]);
    exit;
}

// Default: serve the SPA / main page
// TODO: Route to proper controllers once Phase 2+ is complete
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($app->get('APP_NAME', 'KSF Stock Market')) ?></title>
    <link rel="stylesheet" href="/assets/css/main.css">
</head>
<body>
    <header>
        <h1><?= htmlspecialchars($app->get('APP_NAME', 'KSF Stock Market')) ?></h1>
        <nav>
            <a href="/">Dashboard</a>
            <a href="/portfolio">Portfolio</a>
            <a href="/watchlists">Watchlists</a>
            <a href="/backtest">Backtest</a>
            <a href="/reports">Reports</a>
        </nav>
    </header>

    <main>
        <div class="notice">
            <h2>Modernization in Progress</h2>
            <p>The application is being modernized. PHP 8.1+ with PSR-4 autoloading,
               Python analysis engine, and MariaDB backend.</p>
            <p>Legacy application code still runs in parallel.</p>
        </div>
    </main>

    <footer>
        <p>&copy; <?= date('Y') ?> K.S. Fraser Inc. All rights reserved.</p>
    </footer>
</body>
</html>

<?php

/**
 * Forward API request to the Python Flask service.
 */
function forwardToPythonApi(string $uri, string $method): void
{
    $pythonApiUrl = $_ENV['PYTHON_API_URL'] ?? 'http://127.0.0.1:5000';

    $ch = curl_init();
    $url = rtrim($pythonApiUrl, '/') . $uri;

    curl_setopt_array($ch, [
        CURLOPT_URL => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Accept: application/json',
        ],
    ]);

    // Forward request body for POST/PUT
    if (in_array($method, ['POST', 'PUT', 'PATCH'])) {
        $body = file_get_contents('php://input');
        if ($body) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        }
    }

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    if ($error) {
        http_response_code(502);
        header('Content-Type: application/json');
        echo json_encode([
            'error' => 'Python API unavailable',
            'detail' => $error,
        ]);
        return;
    }

    http_response_code($httpCode);
    header('Content-Type: application/json');
    echo $response;
}
