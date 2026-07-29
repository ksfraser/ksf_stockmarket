<?php
/**
 * WealthSystem Motley Fool 10 Criteria Detail
 *
 * Expects: $mf['checks'] | $motley['checks'] key=>bool
 */
$mf_ws = $mf_ws ?? $motley ?? [];
if (empty($mf_ws) || empty($mf_ws['checks'])):
?>
<p class="text-muted">Motley Fool evaluation not available yet.</p>
<?php return; endif;

$criteria = [
    'Market Cap > $2B' => 'Avoids micro-cap risk and ensures liquidity',
    'Strong Balance Sheet' => 'Low debt / good credit metrics',
    'Long-term Competitive Advantage' => 'Moat/brand/network effects',
    'Industry Leadership / Growth' => 'Leading market share or TAM expansion',
    'Consistent Profitability' => 'Multi-year positive earnings/cash flow',
    'Growth Accelerating' => 'Revenue/earnings inflection intact',
    'Reasonable Valuation' => 'P/E, P/FCF within fair range',
    'Management with Skin in Game' => 'Insider ownership / aligned incentives',
    'Dividend Growth or Buybacks' => 'Capital returned to shareholders',
    'Positive 1yr Momentum' => 'Price above key MAs, not deeply extended',
];

$passed = array_filter($mf_ws['checks'], fn($v) => $v);
$score = count($passed);
$max = count($criteria);
$pct = $max > 0 ? round((($score) / (int)$max) * 100, 1) : 0;
$color = $pct >= 70 ? 'var(--green)' : ($pct >= 50 ? 'var(--yellow)' : 'var(--red)');
?>
<div style="display:flex; gap:20px; align-items:center; margin-bottom:12px;">
    <div style="font-size:2.5em; font-weight:700; color:<?= $color ?>">
        <?= $score ?>/<?= $max ?> <span style="font-size:0.4em; color:var(--text3);"><?= $pct ?>%</span>
    </div>
    <div style="font-size:0.9em; color:var(--text3);">Motley Fool 10-Point Checklist</div>
</div>
<div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:8px;">
    <?php foreach ($criteria as $name => $why):
        $ok = !empty($mf_ws['checks'][$name]);
    ?>
        <span title="<?= htmlspecialchars($why) ?>" style="display:inline-block; padding:4px 10px; border-radius:4px; font-size:0.85em; background:<?= $ok ? 'var(--green-bg)' : 'var(--red-bg)' ?>; color:<?= $ok ? 'var(--green)' : 'var(--red)' ?>;">
            <?= $ok ? '✓' : '✗' ?> <?= htmlspecialchars($name) ?>
        </span>
    <?php endforeach; ?>
</div>
