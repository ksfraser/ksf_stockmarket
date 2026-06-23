<?php
/**
 * Bootstrap advisor accounts.
 *
 * Usage:
 *   php scripts/bootstrap_advisors.php
 *   php scripts/bootstrap_advisors.php --slug=warren-buffet --reset
 *
 * Each advisor:
 *   - gets a normal user record
 *   - gets an advisor_accounts row
 *   - gets portfolio_visibilities set to public
 *   - starts with 100,000 CAD deposited on 2025-01-02
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
    $hash = password_hash('change-me', PASSWORD_DEFAULT);
    $ins = $pdo->prepare(
        'INSERT INTO users (username, email, password_hash, role) VALUES (:u, :e, :h, :r)'
    );
    $ins->execute([':u' => $slug, ':e' => $email, ':h' => $hash, ':r' => 'trader']);
    return (int) $pdo->lastInsertId();
}

function findOrCreateAdvisor(PDO $pdo, int $userId, string $slug, string $strategy = 'buffett_quality', string $schedule = 'daily'): int {
    $stmt = $pdo->prepare('SELECT id FROM advisor_accounts WHERE user_id = :uid LIMIT 1');
    $stmt->execute([':uid' => $userId]);
    $row = $stmt->fetch();
    if ($row) {
        // Ensure slug and strategy are up to date on re-runs.
        $upd = $pdo->prepare(
            'UPDATE advisor_accounts SET slug = :s, strategy = :st, is_active = 1 WHERE id = :id'
        );
        $upd->execute([':s' => $slug, ':st' => $strategy, ':id' => $row['id']]);
        return (int) $row['id'];
    }
    $ins = $pdo->prepare(
        'INSERT INTO advisor_accounts (user_id, slug, strategy, display_name, profile_json, is_active) VALUES (:uid, :s, :st, :dn, :pj, 1)'
    );
    $displayName = ucwords(str_replace('-', ' ', $slug));
        $profileJson = json_encode(['schedule' => $schedule]);
        $ins->execute([':uid' => $userId, ':s' => $slug, ':st' => $strategy, ':dn' => $displayName, ':pj' => $profileJson]);
    return (int) $pdo->lastInsertId();
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
        'INSERT INTO portfolio (user_id, symbol, shares, cost_basis, cost_basis_total, account_type, strategy, notes, entry_date)
         VALUES (:uid, :sym, :sh, :cb, :cbt, :acct, :strat, :n, :ed)'
    );
    $ins->execute([
        ':uid' => $userId,
        ':sym' => 'CASH',
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
    // Best-effort: mark all portfolio lines public if the table exists.
    try {
        $stmt = $pdo->query("SELECT id FROM portfolio_visibilities LIMIT 1");
        if (!$stmt) {
            return;
        }
    } catch (Throwable $e) {
        // Table doesn't exist yet; skip.
        return;
    }
    $pdo->prepare(
        'INSERT INTO portfolio_visibilities (user_id, symbol, account_type, is_public)
         SELECT :uid, symbol, account_type, 1
         FROM portfolio
         WHERE user_id = :uid
         ON DUPLICATE KEY UPDATE is_public = 1'
    )->execute([':uid' => $userId]);
}

// ---------------------------------------------------------------------------
// Determine which slugs to process
// ---------------------------------------------------------------------------
if ($slug) {
    $slugs = [$slug];
} else {
    // Default advisors if none specified.
    $slugs = [
        'warren-buffet' => 'buffett_quality',
        'dividend-growth' => 'dividend_growth',
        'momentum' => 'momentum',
    ];
}

foreach ($slugs as $name => $strategy) {
    if (!is_string($name)) {
        // Single --slug was passed without a strategy alias.
        $name = (string) $slugs;
        $strategy = 'buffett_quality';
    }

    if ($reset) {
        $del = $pdo->prepare('DELETE FROM advisor_runs WHERE advisor_id = (SELECT id FROM advisor_accounts WHERE slug = :s)');
        $del->execute([':s' => $name]);
    }

    $userId = findOrCreateUser($pdo, $name);
    $advisorId = findOrCreateAdvisor($pdo, $userId, $name, $strategy);
    ensureInitialPortfolio($pdo, $userId, $advisorId);
    ensurePublicVisibilities($pdo, $userId);

    printf("Advisor '%s' ready (user_id=%d, advisor_id=%d)\n", $name, $userId, $advisorId);
}

echo "Done.\n";
