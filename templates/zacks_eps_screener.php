<?php
$rows = $data['rows'] ?? [];
$minChange = $data['min_change'] ?? 0.1;
$limit = $data['limit'] ?? 25;
$count = $data['count'] ?? 0;
$direction = $data['direction'] ?? 'bullish';
$isBearish = $direction === 'bearish';
?>
<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4CA; Zacks EPS Revision Screener — MIT Formula (<?= $isBearish ? 'Bearish' : 'Bullish' ?> Signal)</div>
    <p style="margin-bottom:12px;color:var(--text3);font-size:0.9em;">
        <?php if ($isBearish): ?>
        Symbols where <strong>consensus F1 EPS has declined</strong> over the past 4 weeks.
        When Zacks analysts cut estimates, it often signals institutions are distributing 
        (selling off) ahead of a price drop — the mirror image of the bullish signal.
        <?php else: ?>
        Symbols where <strong>consensus F1 EPS has risen</strong> over the past 4 weeks.
        Zacks analysts revise estimates nightly as they model future earnings — 
        <em>this is a leading indicator</em>: institutions accumulate quietly before price moves, 
        and estimate revisions leak out first.
        Higher 4-week delta = stronger institutional accumulation signal.
        <?php endif; ?>
    </p>
    <form method="get" action="?action=zacks_eps_screener" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end;">
        <input type="hidden" name="action" value="zacks_eps_screener">
        <label>Direction:
            <select name="direction" onchange="this.form.submit()" style="padding:4px;">
                <option value="bullish" <?= $isBearish ? '' : 'selected' ?>>Bullish (EPS rising)</option>
                <option value="bearish" <?= $isBearish ? 'selected' : '' ?>>Bearish (EPS falling)</option>
            </select>
        </label>
        <label>Min 4w Δ: <input type="number" name="min_change" value="<?= htmlspecialchars($minChange) ?>" step="0.01" min="0" style="width:80px;padding:4px;"></label>
        <label>Limit: <input type="number" name="limit" value="<?= htmlspecialchars($limit) ?>" step="1" min="1" max="100" style="width:80px;padding:4px;"></label>
        <button type="submit" class="btn btn-sm">Recompute</button>
    </form>
</div>

<div class="card">
    <div class="card-header">Top <?= (int)$count ?> symbols by 4-week F1 EPS revision (<?= $isBearish ? '≤ ' . htmlspecialchars($minChange) : '≥ ' . htmlspecialchars($minChange) ?>)</div>
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
            <?php
                $f1_4w = $r['zacks_eps_change_f1_4w'] !== null ? (float)$r['zacks_eps_change_f1_4w'] : null;
                $f1_1w = $r['zacks_eps_change_f1_1w'] !== null ? (float)$r['zacks_eps_change_f1_1w'] : null;
                $f2_4w = $r['zacks_eps_change_f2_4w'] !== null ? (float)$r['zacks_eps_change_f2_4w'] : null;
                $f2_1w = $r['zacks_eps_change_f2_1w'] !== null ? (float)$r['zacks_eps_change_f2_1w'] : null;
                $f1Color = $f1_4w !== null ? ($f1_4w > 0 ? 'var(--green)' : ($f1_4w < 0 ? 'var(--red)' : 'var(--text3)')) : 'var(--text3)';
                $f2Color = $f2_4w !== null ? ($f2_4w > 0 ? 'var(--green)' : ($f2_4w < 0 ? 'var(--red)' : 'var(--text3)')) : 'var(--text3)';
                $rowBg = $isBearish && $f1_4w !== null && $f1_4w < 0 ? 'rgba(252,129,129,0.05)' : ($isBearish ? '' : '');
            ?>
            <tr style="border-bottom:1px solid var(--border);<?= $rowBg ? 'background:' . $rowBg . ';' : '' ?>">
                <td style="padding:6px;"><?= $i + 1 ?></td>
                <td><strong><?= htmlspecialchars($r['symbol']) ?></strong></td>
                <td><?= htmlspecialchars($r['zacks_recommendation'] ?? '—') ?></td>
                <td><?= (int)($r['zacks_num_analysts'] ?? 0) ?></td>
                <td><?= htmlspecialchars($r['forward_eps'] ?? '—') ?></td>
                <td style="color:<?= $f1Color ?>">
                    <?= $f1_1w !== null ? ($f1_1w > 0 ? '+' : '') . number_format($f1_1w, 2) : '—' ?>
                </td>
                <td style="color:<?= $f1Color ?>;font-weight:600;">
                    <?= $f1_4w !== null ? ($f1_4w > 0 ? '+' : '') . number_format($f1_4w, 2) : '—' ?>
                </td>
                <td style="color:<?= $f2Color ?>">
                    <?= $f2_1w !== null ? ($f2_1w > 0 ? '+' : '') . number_format($f2_1w, 2) : '—' ?>
                </td>
                <td style="color:<?= $f2Color ?>;font-weight:600;">
                    <?= $f2_4w !== null ? ($f2_4w > 0 ? '+' : '') . number_format($f2_4w, 2) : '—' ?>
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
    <p style="padding:12px;color:var(--text3);">No symbols meet the threshold. Try adjusting the direction or lowering the minimum change.</p>
    <?php endif; ?>
</div>

<div class="card" style="margin-top:24px;border-left:4px solid <?= $isBearish ? 'var(--red)' : '#f0a500' ?>;">
    <p style="margin:0;font-size:0.85em;color:var(--text3);">
        <?php if ($isBearish): ?>
        <strong>How to read this (bearish):</strong> A negative 4-week F1 EPS revision means analysts have 
        cut their current-year earnings estimate over the past month. This often precedes price declines 
        because institutions distribute (sell) gradually before the crowd catches on. 
        The MIT/Zacks research treats this as the mirror image of the bullish signal — 
        <em>a leading indicator of institutional selling</em>.
        <?php else: ?>
        <strong>How to read this:</strong> The 4-week F1 EPS revision shows how much analysts have raised 
        their current-year earnings estimate over the past month. A rising estimate means analysts see 
        accelerating earnings — often because institutions are building positions quietly. 
        The MIT/Zacks research calls this the strongest forward indicator because it reflects 
        &quot;big money&quot; pricing in future value before the crowd catches on.
        <?php endif; ?>
    </p>
</div>
