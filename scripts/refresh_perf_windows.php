<?php

/**
 * Refresh the precomputed stock price-window table.
 *
 * Hermes' architecture note (docs/architecture/stock-filter-engine.md §3):
 * price-change windows must be pre-computed into a dedicated table refreshed
 * nightly after prices load — the same pattern as symbol_performance (ETF) and
 * performance_history (seg funds). This keeps the computation in ONE place.
 *
 * This script computes, per active symbol:
 *   Hermes perf windows  — perf_1q..perf_10a (3mo/6mo/12mo/2y/3y/5y/10y %chg)
 *   Research Wizard wins  — chg_1w/4w/12w/24w/52w/ytd + 52w high/low + range %
 * using EXACTLY the same anchored lookback logic as ZacksUniverse::loadWindows()
 * (close at MAX(price_date) <= anchor - W, anchor = universe MAX price_date).
 *
 * Upserts on (symbol, as_of_date = CURDATE()) and prunes to the last 14 days.
 *
 * Usage:
 *   php scripts/refresh_perf_windows.php [--universe-row-limit N]
 *   (deploy as cron, e.g. "0 6 * * * ... php scripts/refresh_perf_windows.php")
 */

declare(strict_types=1);

require_once dirname(__DIR__) . '/vendor/autoload.php';
\Ksf\StockMarket\App::getInstance()->bootstrap(dirname(__DIR__));

foreach ($_ENV as $k => $v) {
    if (is_string($v)) {
        putenv("{$k}={$v}");
        $_SERVER[$k] = $v;
    }
}

spl_autoload_register(static function (string $class): void {
    foreach (['Model', 'Util', 'Controller', 'View'] as $dir) {
        $file = dirname(__DIR__) . "/src/{$dir}/{$class}.php";
        if (file_exists($file)) {
            require_once $file;
            return;
        }
    }
});


$opts = getopt('', ['universe-row-limit:']);
$rowLimit = isset($opts['universe-row-limit']) ? (int) $opts['universe-row-limit'] : 0;

$pdo = \Database::get();

