#!/usr/bin/env php
<?php
declare(strict_types=1);

$configFile = __DIR__ . '/config.yaml';
$yaml = file_get_contents($configFile);
$data = [];
$inData = false;
foreach (explode("\n", $yaml) as $line) {
    $trim = trim($line);
    if ($trim === 'data:') { $inData = true; continue; }
    if ($trim === 'vault:' || $trim === '') { $inData = false; continue; }
    if ($inData && preg_match('/^\s+(\w+):\s*"([^"]*)"$/', $trim, $m)) {
        $data[$m[1]] = $m[2];
    }
}
$host = $data['db_host'] ?? 'ksfraser.ca';
$user = $data['db_user'] ?? 'ksfraser_stockmarket';
$pass = getenv('DB_PASS') ?: '';
if (!$pass) { fwrite(STDERR, "DB_PASS empty\n"); exit(1); }

$pdo = new PDO("mysql:host=$host;dbname=ksfraser_stock_market;charset=utf8mb4", $user, $pass, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);

echo "=== Exchange DBs that exist ===\n";
$res = $pdo->query("SHOW DATABASES LIKE 'ksfraser_sm_%'");
$dbs = $res->fetchAll(PDO::FETCH_ASSOC);
if (empty($dbs)) { echo "  NONE\n"; }
else { foreach ($dbs as $d) { echo "  " . $d["Database"] . "\n"; } }
echo "\n";

echo "=== First symbol in stockprices ===\n";
$stmt = $pdo->query("SELECT symbol, MIN(price_date) AS fd, MAX(price_date) AS ld, COUNT(*) AS c FROM stockprices GROUP BY symbol ORDER BY symbol ASC LIMIT 1");
$r = $stmt->fetch(PDO::FETCH_ASSOC);
echo "  symbol  = " . $r['symbol'] . "\n";
echo "  first   = " . $r['fd'] . "\n";
echo "  last    = " . $r['ld'] . "\n";
echo "  rows    = " . $r['c'] . "\n\n";

echo "=== symbol_master entry ===\n";
$stmt2 = $pdo->prepare("SELECT symbol, exchange, name, currency FROM symbol_master WHERE symbol = :sym");
$stmt2->execute([':sym' => $r['symbol']]);
$sm = $stmt2->fetch(PDO::FETCH_ASSOC);
if ($sm) {
    echo "  symbol   = " . $sm['symbol'] . "\n";
    echo "  exchange = " . $sm['exchange'] . "\n";
    echo "  name     = " . $sm['name'] . "\n";
    echo "  currency = " . $sm['currency'] . "\n";
} else {
    echo "  NOT FOUND in symbol_master\n";
}
echo "\n";

echo "=== Can we write to an existing exchange DB? ===\n";
$testDb = null;
foreach ($dbs as $d) {
    $db = $d["Database"];
    if (preg_match('/^ksfraser_sm_(tsx|nasdaq|nyse|v|cse|amex|other)$/i', $db)) {
        $testDb = $db;
        break;
    }
}
if ($testDb) {
    echo "  Using existing DB: $testDb\n";
    try {
        $pdoT = new PDO("mysql:host=$host;dbname=$testDb;charset=utf8mb4", $user, $pass, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        ]);
        $pdoT->exec("CREATE TABLE IF NOT EXISTS test_write_probe (id INT PRIMARY KEY)");
        echo "  OK can write to $testDb\n";
        $pdoT->exec("DROP TABLE IF EXISTS test_write_probe");
    } catch (Throwable $e) {
        echo "  FAIL cannot write to $testDb: " . $e->getMessage() . "\n";
    }
} else {
    echo "  No exchange DB exists to test against\n";
}
