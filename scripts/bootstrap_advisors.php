<?php
/**
 * Bootstrap advisor accounts.
 *
 * Usage:
 *   php scripts/bootstrap_advisors.php
 *   php scripts/bootstrap_advisors.php --slug=warren-buffet --reset
 *
 * Advisors are regular users:
 *   - role is promoted to 'advisor'
 *   - strategy and schedule live in user_settings
 *   - portfolios and transactions remain in standard shared tables
 */

if (PHP_SAPI !== 'cli') {
    die("CLI only\n");
}

$options = getopt('', ['slug:', 'reset']);
$slug = $options['slug'] ?? null;
$reset = isset($options['reset']);

$dsn = sprintf(
    'mysql:host=%s;dbname=%s;charset=%s',
    getenv('DB_HOST') ?: 'ksfraser.ca',
    getenv('DB_NAME') ?: 'ksfraser_stock_market',
    getenv('DB_CHARSET') ?: 'utf8mb4'
);
$user = getenv('DB_USER') ?: 'ksfraser_stockmarket';
$pass = getenv('DB_PASS') ?: getenv('DB_PASSWORD') ?: '';

if ($pass === '') {
    fwrite(STDERR, "ERROR: DB_PASS/DB_PASSWORD is not set.\n");
    exit(1);
}

try {
    $pdo = new PDO($dsn, $user, $pass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (Throwable $e) {
    fwrite(STDERR, "Database connection failed: " . $e->getMessage() . "\n");
    exit(1);
}

function findOrCreateUser(PDO $pdo, string $slug): int {
    $stmt = $pdo->prepare('SELECT id FROM users WHERE username = :u LIMIT 1');
    $stmt->execute([':u' => $slug]);
    $row = $stmt->fetch();
    if ($row) {
        return (int) $row['id'];
    }
    $email = $slug . '@example.com';
    $hash = password_hash('changeme', PASSWORD_DEFAULT);
    $ins = $pdo->prepare(
        'INSERT INTO users (username, email, password_hash, display_name, role, is_active) '
        . 'VALUES (:u, :e, :h, :d, "advisor", 1)'
    );
    $ins->execute([':u' => $slug, ':e' => $email, ':h' => $hash, ':d' => ucwords(str_replace('-', ' ', $slug))]);
    return (int) $pdo->lastInsertId();
}

function ensureAdvisorSettings(PDO $pdo, int $userId, string $strategy, string $schedule = 'daily'): void {
    $stmt = $pdo->prepare(
        'INSERT INTO user_settings (user_id, setting_key, setting_value, updated_at) '
        . 'VALUES (:uid, "advisor_strategy", :st, NOW()) '
        . 'ON DUPLICATE KEY UPDATE setting_value = :st, updated_at = NOW()'
    );
    $stmt->execute([':uid' => $userId, ':st' => $strategy]);
    $stmt2 = $pdo->prepare(
        'INSERT INTO user_settings (user_id, setting_key, setting_value, updated_at) '
        . 'VALUES (:uid, "advisor_schedule", :sc, NOW()) '
        . 'ON DUPLICATE KEY UPDATE setting_value = :sc, updated_at = NOW()'
    );
    $stmt2->execute([':uid' => $userId, ':sc' => $schedule]);
}

function ensureInitialPortfolio(PDO $pdo, int $userId, int $advisorId): void {
    $stmt = $pdo->prepare(
        'SELECT id FROM portfolio WHERE user_id = :uid AND account_type = :acct LIMIT 1'
    );
    $stmt->execute([':uid' => $userId, ':acct' => 'CASH']);
    $row = $stmt->fetch();
    if ($row) {
        return;
    }
    $ins = $pdo->prepare(
        'INSERT INTO portfolio (user_id, symbol, shares, cost_basis, cost_basis_total, account_type, strategy, notes, entry_date) '
        . 'VALUES (:uid, :sym, :sh, :cb, :cbt, :acct, :strat, :n, :ed)'
    );
    $ins->execute([
        ':uid' => $userId,
        ':sym' => 'CASH-CAD',
        ':sh' => 100000,
        ':cb' => 1.0,
        ':cbt' => 100000.00,
        ':acct' => 'CASH',
        ':strat' => 'Advisor Bootstrap',
        ':n' => 'Initial advisor deposit 2025-01-02',
        ':ed' => '2025-01-02',
    ]);
}

function ensurePublicVisibilities(PDO $pdo, int $userId): void {
    try {
        $stmt = $pdo->query("SELECT id FROM portfolio_visibilities LIMIT 1");
        if (!$stmt) {
            return;
        }
    } catch (Throwable $e) {
        return;
    }
    $pdo->prepare(
        'INSERT INTO portfolio_visibilities (user_id, symbol, account_type, is_public) '
        . 'SELECT :uid, symbol, account_type, 1 FROM portfolio WHERE user_id = :uid '
        . 'ON DUPLICATE KEY UPDATE is_public = 1'
    )->execute([':uid' => $userId]);
}

// ---------------------------------------------------------------------------
// Determine which slugs to process
// ---------------------------------------------------------------------------
if ($slug) {
    $slugs = ['warren-buffet' => 'buffett_quality'];
} else {
    $slugs = [
        'warren-buffet' => 'buffett_quality',
        'dividend-growth' => 'dividend_growth',
        'momentum' => 'momentum',
    ];
}

foreach ($slugs as $name => $strategy) {
    if (!is_string($name)) {
        $name = (string) $slugs;
        $strategy = 'buffett_quality';
    }

    if ($reset) {
        $del = $pdo->prepare('DELETE FROM advisor_runs WHERE user_id = (SELECT id FROM users WHERE username = :s)');
        $del->execute([':s' => $name]);
    }

    $userId = findOrCreateUser($pdo, $name);
    ensureAdvisorSettings($pdo, $userId, $strategy);
    ensureInitialPortfolio($pdo, $userId, (int) $userId);
    ensurePublicVisibilities($pdo, $userId);

    printf("Advisor '%s' ready (user_id=%d, strategy=%s)\n", $name, $userId, $strategy);
}

echo "Done.\n";
