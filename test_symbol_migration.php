#!/usr/bin/env php
<?php
/**
 * test_symbol_migration.php — v3
 *
 * Migrates the FIRST symbol in stockprices into a per-symbol table + a
 * recent table, proving the new-db design works end-to-end.
 *
 * Uses the main DB with a test_ prefix (no CREATE DATABASE privilege needed)
 * so we can validate the SQL/routing logic; DBA creates the real exchange
 * DBs and we point the connection there in production.
 *
 * Column names match the real stockprices schema:
 *   day_open / day_high / day_low / day_close / volume / adj_close /
 *   dividend / split_ratio
 */
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
$host    = $data['db_host']    ?? 'ksfraser.ca';
$user    = $data['db_user']    ?? 'ksfraser_stockmarket';
$pass    = getenv('DB_PASS')    ?: '';
$dbname  = $data['db_name']    ?? 'ksfraser_stock_market';
if (!$pass) { fwrite(STDERR, "DB_PASS empty\n"); exit(1); }

$pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $user, $pass, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES => false,
]);

// ---- PHASE 1: Discover first symbol ----
echo "=== PHASE 1: Discover first symbol ===\n";
$stmt = $pdo->query(
    "SELECT symbol,
            MIN(price_date) AS fd,
            MAX(price_date) AS ld,
            COUNT(*) AS c
     FROM stockprices
     GROUP BY symbol
     ORDER BY symbol ASC
     LIMIT 1"
);
$symbolRow = $stmt->fetch(PDO::FETCH_ASSOC);
if (!$symbolRow) { fwrite(STDERR, "stockprices is empty\n"); exit(1); }

$firstSymbol = $symbolRow['symbol'];
$firstDate   = $symbolRow['fd'];
$lastDate    = $symbolRow['ld'];
$totalRows   = (int) $symbolRow['c'];

echo "  symbol  = $firstSymbol\n";
echo "  first   = $firstDate\n";
echo "  last    = $lastDate\n";
echo "  rows    = " . number_format($totalRows) . "\n\n";

// ---- PHASE 2: Resolve exchange ----
echo "=== PHASE 2: Resolve exchange ===\n";
$stmt2 = $pdo->prepare("SELECT symbol, exchange, name, currency FROM symbol_master WHERE symbol = :sym");
$stmt2->execute([':sym' => $firstSymbol]);
$sm = $stmt2->fetch(PDO::FETCH_ASSOC);
if (!$sm) { fwrite(STDERR, "symbol_master missing for $firstSymbol\n"); exit(1); }

$exchangeCode   = $sm['exchange'];
$symbolName     = $sm['name'];
$symbolCurrency = $sm['currency'] ?? 'CAD';

echo "  exchange = $exchangeCode\n";
echo "  name     = $symbolName\n";
echo "  currency = $symbolCurrency\n\n";

// ---- PHASE 3: Target design (test mode — same DB, prefixed tables) ----
$exchangeDbMap = [
    'TSX'    => 'ksfraser_sm_tsx',
    'TSX.V'  => 'ksfraser_sm_v',
    'NASDAQ' => 'ksfraser_sm_nasdaq',
    'NYSE'   => 'ksfraser_sm_nyse',
    'NYQ'    => 'ksfraser_sm_nyse',
    'AMEX'   => 'ksfraser_sm_amex',
    'CSE'    => 'ksfraser_sm_cse',
];
$realTargetDb  = $exchangeDbMap[$exchangeCode] ?? 'ksfraser_sm_other';
$recentSuffix  = strtolower(preg_replace('/[^a-z0-9]/i', '', $exchangeCode));
$recentTable   = 'test_price_recent_' . ($recentSuffix ?: 'other');
$symTab        = 'test_price_stock_' . str_replace(['.', '-', ' '], ['_', '_', '_'], $firstSymbol);

echo "=== PHASE 3: Target design (test mode) ===\n";
echo "  Real target DB  : $realTargetDb\n";
echo "  Test target DB  : $dbname (same DB, prefix — DBA creates real exchange DBs)\n";
echo "  Per-symbol table: $symTab\n";
echo "  Recent table    : $recentTable\n\n";

// ---- Clean up from any previous run ----
echo "=== PHASE 0: Clean up previous test tables ===\n";
$resT = $pdo->query("SHOW TABLES LIKE 'test_price_%'");
$existing = $resT->fetchAll(PDO::FETCH_COLUMN);
$found = array_filter($existing, fn($t) => strpos($t, $firstSymbol) !== false || strpos($t, 'recent_' . $recentSuffix) !== false);
if ($found) {
    foreach ($found as $t) {
        $pdo->exec("DROP TABLE IF EXISTS `$t`");
        echo "  Dropped $t\n";
    }
} else {
    echo "  No previous test tables found\n";
}
echo "\n";

