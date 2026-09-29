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

$queries = [
    ["Exchange DBs that exist", "SHOW DATABASES LIKE 'ksfraser_sm_%'"],
    ["Stockprices columns", "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'ksfraser_stock_market' AND TABLE_NAME = 'stockprices' ORDER BY ORDINAL_POSITION"],
    ["Stockprices indexes", "SHOW INDEX FROM stockprices"],
    ["First 3 symbols + counts", "SELECT symbol, COUNT(*) AS cnt, MIN(price_date) AS first, MAX(price_date) AS last FROM stockprices GROUP BY symbol ORDER BY symbol ASC LIMIT 3"],
    ["Max price_date", "SELECT MAX(price_date) FROM stockprices"],
    ["0813.HK last 3 rows", "SELECT * FROM stockprices WHERE symbol = '0813.HK' ORDER BY price_date DESC LIMIT 3"],
    ["0813.HK first 3 rows", "SELECT * FROM stockprices WHERE symbol = '0813.HK' ORDER BY price_date ASC LIMIT 3"],
    ["Per-symbol tables (stockprices_%)", "SHOW TABLES LIKE 'stockprices_%'"],
    ["test_* tables", "SHOW TABLES LIKE 'test_%'"],
];

foreach ($queries as $q) {
    echo "=== {$q[0]} ===\n";
    try {
        $res = $pdo->query($q[1]);
        if ($res === false) {
            echo "  (query returned false)\n";
            continue;
        }
        $rows = $res->fetchAll(PDO::FETCH_ASSOC);
        if (empty($rows)) {
            echo "  (empty)\n";
        } else {
            // Print header
            $cols = array_keys($rows[0]);
            // Calculate column widths
            $widths = [];
            foreach ($cols as $c) $widths[$c] = strlen($c);
            $rowsToPrint = $rows;
            // Also include "rows" key use: if numeric, format
            foreach ($rowsToPrint as $row) {
                foreach ($cols as $c) {
                    $val = $row[$c];
                    if (is_null($val)) $val = "NULL";
                    elseif (is_bool($val)) $val = $val ? "1" : "0";
                    elseif (is_numeric($val)) $val = $val;
                    else $val = (string)$val;
                    $widths[$c] = max($widths[$c], strlen($val));
                }
            }
            // Print header
            foreach ($cols as $c) printf("%-${widths[$c]}s  ", $c);
            echo "\n";
            echo str_repeat("-", array_sum($widths) + 2 * count($cols)) . "\n";
            // Print rows
            foreach ($rowsToPrint as $row) {
                foreach ($cols as $c) {
                    $val = $row[$c];
                    if (is_null($val)) $val = "NULL";
                    elseif (is_bool($val)) $val = $val ? "1" : "0";
                    else $val = (string)$val;
                    printf("%-${widths[$c]}s  ", $val);
                }
                echo "\n";
            }
        }
    } catch (Throwable $e) {
        echo "  ERROR: " . $e->getMessage() . "\n";
    }
    echo "\n";
}