// ---------------------------------------------------------------------------
// 1. Schema (Hermes §3.2 + RW/zacks window columns)
// ---------------------------------------------------------------------------
$pdo->exec(
    "CREATE TABLE IF NOT EXISTS stock_performance_windows (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        symbol          VARCHAR(20)    NOT NULL,
        as_of_date      DATE           NOT NULL,
        anchor_date     DATE           NULL,
        -- Hermes filter-engine windows
        perf_1q         DOUBLE         NULL,
        perf_2q         DOUBLE         NULL,
        perf_4q         DOUBLE         NULL,
        perf_2a         DOUBLE         NULL,
        perf_3a         DOUBLE         NULL,
        perf_5a         DOUBLE         NULL,
        perf_10a        DOUBLE         NULL,
        -- Research Wizard windows
        chg_1w          DOUBLE         NULL,
        chg_4w          DOUBLE         NULL,
        chg_12w         DOUBLE         NULL,
        chg_24w         DOUBLE         NULL,
        chg_52w         DOUBLE         NULL,
        chg_ytd         DOUBLE         NULL,
        high_52w        DOUBLE         NULL,
        low_52w         DOUBLE         NULL,
        hl_range_pct    DOUBLE         NULL,
        chg_vs_high_52w DOUBLE         NULL,
        close           DOUBLE         NULL,
        created_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE INDEX unq_symbol_asof (symbol, as_of_date),
        INDEX idx_asof   (as_of_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
);

// ---------------------------------------------------------------------------
// 2. Anchor + latest closes
// ---------------------------------------------------------------------------
$anchor = (string) $pdo->query('SELECT MAX(price_date) FROM stockprices')->fetchColumn();
if ($anchor === '') {
    fwrite(STDERR, "no price data\n");
    exit(1);
}
$asOf = date('Y-m-d');
echo "anchor: {$anchor}  (as_of {$asOf})\n";

$latest = [];
$stmt = $pdo->query(
    "SELECT sm.symbol
     FROM symbol_master sm
     WHERE sm.is_active = 1"
);
$activeSymbols = $stmt->fetchAll(PDO::FETCH_COLUMN);

$stmt = $pdo->query(
    "SELECT sp.symbol, sp.price_date, sp.close
     FROM stockprices sp
     JOIN (SELECT symbol, MAX(price_date) md FROM stockprices GROUP BY symbol) g
       ON g.symbol = sp.symbol AND sp.price_date = g.md"
);
foreach ($stmt as $r) {
    $latest[(string) $r['symbol']] = ['date' => (string) $r['price_date'], 'close' => $r['close']];
}

// ---------------------------------------------------------------------------
// 3. Offset closes (same logic as ZacksUniverse::loadWindows())
// ---------------------------------------------------------------------------
/**
 * @return array<string,float>
 */
$offsetCloses = static function (string $cutoff, PDO $pdo): array {
    $stmt = $pdo->prepare(
        "SELECT s2.symbol, s2.close
         FROM stockprices s2
         JOIN (SELECT symbol, MAX(price_date) md
               FROM stockprices WHERE price_date <= ? GROUP BY symbol) g
           ON g.symbol = s2.symbol AND s2.price_date = g.md"
    );
    $stmt->execute([$cutoff]);
    $out = [];
    foreach ($stmt as $r) {
        if ($r['close'] !== null) {
            $out[(string) $r['symbol']] = (float) $r['close'];
        }
    }
    return $out;
};

// weeks => (stored window label, hermes flag)
$windows = [
    'perf_1q'  => 13,   // 3 months
    'perf_2q'  => 26,   // 6 months
    'perf_4q'  => 52,   // 12 months / 1 year
    'perf_2a'  => 104,  // 2 years
    'perf_3a'  => 156,  // 3 years
    'perf_5a'  => 260,  // 5 years
    'perf_10a' => 520,  // 10 years
    'chg_1w'   => 1,
    'chg_4w'   => 4,
    'chg_12w'  => 12,
    'chg_24w'  => 24,
    'chg_52w'  => 52,
];
$offsetSets = [];
foreach ($windows as $label => $weeks) {
    $cutoff = date('Y-m-d', strtotime($anchor . " - {$weeks} weeks"));
    $offsetSets[$label] = $offsetCloses($cutoff, $pdo);
}

// YTD open: first price_date >= Jan 1 of anchor year.
$year = substr($anchor, 0, 4);
$stmt = $pdo->prepare(
    "SELECT s2.symbol, s2.close
     FROM stockprices s2
     JOIN (SELECT symbol, MIN(price_date) md
           FROM stockprices WHERE price_date >= ? GROUP BY symbol) g
       ON g.symbol = s2.symbol AND s2.price_date = g.md"
);
$stmt->execute([$year . '-01-01']);
$ytdSet = [];
foreach ($stmt as $r) {
    if ($r['close'] !== null) {
        $ytdSet[(string) $r['symbol']] = (float) $r['close'];
    }
}

// 52-week high/low.
$from = date('Y-m-d', strtotime($anchor . ' - 52 weeks'));
$hlSet = [];
$stmt = $pdo->prepare(
    "SELECT symbol, MAX(close) high, MIN(close) low
     FROM stockprices WHERE price_date >= ? GROUP BY symbol"
);
$stmt->execute([$from]);
foreach ($stmt as $r) {
    $hlSet[(string) $r['symbol']] = ['high' => $r['high'], 'low' => $r['low']];
}

// ---------------------------------------------------------------------------
// 4. Assemble + upsert
// ---------------------------------------------------------------------------
$upsert = $pdo->prepare(
    "INSERT INTO stock_performance_windows
        (symbol, as_of_date, anchor_date,
         perf_1q, perf_2q, perf_4q, perf_2a, perf_3a, perf_5a, perf_10a,
         chg_1w, chg_4w, chg_12w, chg_24w, chg_52w, chg_ytd,
         high_52w, low_52w, hl_range_pct, chg_vs_high_52w, close)
     VALUES
        (?, ?, ?,
         ?, ?, ?, ?, ?, ?, ?,
         ?, ?, ?, ?, ?, ?,
         ?, ?, ?, ?, ?)
     ON DUPLICATE KEY UPDATE
         anchor_date = VALUES(anchor_date),
         perf_1q = VALUES(perf_1q), perf_2q = VALUES(perf_2q),
         perf_4q = VALUES(perf_4q), perf_2a = VALUES(perf_2a),
         perf_3a = VALUES(perf_3a), perf_5a = VALUES(perf_5a),
         perf_10a = VALUES(perf_10a),
         chg_1w = VALUES(chg_1w), chg_4w = VALUES(chg_4w),
         chg_12w = VALUES(chg_12w), chg_24w = VALUES(chg_24w),
         chg_52w = VALUES(chg_52w), chg_ytd = VALUES(chg_ytd),
         high_52w = VALUES(high_52w), low_52w = VALUES(low_52w),
         hl_range_pct = VALUES(hl_range_pct),
         chg_vs_high_52w = VALUES(chg_vs_high_52w),
         close = VALUES(close)"
);

$done = 0;
$skipped = 0;
foreach ($activeSymbols as $i => $symbol) {
    if ($rowLimit > 0 && $i >= $rowLimit) {
        break;
    }
    $lp = $latest[$symbol] ?? null;
    if ($lp === null || $lp['close'] === null) {
        $skipped++;
        continue;
    }
    $close = (float) $lp['close'];
    $row = ['close' => $close];
    foreach ($windows as $label => $weeks) {
        $past = $offsetSets[$label][$symbol] ?? null;
        $row[$label] = ($past !== null && $past > 0)
            ? ($close - $past) / $past * 100.0
            : null;
    }
    $yearOpen = $ytdSet[$symbol] ?? null;
    $row['chg_ytd'] = ($yearOpen !== null && $yearOpen > 0)
        ? ($close - $yearOpen) / $yearOpen * 100.0
        : null;
    $high = $hlSet[$symbol]['high'] ?? null;
    $low = $hlSet[$symbol]['low'] ?? null;
    $row['high_52w'] = $high !== null ? (float) $high : null;
    $row['low_52w'] = $low !== null ? (float) $low : null;
    $row['hl_range_pct'] = ($high !== null && $low !== null && (float) $high > (float) $low)
        ? ($close - (float) $low) / ((float) $high - (float) $low) * 100.0
        : null;
    $row['chg_vs_high_52w'] = ($high !== null && (float) $high > 0)
        ? $close / (float) $high * 100.0
        : null;

    $upsert->execute([
        $symbol, $asOf, $anchor,
        $row['perf_1q'], $row['perf_2q'], $row['perf_4q'], $row['perf_2a'],
        $row['perf_3a'], $row['perf_5a'], $row['perf_10a'],
        $row['chg_1w'], $row['chg_4w'], $row['chg_12w'], $row['chg_24w'],
        $row['chg_52w'], $row['chg_ytd'],
        $row['high_52w'], $row['low_52w'], $row['hl_range_pct'], $row['chg_vs_high_52w'],
        $close,
    ]);
    $done++;
}

// ---------------------------------------------------------------------------
// 5. Prune to last 14 as_of days
// ---------------------------------------------------------------------------
$pdo->exec(
    "DELETE spw FROM stock_performance_windows spw
     LEFT JOIN (
         SELECT DISTINCT as_of_date FROM stock_performance_windows
         ORDER BY as_of_date DESC LIMIT 14
     ) keep ON keep.as_of_date = spw.as_of_date
     WHERE keep.as_of_date IS NULL"
);

echo "PERF WINDOWS REFRESH\n";
echo "  as_of:        {$asOf}\n";
echo "  anchor:       {$anchor}\n";
echo "  active:       " . count($activeSymbols) . "\n";
echo "  updated:      {$done}\n";
echo "  skipped:      {$skipped}\n";