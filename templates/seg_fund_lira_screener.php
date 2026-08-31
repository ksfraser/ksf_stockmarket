<?php
/**
 * LIRA/LRSP Seg-Fund Screener
 * Ranks equity seg funds for a retirement account. Defaults: 52yo, $200k,
 * 60% CA / 25% US / 15% INTL, 10-year runway.
 */
$ranked = $data['ranked'] ?? ['CA'=>[], 'US'=>[], 'INTL'=>[]];
$carriers = $data['carriers'] ?? [];
$age = $data['age'] ?? 52;
$principal = $data['principal'] ?? 200000;
$alloc = $data['allocation'] ?? ['CA'=>0.60, 'US'=>0.25, 'INTL'=>0.15];
$runway = $data['runway'] ?? 10;

function geo_label($k) {
    return ['CA'=>'🇨🇦 Canadian', 'US'=>'🇺🇸 US', 'INTL'=>'🌍 International'][$k] ?? $k;
}
function fmt_pct($v) {
    if ($v === null || $v === '') return '—';
    return number_format((float)$v, 1) . '%';
}
function fmt_mer($v) {
    if ($v === null || $v === '') return '—';
    return number_format((float)$v, 2) . '%';
}
function fmt_money($v) {
    return '$' . number_format((float)$v, 0);
}
?>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4CA; LIRA/LRSP Seg-Fund Screener</div>
    <p style="margin-bottom:12px;color:var(--text3);font-size:0.9em;">
        Equity seg funds ranked by 10-year risk-adjusted return (10y return ÷ max drawdown).
        Universe: LIRA/LRSP-eligible, primary series only, full 10-yr track record.
        Default allocation: 60% Canadian / 25% US / 15% International. Aggregation favors carriers
        that field <em>all three</em> geographies; carrier score = mean of top-fund risk-adjusted return.
    </p>
    <form method="get" action="?action=seg_fund_lira" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end;">
        <label>Age: <input type="number" name="age" value="<?= htmlspecialchars($age) ?>" min="18" max="100" style="width:80px;padding:4px;"></label>
        <label>Principal ($): <input type="number" name="principal" value="<?= htmlspecialchars($principal) ?>" min="1000" step="1000" style="width:120px;padding:4px;"></label>
        <button type="submit" class="btn btn-sm">Recompute</button>
        <span style="margin-left:auto;color:var(--text3);font-size:0.85em;">
            Allocated: <?= fmt_money($principal * $alloc['CA']) ?> CA,
            <?= fmt_money($principal * $alloc['US']) ?> US,
            <?= fmt_money($principal * $alloc['INTL']) ?> INTL
            · <?= $runway ?>-yr runway
        </span>
    </form>
</div>

<?php if (empty($carriers)): ?>
<div class="card"><p>No carriers field all three geographies with 10-year data. Check the per-bucket rankings below.</p></div>
<?php else: ?>
<div class="card" style="margin-bottom:24px;border-left:4px solid var(--accent);">
    <div class="card-header">&#x1F3C6; Recommended Carriers (all 3 geographies)</div>
    <table style="width:100%;border-collapse:collapse;font-size:0.9em;">
        <thead>
            <tr style="border-bottom:1px solid var(--border);text-align:left;">
                <th style="padding:6px;">#</th>
                <th>Carrier</th>
                <th>Avg RiskAdj</th>
                <th>Avg MER</th>
                <th>🇨🇦 Canadian Pick</th>
                <th>🇺🇸 US Pick</th>
                <th>🌍 Intl Pick</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($carriers as $i => $c): ?>
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:6px;"><?= $i + 1 ?></td>
                <td><strong><?= htmlspecialchars($c['carrier']) ?></strong></td>
                <td><?= number_format($c['avg_risk_adj'], 2) ?></td>
                <td><?= fmt_mer($c['avg_mer']) ?></td>
                <td><?= htmlspecialchars($c['ca']['fund_name']) ?> (10y <?= fmt_pct($c['ca']['ret_10y']) ?>)</td>
                <td><?= htmlspecialchars($c['us']['fund_name']) ?> (10y <?= fmt_pct($c['us']['ret_10y']) ?>)</td>
                <td><?= htmlspecialchars($c['intl']['fund_name']) ?> (10y <?= fmt_pct($c['intl']['ret_10y']) ?>)</td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <p style="margin-top:8px;color:var(--text3);font-size:0.85em;">
        RiskAdj = annualized 10y return ÷ max drawdown. Higher = better return-per-unit-of-pain.
        MER is weighted equally across the 3 picks (carrier-level blended MER).
    </p>
</div>
<?php endif; ?>

<?php foreach (['CA', 'US', 'INTL'] as $geo): ?>
<div class="card" style="margin-bottom:24px;">
    <div class="card-header"><?= geo_label($geo) ?> — Top 25 by Risk-Adjusted Return</div>
    <p style="color:var(--text3);font-size:0.85em;margin-bottom:8px;">
        Target: <?= fmt_money($principal * $alloc[$geo]) ?> (<?= ($alloc[$geo]*100) ?>% of <?= fmt_money($principal) ?>)
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:0.85em;">
        <thead>
            <tr style="border-bottom:1px solid var(--border);text-align:left;">
                <th style="padding:4px;">#</th>
                <th>Carrier</th>
                <th>Fund</th>
                <th>Series</th>
                <th>10y</th>
                <th>5y</th>
                <th>MaxDD</th>
                <th>Vol</th>
                <th>MER</th>
                <th>RiskAdj</th>
            </tr>
        </thead>
        <tbody>
        <?php $i = 0; foreach (array_slice($ranked[$geo], 0, 25) as $r): $i++; ?>
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:4px;"><?= $i ?></td>
                <td><?= htmlspecialchars($r['carrier']) ?></td>
                <td><?= htmlspecialchars($r['fund_name']) ?></td>
                <td style="color:var(--text3);"><?= htmlspecialchars($r['series_code'] ?? '') ?></td>
                <td><?= fmt_pct($r['ret_10y']) ?></td>
                <td><?= fmt_pct($r['ret_5y']) ?></td>
                <td><?= fmt_pct($r['max_drawdown']) ?></td>
                <td><?= htmlspecialchars($r['volatility_rating'] ?? '—') ?></td>
                <td><?= fmt_mer($r['mer']) ?></td>
                <td><strong><?= number_format($r['risk_adj'], 2) ?></strong></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endforeach; ?>

<div class="card" style="margin-top:24px;border-left:4px solid #f0a500;">
    <p style="margin:0;font-size:0.85em;color:var(--text3);">
        <strong>Caveats:</strong>
        Canada Life's "Global Growth Opportunities" series dominate the INTL top-10 but are <em>global</em>
        funds (multi-geo), not pure international. Use the carrier picks as a starting point — confirm
        the fund's actual mandate with the fund facts PDF before recommending. Stored
        <code>max_drawdown</code> is the analytic worst peak-to-trough, not the seg-fund guarantee floor;
        the guarantee at maturity is separate. Returns are <em>annualized</em> (fund-Facts convention) — do not re-annualize.
    </p>
</div>
