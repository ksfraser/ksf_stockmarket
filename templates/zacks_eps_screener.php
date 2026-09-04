<?php
$rows = $data['rows'] ?? [];
$minChange = $data['min_change'] ?? 0.1;
$limit = $data['limit'] ?? 25;
$count = $data['count'] ?? 0;
?>
<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4CA; Zacks EPS Revision Screener — MIT Formula (Leading Indicator)</div>
    <p style="margin-bottom:12px;color:var(--text3);font-size:0.9em;">
        Symbols where <strong>consensus F1 EPS has risen</strong> over the past 4 weeks.
        Zacks analysts revise estimates nightly as they model future earnings — 
        <em>this is a leading indicator</em>: institutions accumulate quietly before price moves, 
        and estimate revisions leak out first.
        Higher 4-week delta = stronger institutional accumulation signal.
    </p>
    <form method="get" action="?action=zacks_eps_screener" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end;">
        <label>Min 4w Δ: <input type="number" name="min_change" value="<?= htmlspecialchars($minChange) ?>" step="0.01" min="0" style="width:80px;padding:4px;"></label>
        <label>Limit: <input type="number" name="limit" value="<?= htmlspecialchars($limit) ?>" step="1" min="1" max="100" style="width:80px;padding:4px;"></label>
        <button type="submit" class="btn btn-sm">Recompute</button>
    </form>
</div>

<div class="card">
    <div class="card-header">Top <?= (int)$count ?> symbols by 4-week F1 EPS revision (≥ <?= htmlspecialchars($minChange) ?>)</div>
    <table style="width:100%;border-collapse:collapse;font-size:0.9em;">
        <thead>
            <tr style="border-bottom:1px solid var(--border);text-align:left;">
                <th style="padding:6px;">#</th>
                <th>Symbol</th>
                <th>Rec</th>
                <th>Analysts</th>
                <th>Fwd EPS</th>
                <th>F1 1w Δ</th>
                <th>F1 4w Δ</th>
                <th>F2 1w Δ</th>
                <th>F2 4w Δ</th>
                <th>Trailing P/E</th>
                <th>Forward P/E</th>
                <th>ROE</th>
                <th>Beta</th>
                <th>Industry</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($rows as $i => $r): ?>
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:6px;"><?= $i + 1 ?></td>
                <td><strong><?= htmlspecialchars($r['symbol']) ?></strong></td>
                <td><?= htmlspecialchars($r['zacks_recommendation'] ?? '—') ?></td>
                <td><?= (int)($r['zacks_num_analysts'] ?? 0) ?></td>
                <td><?= htmlspecialchars($r['forward_eps'] ?? '—') ?></td>
                <td style="color:<?= (!empty($r['zacks_eps_change_f1_1w']) && $r['zacks_eps_change_f1_1w'] > 0) ? 'var(--green)' : 'var(--text3)' ?>">
                    <?= $r['zacks_eps_change_f1_1w'] !== null ? number_format((float)$r['zacks_eps_change_f1_1w'], 2) : '—' ?>
                </td>
                <td style="color:var(--green);font-weight:600;">
                    <?= $r['zacks_eps_change_f1_4w'] !== null ? '+' . number_format((float)$r['zacks_eps_change_f1_4w'], 2) : '—' ?>
                </td>
                <td style="color:<?= (!empty($r['zacks_eps_change_f2_1w']) && $r['zacks_eps_change_f2_1w'] > 0) ? 'var(--green)' : 'var(--text3)' ?>">
                    <?= $r['zacks_eps_change_f2_1w'] !== null ? number_format((float)$r['zacks_eps_change_f2_1w'], 2) : '—' ?>
                </td>
                <td style="color:var(--green);font-weight:600;">
                    <?= $r['zacks_eps_change_f2_4w'] !== null ? '+' . number_format((float)$r['zacks_eps_change_f2_4w'], 2) : '—' ?>
                </td>
                <td><?= $r['trailing_pe'] !== null ? number_format((float)$r['trailing_pe'], 2) : '—' ?></td>
                <td><?= $r['forward_pe'] !== null ? number_format((float)$r['forward_pe'], 2) : '—' ?></td>
                <td><?= $r['roe'] !== null ? number_format((float)$r['roe'], 1) . '%' : '—' ?></td>
                <td><?= $r['beta'] !== null ? number_format((float)$r['beta'], 2) : '—' ?></td>
                <td><?= htmlspecialchars($r['industry'] ?? '—') ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php if (empty($rows)): ?>
    <p style="padding:12px;color:var(--text3);">No symbols meet the threshold. Try lowering the minimum change.</p>
    <?php endif; ?>
</div>

<div class="card" style="margin-top:24px;border-left:4px solid #f0a500;">
    <p style="margin:0;font-size:0.85em;color:var(--text3);">
        <strong>How to read this:</strong> The 4-week F1 EPS revision shows how much analysts have raised 
        their current-year earnings estimate over the past month. A rising estimate means analysts see 
        accelerating earnings — often because institutions are building positions quietly. 
        The MIT/Zacks research calls this the strongest forward indicator because it reflects 
        &quot;big money&quot; pricing in future value before the crowd catches on.
    </p>
</div>
