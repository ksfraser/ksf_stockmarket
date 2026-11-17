<?php

declare(strict_types=1);

/**
 * Batch-run all active Zacks RW screens and persist results to tradingview_screener_results.
 *
 * Usage:
 *   php scripts/cron/run_rw_screens.php
 *
 * Exit codes:
 *   0 = success
 *   1 = partial failure
 */

require_once __DIR__ . '/../../vendor/autoload.php';
\ksfraser\StockMarket\App::getInstance()->bootstrap(dirname(__DIR__, 2));

// Mirror env for config/database.php (getenv-based) in CLI context
foreach ($_ENV as $k => $v) {
    if (is_string($v)) {
        putenv("{$k}={$v}");
        $_SERVER[$k] = $v;
    }
}

use ksfraser\StockMarket\Controller\ZacksScreenController;
use ksfraser\StockMarket\Model\Database;
use ksfraser\StockMarket\Util\ZacksFieldResolver;
use ksfraser\StockMarket\Service\ZacksScreenRunner;
use ksfraser\StockMarket\Service\ZacksUniverse;

$pdo = Database::get();
$startedAt = date('Y-m-d H:i:s');

// Load all active stock screens (including private ones for system cron)
$stmt = $pdo->query("
    SELECT us.id, us.name, us.filters_json, u.username AS owner
    FROM user_screens us
    JOIN users u ON u.id = us.user_id
    WHERE us.universe = 'stocks'
      AND us.is_deleted = 0
    ORDER BY us.id ASC
");
$screens = $stmt->fetchAll(PDO::FETCH_ASSOC);

if (!$screens) {
    echo "[{$startedAt}] No active screens found.\n";
    exit(0);
}

echo "[{$startedAt}] Running " . count($screens) . " screen(s)...\n";

$resolver = new ZacksFieldResolver();
$runner = new ZacksScreenRunner($resolver);
$controller = new ZacksScreenController();

$totalMatched = 0;
$errors = [];

foreach ($screens as $screen) {
    $id = (int)$screen['id'];
    $name = $screen['name'];

    try {
        $payload = json_decode((string)$screen['filters_json'], true);
        if (!is_array($payload) || ($payload['engine'] ?? '') !== 'zacks_rw') {
            echo "  Screen #{$id} ({$name}): skipped — not a Zacks RW screen\n";
            continue;
        }

        $rules = is_array($payload['rules'] ?? null) ? $payload['rules'] : [];

        $universe = new ZacksUniverse($pdo);
        $universe->setNeedVol20(ZacksScreenRunner::requiresVol20($rules, $resolver));
        $universe->load();

        $result = $runner->run($rules, $universe);
        $result['universe_size'] = $universe->count();
        $result['rule_count'] = count($rules);

        // Persist results into tradingview_screener_results
        $screenNameSlug = preg_replace('/[^a-z0-9_]/i', '_', $name);
        $presetName = 'rw_screen_' . $id . '_' . $screenNameSlug;
        $market = 'america';

        // Remove previous results for this screen
        $pdo->prepare('DELETE FROM tradingview_screener_results WHERE preset_name = :pn')
            ->execute([':pn' => $presetName]);

        // Insert new results
        $insert = $pdo->prepare('
            INSERT INTO tradingview_screener_results (preset_name, market, symbol, data, run_at)
            VALUES (:pn, :mkt, :sym, :data, NOW())
        ');
        foreach ($result['symbols'] as $row) {
            $insert->execute([
                ':pn' => $presetName,
                ':mkt' => $market,
                ':sym' => $row['symbol'] ?? '',
                ':data' => json_encode($row, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
            ]);
        }

        $matched = count($result['symbols']);
        $totalMatched += $matched;
        echo "  Screen #{$id} ({$name}): {$matched} matched / " . $result['universe_size'] . " universe, " . count($result['skipped']) . " skipped\n";
    } catch (Throwable $e) {
        $errors[] = "Screen #{$id} ({$name}): " . $e->getMessage();
        echo "  Screen #{$id} ({$name}): ERROR — " . $e->getMessage() . "\n";
    }
}

echo "\n[{$startedAt}] Done. Total matched: {$totalMatched}";
if ($errors) {
    echo "\nErrors:\n";
    foreach ($errors as $err) {
        echo "  - {$err}\n";
    }
    exit(1);
}
echo "\n";
exit(0);
