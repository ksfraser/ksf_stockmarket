<?php
/**
 * Bulk fix analyst_targets current_price duplication bug.
 * Uses single UPDATE with subquery for performance.
 */
require_once __DIR__ . '/../vendor/autoload.php';
require_once __DIR__ . '/../src/App.php';

$APP_ROOT = dirname(__DIR__);
use Ksf\StockMarket\App;
App::getInstance()->bootstrap($APP_ROOT);

$content = file_get_contents($APP_ROOT . '/.env');
$lines = explode("\n", $content);
foreach ($lines as $line) {
    $line = trim($line);
    if (strpos($line, '#') === 0 || $line === '') continue;
    $parts = explode('=', $line, 2);
    if (count($parts) === 2) putenv($parts[0] . '=' . $parts[1]);
}

use Ksf\StockMarket\Model\Database;
$pdo = Database::get();

echo "=== Bulk Fix: analyst_targets price equality ===\n";
$stmt = $pdo->query("SELECT COUNT(*) FROM analyst_targets WHERE target_price = current_price");
$broken = $stmt->fetchColumn();
echo "Rows broken (target == current): $broken\n";

// Batch update: process in batches of 100 to avoid lock timeouts.
$stmt = $pdo->query("SELECT DISTINCT ticker FROM analyst_targets WHERE current_price = target_price LIMIT 100");
$batch = $stmt->fetchAll(PDO::FETCH_COLUMN);
$fixed = 0;

foreach ($batch as $ticker) {
    $realPriceStmt = $pdo->prepare("SELECT close FROM stockprices WHERE symbol = :t ORDER BY price_date DESC LIMIT 1");
    $realPriceStmt->execute(['t' => $ticker]);
    $realRow = $realPriceStmt->fetch();
    if ($realRow && $realRow['close'] !== null) {
        $update = $pdo->prepare("UPDATE analyst_targets SET current_price = :c WHERE ticker = :t AND current_price = target_price");
        $update->execute(['c' => $realRow['close'], 't' => $ticker]);
        $fixed += $update->rowCount();
    }
}

echo "Batch updated: $fixed rows (batch size: " . count($batch) . ")\n";
echo "Rows updated: $fixed\n";

$stmt2 = $pdo->query("SELECT COUNT(*) FROM analyst_targets WHERE target_price = current_price");
$remaining = $stmt2->fetchColumn();
echo "Rows remaining broken: $remaining\n";
