<?php
/**
 * Unified ratings/criteria overview for the detail page.
 *
 * Aggregates checks from:
 * - Buffett Quality
 * - Zacks-style Composite
 * - VectorVest 5-Point Checklist
 * - Exit Signal Risk Assessment
 *
 * Criteria are grouped by category to reduce overlap noise.
 */

$buffettChecks     = $buffettScore['checks'] ?? [];
$zacksChecks       = $zacksScore['checks'] ?? [];
$vvChecks          = $vectorvest['checks'] ?? [];
$exitDetails       = $exitSignals['individual_signals'] ?? [];
$exitWeights       = $exitSignals['signal_weights'] ?? [];

$vvPassCount       = $vectorvest['pass_count'] ?? 0;
$vvMax             = $vectorvest['max'] ?? 5;
$vvScore           = $vectorvest['score'] ?? 0;

$buffettTotal      = $buffettScore['total'] ?? null;
$zacksRank         = $zacksScore['rank'] ?? null;
$zacksRankText     = $zacksScore['rank_text'] ?? 'N/A';
$zacksComposite    = $zacksScore['composite'] ?? null;
$zacksVgmGrade     = $zacksScore['vgm_grade'] ?? 'N/A';

$exitRisk          = $exitSignals['composite_exit_risk'] ?? null;
$exitTriggered     = $exitSignals['n_signals_triggered'] ?? 0;
$exitTotalSignals  = $exitSignals['n_signals_total'] ?? 0;

/**
 * Normalize a check to:
 *   ['name' => string, 'passed' => bool|null, 'sources' => string[]]
 */
$norm = [];

// Buffett -> Quality/Growth/Valuation
$mapBuffett = [
    'ROE > 15%'       => ['Quality', 'Return on Equity'],
    'D/E < 0.5'       => ['Quality', 'Debt/Equity'],
    'Margin > 10%'    => ['Quality', 'Profit Margin'],
    'Positive FCF'    => ['Quality', 'Free Cash Flow'],
    'Payout < 60%'    => ['Quality', 'Dividend Payout Ratio'],
    'Rev Growth+'     => ['Growth', 'Revenue Growth'],
    'CR > 1.5'        => ['Quality', 'Current Ratio'],
    'Beta < 1.2'      => ['Risk', 'Beta'],
    'P/E < 25x'       => ['Valuation', 'Trailing P/E'],
];
foreach ($buffettChecks as $label => $passed) {
    if (isset($mapBuffett[$label])) {
        [$cat, $name] = $mapBuffett[$label];
        $key = $cat . '::' . $name;
        if (!isset($norm[$key])) {
            $norm[$key] = ['category' => $cat, 'name' => $name, 'passed' => $passed, 'sources' => []];
        }
        $norm[$key]['sources'][] = 'Buffett';
        if ($norm[$key]['passed'] === null) $norm[$key]['passed'] = $passed;
    }
}

// Zacks -> Value/Growth/Momentum mapped to categories
$mapZacks = [
    'P/E < 20x'          => ['Valuation', 'Trailing P/E'],
    'P/B < 2.0'          => ['Valuation', 'Price/Book'],
    'FCF Yield > 3%'     => ['Valuation', 'FCF Yield'],
    'D/E < 0.8'          => ['Quality', 'Debt/Equity'],
    'EPS Growth > 10%'   => ['Growth', 'EPS Growth'],
    'Revenue Growth > 5%'=> ['Growth', 'Revenue Growth'],
    'Price > SMA200'     => ['Momentum', 'Price vs 200D SMA'],
    'RSI 30-65'          => ['Momentum', 'RSI(14)'],
];
foreach ($zacksChecks as $label => $passed) {
    if (isset($mapZacks[$label])) {
        [$cat, $name] = $mapZacks[$label];
        $key = $cat . '::' . $name;
        if (!isset($norm[$key])) {
            $norm[$key] = ['category' => $cat, 'name' => $name, 'passed' => $passed, 'sources' => []];
        }
        $norm[$key]['sources'][] = 'Zacks';
        if ($norm[$key]['passed'] === null) $norm[$key]['passed'] = $passed;
    }
}

// VectorVest -> Momentum/Growth
$mapVV = [
    'smooth_uptrend'   => ['Momentum', 'Smooth Uptrend'],
    'price_rising'     => ['Momentum', 'Price Rising (20D)'],
    'earnings_rising'  => ['Growth', 'Earnings Rising'],
    'follow_through'   => ['Momentum', 'Follow-Through'],
];
foreach ($vvChecks as $key => $check) {
    if (isset($mapVV[$key])) {
        [$cat, $name] = $mapVV[$key];
        $passed = $check['passed'] ?? null;
        $nk = $cat . '::' . $name;
        if (!isset($norm[$nk])) {
            $norm[$nk] = ['category' => $cat, 'name' => $name, 'passed' => $passed, 'sources' => []];
        }
        $norm[$nk]['sources'][] = 'VectorVest';
        if ($norm[$nk]['passed'] === null) $norm[$nk]['passed'] = $passed;
    }
}

