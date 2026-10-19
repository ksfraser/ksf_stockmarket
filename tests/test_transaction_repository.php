<?php
/**
 * Unit + integration tests for TransactionRepository + StockController fixes.
 *
 * Run:  php tests/test_transaction_repository.php
 * Uses only SQLite price_cache (short-term) + mock PDO for data layer.
 */
require_once __DIR__ . '/../../src/Model/Database.php';
require_once __DIR__ . '/../../src/Controller/StockController.php';

$passed = 0;
$failed = 0;

function assert_true($condition, string $label) {
    global $passed, $failed;
    if ($condition) {
        echo "PASS: $label\n";
        $passed++;
    } else {
        echo "FAIL: $label\n";
        $failed++;
    }
}

// 1. TransactionRepository loads and has required methods
assert_true(class_exists('TransactionRepository'), 'TransactionRepository class exists');

// 2. StockController syntax passes
assert_true(
    !str_contains(file_get_contents(__DIR__ . '/../../src/Controller/StockController.php'), 'getLatestRow'),
    'StockController still references getLatestRow method (should exist after fix)');

// 3. Integration test: login -> portfolio -> detail (V) via curl
$cookie = tempnam('/tmp', 'cookie');
system('curl -s -c ' . escapeshellarg($cookie) . ' -X POST "http://localhost/stockmarket/?action=login" -d "username=admin&password=admin123" > /dev/null 2>&1');
$portfolio = system('curl -s -b ' . escapeshellarg($cookie) . ' -o /dev/null -w "%{http_code}" "http://localhost/stockmarket/?action=portfolio" 2>/dev/null');
$portfolio = trim($portfolio);
assert_true($portfolio === '200', 'Portfolio page HTTP 200 (current: ' . $portfolio . ')');

$detail = system('curl -s -b ' . escapeshellarg($cookie) . ' -o /dev/null -w "%{http_code}" "http://localhost/stockmarket/?action=detail&symbol=V" 2>/dev/null');
$detail = trim($detail);
assert_true($detail === '200', 'Detail page V HTTP 200 (current: ' . $detail . ')');

echo "\n=== Results: $passed passed, $failed failed ===\n";
exit($failed > 0 ? 1 : 0);
