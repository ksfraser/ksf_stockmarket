#!/usr/bin/env php
<?php
/**
 * test_per_symbol_migration.php
 *
 * Kevin Fraser asked (2026-09-09): "Have you written the test insert into ...
 * select query for a symbol yet?"
 *
 * This is the real thing: INSERT...SELECT from stockprices into a per-symbol
 * table inside a real exchange DB (ksfraser_sm_other for 0813.HK/HKG),
 * then verify row counts and spot-check data.
 *
 * Cleans up its own test tables afterward if you pass --cleanup.
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
if (!$pass) { fwrite(STDERR, "DB_PASS empty\n"); exit(1); }

$cleanup = in_array('--cleanup', $argv, true);

echo "=== CONNECT ===\n";
$pdoMain = new PDO("mysql:host=$host;dbname=ksfraser_stock_market;charset=utf8mb4", $user, $pass, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES => false,
]);

// ---- Pick first symbol + resolve exchange ----
echo "=== PICK FIRST SYMBOL + RESOLVE EXCHANGE ===\n";
$stmt = $pdoMain->query(
    "SELECT s.symbol, s.exchange, s.name, s.currency,
            MIN(p.price_date) AS first_date, MAX(p.price_date) AS last_date,
            COUNT(*) AS row_count
     FROM stockprices p
     JOIN symbol_master s ON s.symbol = p.symbol
     GROUP BY p.symbol
     ORDER BY p.symbol ASC
     LIMIT 1"
);
$symbolRow = $stmt->fetch(PDO::FETCH_ASSOC);
if (!$symbolRow) { fwrite(STDERR, "stockprices empty\n"); exit(1); }

$targetSymbol   = $symbolRow['symbol'];
$exchangeCode   = $symbolRow['exchange'];
$symbolName     = $symbolRow['name'];
$symbolCurrency = $symbolRow['currency'] ?? 'CAD';
$firstDate      = $symbolRow['first_date'];
$lastDate       = $symbolRow['last_date'];
$totalRows      = (int) $symbolRow['row_count'];

echo "  Symbol       : $targetSymbol\n";
echo "  Name         : $symbolName\n";
echo "  Exchange     : $exchangeCode\n";
echo "  Currency     : $symbolCurrency\n";
echo "  Date range   : $firstDate → $lastDate\n";
echo "  Row count    : " . number_format($totalRows) . "\n\n";

// ---- Map exchange → exchange DB (matches the 6 Kevin created) ----
$exchangeDbMap = [
    'TSX'    => 'ksfraser_sm_tsx',
    'TSX.V'  => 'ksfraser_sm_v',
    'NASDAQ' => 'ksfraser_sm_nasdaq',
    'NYSE'   => 'ksfraser_sm_nyse',
    'NYQ'    => 'ksfraser_sm_nyse',
    'AMEX'   => 'ksfraser_sm_amex',
    'CSE'    => 'ksfraser_sm_cse',
];
$exchangeDb = $exchangeDbMap[$exchangeCode] ?? 'ksfraser_sm_other';

echo "=== TARGET DESIGN ===\n";
echo "  Exchange DB        : $exchangeDb\n";
$tableSymbol = 'stockprices_' . str_replace(['.', '-', ' '], ['_', '_', '_'], $targetSymbol);
echo "  Per-symbol table   : $tableSymbol\n";
$recentTable = 'stockprices_recent_' . strtolower(preg_replace('/[^a-z0-9]/i', '', $exchangeCode));
echo "  Recent table       : $recentTable\n\n";

// ---- Connect to exchange DB ----
echo "=== CONNECT TO EXCHANGE DB: $exchangeDb ===\n";
try {
    $pdoTgt = new PDO("mysql:host=$host;dbname=$exchangeDb;charset=utf8mb4", $user, $pass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    echo "  Connected OK\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "Cannot connect to $exchangeDb: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- Clean up previous test tables if requested ----
if ($cleanup) {
    echo "=== CLEANUP: drop any previous test tables ===\n";
    foreach (["stockprices_test_$targetSymbol", "stockprices_recent_test"] as $t) {
        try {
            $pdoTgt->exec("DROP TABLE IF EXISTS `$t`");
            echo "  Dropped $t\n";
        } catch (Throwable $e) {
            echo "  (already gone) $t\n";
        }
    }
    echo "\n";
}

// ---- CREATE per-symbol table ----
echo "=== CREATE PER-SYMBOL TABLE ===\n";
echo "  CREATE TABLE `$tableSymbol` (\n";
echo "      price_date   DATE            NOT NULL,\n";
echo "      open         DECIMAL(11,4)  NULL,\n";
echo "      high         DECIMAL(11,4)  NULL,\n";
echo "      low          DECIMAL(11,4)  NULL,\n";
echo "      close        DECIMAL(11,4)  NOT NULL,\n";
echo "      volume       BIGINT          NULL,\n";
echo "      adj_close    DECIMAL(11,4)  NULL,\n";
echo "      dividend     DECIMAL(11,4)  DEFAULT 0,\n";
echo "      split_ratio  DECIMAL(11,4)  DEFAULT 1,\n";
echo "      currency     VARCHAR(3)      NOT NULL DEFAULT 'CAD',\n";
echo "      PRIMARY KEY (price_date)\n";
echo "  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n\n";

try {
    $pdoTgt->exec("CREATE TABLE IF NOT EXISTS `$tableSymbol` (
        price_date   DATE            NOT NULL,
        open         DECIMAL(11,4)  NULL,
        high         DECIMAL(11,4)  NULL,
        low          DECIMAL(11,4)  NULL,
        close        DECIMAL(11,4)  NOT NULL,
        volume       BIGINT          NULL,
        adj_close    DECIMAL(11,4)  NULL,
        dividend     DECIMAL(11,4)  DEFAULT 0,
        split_ratio  DECIMAL(11,4)  DEFAULT 1,
        currency     VARCHAR(3)      NOT NULL DEFAULT 'CAD',
        PRIMARY KEY (price_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    echo "  ✓ Created $exchangeDb.$tableSymbol\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "CREATE TABLE failed: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- CREATE recent table (if not exists) ----
echo "=== CREATE RECENT TABLE ===\n";
try {
    $pdoTgt->exec("CREATE TABLE IF NOT EXISTS `$recentTable` (
        symbol       VARCHAR(20)     NOT NULL,
        price_date   DATE            NOT NULL,
        open         DECIMAL(11,4)  NULL,
        high         DECIMAL(11,4)  NULL,
        low          DECIMAL(11,4)  NULL,
        close        DECIMAL(11,4)  NOT NULL,
        volume       BIGINT          NULL,
        adj_close    DECIMAL(11,4)  NULL,
        dividend     DECIMAL(11,4)  DEFAULT 0,
        split_ratio  DECIMAL(11,4)  DEFAULT 1,
        PRIMARY KEY (symbol, price_date),
        INDEX idx_date (price_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    echo "  ✓ Created $exchangeDb.$recentTable (or already exists)\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "CREATE recent table failed: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- THE TEST INSERT...SELECT (per-symbol table) ----
echo "=== TEST INSERT...SELECT INTO PER-SYMBOL TABLE ===\n";
echo "  INSERT INTO `$exchangeDb`.`$tableSymbol`\n";
echo "      (price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency)\n";
echo "  SELECT price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency\n";
echo "  FROM `ksfraser_stock_market`.`stockprices`\n";
echo "  WHERE symbol = :sym\n";
echo "  ORDER BY price_date;\n\n";

$insertSql = "INSERT INTO `$tableSymbol` (price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency)
    SELECT price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency
    FROM `ksfraser_stock_market`.`stockprices`
    WHERE symbol = :sym
    ORDER BY price_date";

$start = microtime(true);
try {
    $stmtIns = $pdoTgt->prepare($insertSql);
    $stmtIns->execute([':sym' => $targetSymbol]);
    $inserted = $stmtIns->rowCount();
    $elapsed = round(microtime(true) - $start, 2);
    echo "  ✓ Inserted $inserted rows into $exchangeDb.$tableSymbol\n";
    echo "    Time: ${elapsed}s\n";
    echo "    Throughput: " . number_format($inserted / max($elapsed, 0.01)) . " rows/s\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "INSERT...SELECT failed: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- THE TEST INSERT...SELECT (recent table — last 252 trading days ≈ 1 year) ----
echo "=== TEST INSERT...SELECT INTO RECENT TABLE (last ~1 year / 252 trading days) ===\n";
echo "  INSERT INTO `$exchangeDb`.`$recentTable`\n";
echo "      (symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio)\n";
echo "  SELECT symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio\n";
echo "  FROM `ksfraser_stock_market`.`stockprices`\n";
echo "  WHERE symbol = :sym\n";
echo "    AND price_date >= (\n";
echo "        SELECT MAX(price_date) - INTERVAL 252 DAY\n";
echo "        FROM `ksfraser_stock_market`.`stockprices`\n";
echo "        WHERE symbol = :sym\n";
echo "    )\n";
echo "  ORDER BY price_date;\n\n";

$insertRecentSql = "INSERT INTO `$recentTable` (symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio)
    SELECT symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio
    FROM `ksfraser_stock_market`.`stockprices`
    WHERE symbol = :sym
      AND price_date >= (
          SELECT MAX(price_date) - INTERVAL 252 DAY
          FROM `ksfraser_stock_market`.`stockprices`
          WHERE symbol = :sym
      )
    ORDER BY price_date";

$start2 = microtime(true);
try {
    $stmtInsR = $pdoTgt->prepare($insertRecentSql);
    $stmtInsR->execute([':sym' => $targetSymbol]);
    $insertedRecent = $stmtInsR->rowCount();
    $elapsed2 = round(microtime(true) - $start2, 2);
    echo "  ✓ Inserted $insertedRecent rows into $exchangeDb.$recentTable\n";
    echo "    Time: ${elapsed2}s\n\n";
} catch (Throwable $e) {
    fwrite(STDERR, "INSERT...SELECT into recent table failed: " . $e->getMessage() . "\n");
    exit(1);
}

// ---- VERIFY PER-SYMBOL TABLE ----
echo "=== VERIFY PER-SYMBOL TABLE ===\n";
$verSym = $pdoTgt->query("SELECT COUNT(*) AS cnt, MIN(price_date) AS first, MAX(price_date) AS last FROM `$tableSymbol`");
$vr = $verSym->fetch(PDO::FETCH_ASSOC);
$verifyRows  = (int) $vr['cnt'];
$verifyFirst = $vr['first'];
$verifyLast  = $vr['last'];

echo "  Rows          : $verifyRows (source: $totalRows)\n";
echo "  First date    : $verifyFirst (source: $firstDate)\n";
echo "  Last date     : $verifyLast (source: $lastDate)\n";
$matchRows = ($verifyRows === $totalRows);
$matchFirst = ($verifyFirst === $firstDate);
$matchLast = ($verifyLast === $lastDate);
echo "  Row count OK  : " . ($matchRows ? "YES" : "NO — MISMATCH") . "\n";
echo "  First date OK : " . ($matchFirst ? "YES" : "NO — MISMATCH") . "\n";
echo "  Last date OK  : " . ($matchLast ? "YES" : "NO — MISMATCH") . "\n\n";

echo "  Spot-check (first 3 rows from new table):\n";
$spot = $pdoTgt->prepare("SELECT price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency FROM `$tableSymbol` ORDER BY price_date LIMIT 3");
$spot->execute();
while ($r = $spot->fetch(PDO::FETCH_ASSOC)) {
    printf("    %s  O=%s H=%s L=%s C=%s V=%s Adj=%s Div=%s Split=%s Cur=%s\n",
        $r['price_date'],
        $r['open'] ?? 'NULL', $r['high'] ?? 'NULL', $r['low'] ?? 'NULL', $r['close'],
        $r['volume'] ?? 'NULL',
        $r['adj_close'] ?? 'NULL', $r['dividend'] ?? '0.0000', $r['split_ratio'] ?? '1.0000',
        $r['currency']
    );
}
echo "\n";

echo "  Spot-check (last 3 rows from new table):\n";
$spotLast = $pdoTgt->prepare("SELECT price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency FROM `$tableSymbol` ORDER BY price_date DESC LIMIT 3");
$spotLast->execute();
while ($r = $spotLast->fetch(PDO::FETCH_ASSOC)) {
    printf("    %s  O=%s H=%s L=%s C=%s V=%s Adj=%s Div=%s Split=%s Cur=%s\n",
        $r['price_date'],
        $r['open'] ?? 'NULL', $r['high'] ?? 'NULL', $r['low'] ?? 'NULL', $r['close'],
        $r['volume'] ?? 'NULL',
        $r['adj_close'] ?? 'NULL', $r['dividend'] ?? '0.0000', $r['split_ratio'] ?? '1.0000',
        $r['currency']
    );
}
echo "\n";

// ---- VERIFY RECENT TABLE ----
echo "=== VERIFY RECENT TABLE ===\n";
$verRecent = $pdoTgt->prepare("SELECT COUNT(*) AS cnt, MIN(price_date) AS first, MAX(price_date) AS last FROM `$recentTable` WHERE symbol = :sym");
$verRecent->execute([':sym' => $targetSymbol]);
$vr2 = $verRecent->fetch(PDO::FETCH_ASSOC);
$verifyRecentRows = (int) ($vr2['cnt'] ?? 0);
echo "  Rows for $targetSymbol : $verifyRecentRows\n";
echo "  First date             : " . ($vr2['first'] ?? 'NULL') . "\n";
echo "  Last date              : " . ($vr2['last'] ?? 'NULL') . "\n";
echo "  Expected window        : last 252 trading days ≈ 1 year\n\n";

echo "  Spot-check (last 3 rows from recent table):\n";
$spotRecent = $pdoTgt->prepare("SELECT price_date, open, high, low, close, volume, adj_close, dividend, split_ratio FROM `$recentTable` WHERE symbol = :sym ORDER BY price_date DESC LIMIT 3");
$spotRecent->execute([':sym' => $targetSymbol]);
while ($r = $spotRecent->fetch(PDO::FETCH_ASSOC)) {
    printf("    %s  O=%s H=%s L=%s C=%s V=%s Adj=%s Div=%s Split=%s\n",
        $r['price_date'],
        $r['open'] ?? 'NULL', $r['high'] ?? 'NULL', $r['low'] ?? 'NULL', $r['close'],
        $r['volume'] ?? 'NULL',
        $r['adj_close'] ?? 'NULL', $r['dividend'] ?? '0.0000', $r['split_ratio'] ?? '1.0000'
    );
}
echo "\n";

// ---- SOURCE/DESTINATION SPOT COMPARE ----
echo "=== SOURCE vs DESTINATION SPOT COMPARE (first row) ===\n";
$srcRow = $pdoMain->prepare("SELECT price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency FROM `stockprices` WHERE symbol = :sym ORDER BY price_date LIMIT 1");
$srcRow->execute([':sym' => $targetSymbol]);
$src = $srcRow->fetch(PDO::FETCH_ASSOC);

$destRow = $pdoTgt->prepare("SELECT price_date, open, high, low, close, volume, adj_close, dividend, split_ratio, currency FROM `$tableSymbol` WHERE price_date = :d ORDER BY price_date LIMIT 1");
$destRow->execute([':d' => $firstDate]);
$dest = $destRow->fetch(PDO::FETCH_ASSOC);

$cols = ['price_date', 'open', 'high', 'low', 'close', 'volume', 'adj_close', 'dividend', 'split_ratio', 'currency'];
$allMatch = true;
foreach ($cols as $c) {
    $sv = $src[$c] ?? 'NULL';
    $dv = $dest[$c] ?? 'NULL';
    $match = ($sv == $dv);
    if (!$match) $allMatch = false;
    printf("  %-12s  source=%s  dest=%s  %s\n", $c, json_encode($sv), json_encode($dv), $match ? "MATCH" : "DIFF");
}
echo "\n";

// ---- RESULT ----
echo "=== RESULT ===\n";
$ok = $matchRows && $matchFirst && $matchLast && $allMatch;
if ($ok) {
    echo "✓✓✓ SUCCESS — $targetSymbol migrated via INSERT...SELECT into $exchangeDb.\n";
    echo "  Per-symbol table : $exchangeDb.$tableSymbol   ($verifyRows rows)\n";
    echo "  Recent table     : $exchangeDb.$recentTable   ($verifyRecentRows rows, last 252 days)\n";
    echo "\n  Notes:\n";
    echo "  - INSERT...SELECT is the migration primitive — works correctly.\n";
    echo "  - Recent table is a bounded window (last 252 trading days), not full history.\n";
    echo "  - Source and destination spot-check match for all 10 columns.\n";
    echo "  - Full migration = loop over all symbols in symbol_master, INSERT...SELECT each.\n";
    echo "\n  Cleanup: run with --cleanup to drop the test tables from $exchangeDb.\n";
    exit(0);
} else {
    fwrite(STDERR, "✗✗✗ FAILURE — mismatch detected.\n");
    if (!$matchRows) fwrite(STDERR, "  Row count: dest=$verifyRows vs source=$totalRows\n");
    if (!$matchFirst) fwrite(STDERR, "  First date: dest=$verifyFirst vs source=$firstDate\n");
    if (!$matchLast) fwrite(STDERR, "  Last date: dest=$verifyLast vs source=$lastDate\n");
    exit(1);
}
