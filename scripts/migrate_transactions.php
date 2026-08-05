<?php
/**
 * Migrate legacy `transaction` data into `transactions`.
 *
 *   php scripts/migrate_transactions.php
 */

require_once __DIR__ . '/../local.php';
Local_Init();
$pdo = Local_DB()->getConnection();
$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$hasLegacy = $pdo->query("SHOW TABLES LIKE 'transaction'")->fetchColumn();
$hasModern = $pdo->query("SHOW TABLES LIKE 'transactions'")->fetchColumn();

if (!$hasLegacy || !$hasModern) {
    echo "Expected legacy `transaction` and modern `transactions` tables.\n";
    exit(1);
}

// Idempotent insert: skip duplicates on (`username`,`sequence`)
$insert = $pdo->prepare("
  INSERT IGNORE INTO transactions
    (user_id, symbol, trade_date, type, quantity, price, total, commission, account_type, source_file, source_line, notes, created_at, updated_at)
  SELECT
    (SELECT idusers FROM users WHERE username = t.username LIMIT 1),
    UPPER(t.stocksymbol),
    t.transactiondate,
    UPPER(t.transactiontype),
    t.numbershares,
    t.dollar,
    t.dollar * t.numbershares,
    0,
    t.account,
    'legacy_migration',
    0,
    CONCAT('Migrated from legacy transaction sequence=', t.sequence),
    NOW(),
    NOW()
  FROM transaction t
  WHERE t.username IS NOT NULL AND t.transactiondate IS NOT NULL
");

$insert->execute();

$count = $insert->rowCount();
echo "Inserted rows: $count\n";