// Exit signals -> Risk
$exitMeta = [
    'trailing_stop_breach' => ['Momentum', 'Trailing Stop Breach'],
    'rsi_overbought'       => ['Momentum', 'RSI Overbought'],
    'ma200_breakdown'      => ['Momentum', '200D MA Breakdown'],
    'bb_upper_touch'       => ['Momentum', 'BB Upper Touch'],
    'roe_deterioration'    => ['Quality', 'ROE Deterioration'],
    'debt_equity_rise'     => ['Quality', 'Debt/Equity Rise'],
    'fcf_negative'         => ['Quality', 'Negative FCF'],
    'pe_extreme'           => ['Valuation', 'P/E Extreme'],
];
foreach ($exitDetails as $key => $triggered) {
    $triggered = (bool)$triggered;
    if (isset($exitMeta[$key])) {
        [$cat, $name] = $exitMeta[$key];
        $nk = $cat . '::' . $name;
        if (!isset($norm[$nk])) {
            $norm[$nk] = ['category' => $cat, 'name' => $name, 'passed' => null, 'sources' => []];
        }
        // For exit signals, "passed" from a scoring perspective means NOT triggered
        $passed = !$triggered;
        // Keep first positive pass if already set; this is simplistic but avoids false negatives
        if ($norm[$nk]['passed'] === null) {
            $norm[$nk]['passed'] = $passed;
        }
        $norm[$nk]['sources'][] = 'Exit Signals';
    }
}

// Group by category order
$catOrder = ['Quality', 'Growth', 'Valuation', 'Momentum', 'Risk'];
$grouped = array_fill_keys($catOrder, []);
foreach ($norm as $item) {
    $cat = $item['category'];
    if (!isset($grouped[$cat])) $grouped[$cat] = [];
    $grouped[$cat][] = $item;
}

$compositeScores = array_filter([
    $buffettTotal !== null ? ['Buffett', $buffettTotal, 100] : null,
    $zacksRank !== null ? ['Zacks', ($zacksRank - 1) * 25, 100] : null, // rough 1..5 -> 0..100
    $vvScore ? ['VectorVest', $vvScore, 100] : null,
    $exitRisk !== null ? ['Exit Risk', round((1 - $exitRisk) * 100, 1), 100] : null,
]);
?>

<div class="card" style="border-color:var(--accent);margin-top:12px;">
    <div class="card-header">&#x1F3AF; Ratings & Criteria Overview</div>
    <p style="margin-bottom:12px;color:var(--text2);font-size:0.9em;">
        Unified view of quality, growth, valuation, momentum, and risk checks drawn from
        Buffett, Zacks, VectorVest, and exit-signal models.
    </p>

    <!-- Composite Scores -->
    <div class="stats-grid" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr));margin-bottom:16px;">
        <?php if ($buffettTotal !== null): ?>
        <div class="stat-card">
            <div class="stat-value" style="color:<?= $buffettTotal >= 70 ? 'var(--green)' : (($buffettTotal >= 50 ? 'var(--yellow)' : 'var(--red)')) ?>">
                <?= (int)$buffettTotal ?>/100
            </div>
            <div class="stat-label">Buffett Quality</div>
        </div>
        <?php endif; ?>
        <?php if ($zacksRankText !== 'N/A'): ?>
        <div class="stat-card">
            <div class="stat-value" style="color:<?= ($zacksRank ?? 5) <= 2 ? 'var(--green)' : (($zacksRank == 3) ? 'var(--yellow)' : 'var(--red)') ?>">
                <?= htmlspecialchars($zacksRankText) ?>
                <div style="font-size:0.5em;color:var(--text3);">Rank <?= (int)($zacksRank ?? 0) ?>/5</div>
            </div>
            <div class="stat-label">Zacks Style</div>
        </div>
        <?php endif; ?>
        <?php if ($vvScore): ?>
        <div class="stat-card">
            <div class="stat-value" style="color:<?= $vvScore >= 80 ? 'var(--green)' : (($vvScore >= 60 ? 'var(--yellow)' : 'var(--red)')) ?>">
                <?= (int)$vvScore ?>/100
            </div>
            <div class="stat-label">VectorVest (<?= $vvPassCount ?>/<?= $vvMax ?>)</div>
        </div>
        <?php endif; ?>
        <?php if ($exitRisk !== null): ?>
        <div class="stat-card">
            <div class="stat-value" style="color:<?= $exitRisk >= 0.6 ? 'var(--red)' : (($exitRisk >= 0.3 ? 'var(--yellow)' : 'var(--green)')) ?>">
                <?= round($exitRisk * 100) ?>%
            </div>
            <div class="stat-label">Exit Risk</div>
        </div>
        <?php endif; ?>
    </div>

    <!-- Criteria Grid by Category -->
    <?php foreach ($catOrder as $cat): if (empty($grouped[$cat])) continue; ?>
        <div style="margin-bottom:14px;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;margin-bottom:6px;letter-spacing:0.08em;">
                <?= htmlspecialchars($cat) ?>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
                <?php foreach ($grouped[$cat] as $item): 
                    $passed = $item['passed'];
                    $badgeBg = match(true) {
                        $passed === true  => 'var(--green-bg)',
                        $passed === false => 'var(--red-bg)',
                        default           => 'rgba(255,255,255,0.06)',
                    };
                    $color = match(true) {
                        $passed === true  => 'var(--green)',
                        $passed === false => 'var(--red)',
                        default           => 'var(--text3)',
                    };
                    $icon = match(true) {
                        $passed === true  => '✓',
                        $passed === false => '✗',
                        default           => '•',
                    };
                ?>
                <span style="
                    display:inline-flex;align-items:center;gap:6px;
                    padding:4px 10px;border-radius:999px;font-size:0.8em;
                    background:<?= $badgeBg ?>;color:<?= $color ?>;
                    border:1px solid rgba(255,255,255,0.06);
                ">
                    <span style="font-weight:700;"><?= $icon ?></span>
                    <span><?= htmlspecialchars($item['name']) ?></span>
                    <span style="opacity:0.7;font-size:0.85em;">
                        <?= htmlspecialchars(implode(', ', array_unique($item['sources']))) ?>
                    </span>
                </span>
                <?php endforeach; ?>
            </div>
        </div>
    <?php endforeach; ?>
</div>
