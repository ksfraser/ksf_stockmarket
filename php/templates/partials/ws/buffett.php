<?php
/**
 * WealthSystem Buffett 12-Tenets Detail
 *
 * Expects: $buffett['checks'], $buffett['total'], $buffett['max']
 * Each check: ['passed' => bool, 'detail' => string]
 */
if (empty($buffett_ws) && isset($buffett['checks'])) {
    $buffett_ws = $buffett;
}
if (empty($buffett_ws)):
?>
<p class="text-muted">Buffett analysis not yet generated for this symbol.</p>
<?php return; endif;

$total = (int)($buffett_ws['total'] ?? 0);
$max = (int)($buffett_ws['max'] ?? 100);
$pct = $max > 0 ? round(($total / max((int)$max, 1)) * 100, 1) : 0;
$color = $pct >= 70 ? 'var(--green)' : ($pct >= 50 ? 'var(--yellow)' : 'var(--red)');

$tenets = [
    'ROE > 15%'        => 'durable competitive advantage / high returns on capital',
    'D/E < 0.5'        => 'conservative balance sheet; low risk',
    'Margin > 10%'     => 'consistent profitability with pricing power',
    'Positive FCF'     => 'cash generation after capex; owner earnings',
    'Payout < 60%'     => 'retains earnings for reinvestment',
    'Rev Growth+'      => 'growing economic moat over time',
    'CR > 1.5'         => 'short-term liquidity',
    'Beta < 1.2'       => 'lower market risk vs index',
    'P/E < 25x'        => 'reasonable price relative to earnings',
    'Low CapEx Needs'  => 'asset-light or predictable reinvestment',
    'Simple Business'  => 'understandable with predictable future',
    'Honest Mgmt'      => 'transparent capital allocation and disclosures',
];
?>
<div style="display:flex; gap:20px; align-items:center; margin-bottom:12px;">
    <div style="font-size:2.5em; font-weight:700; color:<?= $color ?>">
        <?= $total ?>/<?= $max ?> <span style="font-size:0.4em; color:var(--text3);"><?= $pct ?>%</span>
    </div>
    <div style="font-size:0.9em; color:var(--text3);">
        Buffett Quality Score — 12 Tenets
    </div>
</div>
<div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:8px;">
    <?php foreach (array_slice($tenets, 0, 9) as $name => $why):
        $passed = !empty($buffett_ws['checks'][$name]) || false;
    ?>
        <span title="<?= htmlspecialchars($why) ?>" style="display:inline-block; padding:4px 10px; border-radius:4px; font-size:0.85em; background:<?= $passed ? 'var(--green-bg)' : 'var(--red-bg)' ?>; color:<?= $passed ? 'var(--green)' : 'var(--red)' ?>;">
            <?= $passed ? '✓' : '✗' ?> <?= htmlspecialchars($name) ?>
        </span>
    <?php endforeach; ?>
</div>
<div style="margin-top:10px; font-size:0.85em; color:var(--text3);">
    Tenets 10–12 depend on business-model clarity and management quality; evaluate manually in watchlist notes.
</div>
