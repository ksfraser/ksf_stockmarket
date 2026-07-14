<?php
/**
 * SymbolResolver unit tests.
 *
 * Run: php tests/test_symbol_resolver.php
 */

require_once __DIR__ . '/../php/src/Util/SymbolResolver.php';

// In-memory SQLite makes for a realistic zero-row resolver
$pdo = new PDO('sqlite::memory:');

// Seed tables so resolver doesn't crash on missing schema
$pdo->exec("CREATE TABLE IF NOT EXISTS exchange_mapping (
    id INT PRIMARY KEY, symbol VARCHAR(32), yahoo_ticker VARCHAR(32),
    is_primary INT DEFAULT 1, is_active INT DEFAULT 1
)");
$pdo->exec("CREATE TABLE IF NOT EXISTS symbol_master (
    symbol VARCHAR(32) PRIMARY KEY, name VARCHAR(255), exchange VARCHAR(32),
    sector VARCHAR(128), industry VARCHAR(128)
)");
$pdo->exec("CREATE TABLE IF NOT EXISTS portfolio (
    symbol VARCHAR(32) PRIMARY KEY, price_symbol VARCHAR(32)
)");

// exchange_mapping seeds
$pdo->exec("INSERT INTO exchange_mapping (id, symbol, yahoo_ticker)
    VALUES (1, 'SRV.UN', 'SRV-UN.TO'), (2, 'BPF.UN', 'BPF-UN.TO')");

// symbol_master seeds
$pdo->exec("INSERT INTO symbol_master (symbol, exchange) VALUES ('CNR', 'TSX')");
$pdo->exec("INSERT INTO symbol_master (symbol, exchange) VALUES ('GOLD', 'NYSE')");

$resolver = new SymbolResolver($pdo);

$passed = 0;
$failed = 0;

function assert_equals(string $label, $expected, $actual): void {
    global $passed, $failed;
    if ($expected === $actual) {
        echo "  PASS: $label\n";
        $passed++;
    } else {
        echo "  FAIL: $label — expected " . var_export($expected, true) . ", got " . var_export($actual, true) . "\n";
        $failed++;
    }
}

echo "=== Suffix handling (no matching rows) ===\n";
assert_equals('PNG stays PNG',                        'PNG',   $resolver->resolve('PNG'));
assert_equals('AAPL stays AAPL',                      'AAPL',  $resolver->resolve('AAPL'));
assert_equals('GLD stays GLD',                        'GLD',   $resolver->resolve('GLD'));

echo "\n=== .UN suffix normalization (exchange_mapping branch) ===\n";
assert_equals('SRV.UN → SRV-UN.TO',                   'SRV-UN.TO', $resolver->resolve('SRV.UN'));
assert_equals('BPF.UN → BPF-UN.TO',                   'BPF-UN.TO', $resolver->resolve('BPF.UN'));

echo "\n=== symbol_master TSX branch ===\n";
assert_equals('CNR → CNR.TO',                         'CNR.TO', $resolver->resolve('CNR'));
assert_equals('GOLD stays GOLD',                      'GOLD',   $resolver->resolve('GOLD'));

echo "\n=== .B.TO class share hyphenation ===\n";
assert_equals('BF.B.TO stays BF-B.TO',               'BF-B.TO', $resolver->resolve('BF.B.TO'));
assert_equals('AGF.B.TO stays AGF-B.TO',             'AGF-B.TO', $resolver->resolve('AGF.B.TO'));
assert_equals('BAM-A.TO stays BAM-A.TO',             'BAM-A.TO', $resolver->resolve('BAM-A.TO'));

echo "\n=== TSX Venture .V suffix ===\n";
assert_equals('VX.V stays VX.V',                     'VX.V',   $resolver->resolve('VX.V'));
assert_equals('CNE.V stays CNE.V',                   'CNE.V',  $resolver->resolve('CNE.V'));

echo "\n=== hyphen-dot canonicalization ===\n";
assert_equals('AW.UN.TO → AW-UN.TO',                 'AW-UN.TO', $resolver->resolve('AW.UN.TO'));
assert_equals('BNE.UN.TO → BNE-UN.TO',               'BNE-UN.TO', $resolver->resolve('BNE.UN.TO'));

echo "\n=== candidates() ===\n";
$c = $resolver->candidates('SRV.UN');
assert_equals('candidates[0] = original',             'SRV.UN',    $c[0] ?? null);
assert_equals('candidates[1] = resolved',             'SRV-UN.TO', $c[1] ?? null);

echo "\n=== Summary ===\n";
echo "Passed: $passed, Failed: $failed\n";
exit($failed > 0 ? 1 : 0);
