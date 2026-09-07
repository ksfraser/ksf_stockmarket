<?php

declare(strict_types=1);

/**
 * Import Research Wizard .und screen files into user_screens.
 *
 * Usage:
 *   php scripts/import_zacks_screens.php [--dir /path/to/und] [--owner zacks_rw] [--rank]
 *
 *   --dir    override the inputs directory (default: config.yaml zacks_rw.inputs_dir)
 *   --owner  override the screen-owner username (default: same config key)
 *   --rank   also populate fundamentals.zacks_rank/composite/grades so screens
 *            that filter "Zacks Rank" (field 192) have data to run against
 */

require_once __DIR__ . '/../vendor/autoload.php';
\Ksf\StockMarket\App::getInstance()->bootstrap(dirname(__DIR__));

// App::bootstrap() loads .env into $_ENV only; mirror to the real environment
// so config/database.php (getenv-based) resolves credentials in CLI context.
foreach ($_ENV as $k => $v) {
    if (is_string($v)) {
        putenv("{$k}={$v}");
        $_SERVER[$k] = $v;
    }
}

spl_autoload_register(function (string $class): void {
    foreach (['Model', 'Util', 'Controller', 'View'] as $dir) {
        $file = dirname(__DIR__) . '/src/' . $dir . '/' . $class . '.php';
        if (file_exists($file)) {
            require_once $file;
            return;
        }
    }
});

use Ksf\StockMarket\Service\ZacksRankPopulator;
use Ksf\StockMarket\Service\ZacksScreenImporter;
use Ksf\StockMarket\Util\ZacksRwConfig;

$opts = [
    'dir' => null,
    'owner' => null,
    'rank' => false,
];
foreach (array_slice($argv, 1) as $arg) {
    if (str_starts_with($arg, '--dir=')) {
        $opts['dir'] = substr($arg, 6);
    } elseif (str_starts_with($arg, '--owner=')) {
        $opts['owner'] = substr($arg, 8);
    } elseif ($arg === '--rank') {
        $opts['rank'] = true;
    }
}
if ($opts['owner'] !== null) {
    putenv('ZACKS_RW_OWNER=' . $opts['owner']);
}

try {
    $pdo = Database::get();

    $importer = new ZacksScreenImporter($pdo);
    $report = $importer->importAll($opts['dir']);

    echo 'OK' . PHP_EOL;
    echo "  owner:            {$report['owner']} (#{$report['owner_id']})" . PHP_EOL;
    echo "  files found:      {$report['found']}" . PHP_EOL;
    echo "  parsed ok:        {$report['parsed_ok']}" . PHP_EOL;
    echo "  screens inserted: {$report['inserted']}" . PHP_EOL;
    echo "  screens updated:  {$report['updated']}" . PHP_EOL;
    echo "  failed:           {$report['failed']}" . PHP_EOL;
    echo "  parser warnings:  {$report['parser_warnings']}" . PHP_EOL;

    $unsupported = 0;
    $totalRules = 0;
    foreach ($report['screens'] as $s) {
        $totalRules += $s['rules'];
    }
    echo "  rules stored:     {$totalRules}" . PHP_EOL;

    if ($opts['rank']) {
        $rank = (new ZacksRankPopulator($pdo))->populateAll();
        echo 'RANK POPULATION' . PHP_EOL;
        echo "  active symbols:  {$rank['total_active']}" . PHP_EOL;
        echo "  scored:          {$rank['scored']}" . PHP_EOL;
        echo "  updated rows:    {$rank['updated_rank']}" . PHP_EOL;
        $dist = $rank['distribution'] ?? [];
        if ($dist) {
            $parts = [];
            foreach ($dist as $r => $c) {
                $parts[] = "rank {$r}: {$c}";
            }
            echo '  distribution:    ' . implode(', ', $parts) . PHP_EOL;
        }
    }

    echo 'INPUTS DIR: ' . ZacksRwConfig::inputsDir() . PHP_EOL;
} catch (Throwable $e) {
    fwrite(STDERR, 'ERROR: ' . $e->getMessage() . PHP_EOL);
    exit(1);
}