// ---- PHASE 4: Create per-symbol history table ----
echo "=== PHASE 4: Create per-symbol history table ===\n";
$createSym = <<<SQL
CREATE TABLE IF NOT EXISTS `$symTab` (
    price_date   DATE            NOT NULL,
    `day_open`   DOUBLE          NULL,
    `day_high`   DOUBLE          NULL,
    `day_low`    DOUBLE          NULL,
    `day_close`  DOUBLE          NULL,
    `volume`     BIGINT          NULL,
    adj_close    DOUBLE          NULL,
    dividend     DOUBLE          DEFAULT 0,
    split_ratio  DOUBLE          DEFAULT 1,
    split_factor DOUBLE          DEFAULT 1.0,
    PRIMARY KEY (price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
SQL;
try {
    $pdo->exec($createSym);
    echo "  Created $dbname.$symTab\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "FAILED create $symTab: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- PHASE 5: Create recent table ----
echo "=== PHASE 5: Create recent table ===\n";
$createRecent = <<<SQL
CREATE TABLE IF NOT EXISTS `$recentTable` (
    symbol       VARCHAR(20)     NOT NULL,
    price_date   DATE            NOT NULL,
    `day_open`   DOUBLE          NULL,
    `day_high`   DOUBLE          NULL,
    `day_low`    DOUBLE          NULL,
    `day_close`  DOUBLE          NULL,
    `volume`     BIGINT          NULL,
    adj_close    DOUBLE          NULL,
    dividend     DOUBLE          DEFAULT 0,
    split_ratio  DOUBLE          DEFAULT 1,
    PRIMARY KEY (symbol, price_date),
    INDEX idx_date (price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
SQL;
try {
    $pdo->exec($createRecent);
    echo "  Created $dbname.$recentTable\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "FAILED create $recentTable: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- PHASE 6: Copy into per-symbol table ----
echo "=== PHASE 6: Copy into per-symbol table ===\n";
$copySym = <<<SQL
INSERT INTO `$symTab`
    (price_date, `day_open`, `day_high`, `day_low`, `day_close`, `volume`,
     adj_close, dividend, split_ratio, split_factor)
SELECT
    price_date, `day_open`, `day_high`, `day_low`, `day_close`, `volume`,
    adj_close, dividend, split_ratio, 1.0
FROM `stockprices`
WHERE symbol = :sym
ORDER BY price_date
ON DUPLICATE KEY UPDATE
    `day_open`   = VALUES(`day_open`),
    `day_high`   = VALUES(`day_high`),
    `day_low`    = VALUES(`day_low`),
    `day_close`  = VALUES(`day_close`),
    `volume`     = VALUES(`volume`),
    adj_close    = VALUES(adj_close),
    dividend     = VALUES(dividend),
    split_ratio  = VALUES(split_ratio),
    split_factor = VALUES(split_factor)
SQL;
try {
    $stmtCopy = $pdo->prepare($copySym);
    $stmtCopy->execute([':sym' => $firstSymbol]);
    $copiedSym = $stmtCopy->rowCount();
    echo "  Inserted/updated $copiedSym rows into $symTab\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "FAILED copy to $symTab: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- PHASE 7: Copy into recent table ----
echo "=== PHASE 7: Copy into recent table ===\n";
$copyRecent = <<<SQL
INSERT INTO `$recentTable`
    (symbol, price_date, `day_open`, `day_high`, `day_low`, `day_close`, `volume`,
     adj_close, dividend, split_ratio)
SELECT
    symbol, price_date, `day_open`, `day_high`, `day_low`, `day_close`, `volume`,
    adj_close, dividend, split_ratio
FROM `stockprices`
WHERE symbol = :sym
ORDER BY price_date
ON DUPLICATE KEY UPDATE
    `day_open`   = VALUES(`day_open`),
    `day_high`   = VALUES(`day_high`),
    `day_low`    = VALUES(`day_low`),
    `day_close`  = VALUES(`day_close`),
    `volume`     = VALUES(`volume`),
    adj_close    = VALUES(adj_close),
    dividend     = VALUES(dividend),
    split_ratio  = VALUES(split_ratio)
SQL;
try {
    $stmtCopyR = $pdo->prepare($copyRecent);
    $stmtCopyR->execute([':sym' => $firstSymbol]);
    $copiedRecent = $stmtCopyR->rowCount();
    echo "  Inserted/updated $copiedRecent rows into $recentTable\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "FAILED copy to $recentTable: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- PHASE 8: Verify per-symbol table ----
echo "=== PHASE 8: Verify per-symbol table ===\n";
$verSym = $pdo->prepare(
    "SELECT COUNT(*) AS c, MIN(price_date) AS fd, MAX(price_date) AS ld
     FROM `$symTab`"
);
$verSym->execute();
$vr = $verSym->fetch(PDO::FETCH_ASSOC);
$verifySymRows  = (int) $vr['c'];
$verifySymFirst = $vr['fd'];
$verifySymLast  = $vr['ld'];

echo "  Rows           : $verifySymRows (expected $totalRows)\n";
echo "  First date     : $verifySymFirst (expected $firstDate)\n";
echo "  Last date      : $verifySymLast (expected $lastDate)\n";

$spotSym = $pdo->prepare(
    "SELECT price_date,
            `day_open`, `day_high`, `day_low`, `day_close`, `volume`,
            adj_close, dividend, split_ratio, split_factor
     FROM `$symTab`
     ORDER BY price_date
     LIMIT 3"
);
$spotSym->execute();
$spotRows = $spotSym->fetchAll(PDO::FETCH_ASSOC);
echo "\n  Spot-check first 3 rows:\n";
foreach ($spotRows as $i => $r) {
    printf("    %s  O=%.2f H=%.2f L=%.2f C=%.2f V=%s Adj=%.2f Div=%.4f Split=%.4f F=%.4f\n",
        $r['price_date'],
        $r['day_open']  ?? 0,
        $r['day_high']  ?? 0,
        $r['day_low']   ?? 0,
        $r['day_close'] ?? 0,
        isset($r['volume']) && $r['volume'] !== null ? number_format($r['volume']) : 'NULL',
        $r['adj_close']  ?? 0,
        $r['dividend']   ?? 0,
        $r['split_ratio'] ?? 1,
        $r['split_factor'] ?? 1
    );
}

// ---- PHASE 9: Verify recent table ----
echo "\n=== PHASE 9: Verify recent table ===\n";
$verRecent = $pdo->prepare(
    "SELECT COUNT(*) AS c, MIN(price_date) AS fd, MAX(price_date) AS ld
     FROM `$recentTable`
     WHERE symbol = :sym"
);
$verRecent->execute([':sym' => $firstSymbol]);
$vr2 = $verRecent->fetch(PDO::FETCH_ASSOC);
$verifyRecentRows = (int) ($vr2['c'] ?? 0);

echo "  Rows           : $verifyRecentRows (expected $totalRows)\n";
echo "  First date     : " . ($vr2['fd'] ?? 'NULL') . "\n";
echo "  Last date      : " . ($vr2['ld'] ?? 'NULL') . "\n";

$spotRecent = $pdo->prepare(
    "SELECT price_date,
            `day_open`, `day_high`, `day_low`, `day_close`
     FROM `$recentTable`
     WHERE symbol = :sym
     ORDER BY price_date DESC
     LIMIT 3"
);
$spotRecent->execute([':sym' => $firstSymbol]);
$spotRecentRows = $spotRecent->fetchAll(PDO::FETCH_ASSOC);
echo "\n  Spot-check last 3 rows:\n";
foreach ($spotRecentRows as $r) {
    printf("    %s  O=%.2f H=%.2f L=%.2f C=%.2f\n",
        $r['price_date'],
        $r['day_open']  ?? 0,
        $r['day_high']  ?? 0,
        $r['day_low']   ?? 0,
        $r['day_close'] ?? 0
    );
}

// ---- RESULT ----
echo "\n=== RESULT ===\n";
$ok = ($verifySymRows === $totalRows)
    && ($verifySymFirst === $firstDate)
    && ($verifySymLast === $lastDate)
    && ($verifyRecentRows === $totalRows);

if ($ok) {
    echo "SUCCESS — $firstSymbol migrated cleanly.\n";
    echo "  Per-symbol table : $dbname.$symTab  ($verifySymRows rows)\n";
    echo "  Recent table     : $dbname.$recentTable  ($verifyRecentRows rows)\n";
    echo "\n  Sample — first row day_open/day_close match source: ";
    $firstRow = array_shift($spotRows);
    $srcFirst = $pdo->prepare("SELECT `day_open`, `day_close` FROM stockprices WHERE symbol = :sym ORDER BY price_date LIMIT 1");
    $srcFirst->execute([':sym' => $firstSymbol]);
    $sf = $srcFirst->fetch(PDO::FETCH_ASSOC);
    $match = ($firstRow['day_open'] == ($sf['day_open'] ?? 0))
          && ($firstRow['day_close'] == ($sf['day_close'] ?? 0));
    echo ($match ? "YES" : "NO — investigate!") . "\n";
    echo "\n  Next steps:\n";
    echo "  1. DBA creates real exchange DBs (ksfraser_sm_tsx / nasdaq / nyse / v / cse / amex / other)\n";
    echo "  2. Point connection at $realTargetDb instead of $dbname\n";
    echo "  3. Re-run with real exchange DB as target to confirm remote-DB path\n";
    echo "  4. Full migration script (all symbols) goes in migrate_prices_to_exchange_dbs.php\n";
    exit(0);
} else {
    fwrite(STDERR, "FAILURE — mismatch detected.\n");
    if ($verifySymRows !== $totalRows) fwrite(STDERR, "  Per-symbol row count: got $verifySymRows, expected $totalRows\n");
    if ($verifySymFirst !== $firstDate) fwrite(STDERR, "  Per-symbol first-date mismatch\n");
    if ($verifySymLast !== $lastDate) fwrite(STDERR, "  Per-symbol last-date mismatch\n");
    if ($verifyRecentRows !== $totalRows) fwrite(STDERR, "  Recent row count: got $verifyRecentRows, expected $totalRows\n");
    exit(1);
}
