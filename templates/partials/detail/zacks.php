<div class="card" style="margin-top:12px;">
    <div class="card-header">Zacks-Style Composite Score</div>
    <?php if (!empty($zacksScore) && !empty($zacksScore['rank'])): ?>
        <div style="display:flex; gap:20px; align-items:center; margin-bottom:12px; flex-wrap:wrap;">
            <div style="font-size:2.5em; font-weight:700; color:<?= ($zacksScore['rank'] ?? 0) <= 2 ? 'var(--green)' : (($zacksScore['rank'] ?? 0) == 3 ? 'var(--yellow)' : 'var(--red)') ?>">
                <?= $zacksScore['rank_text'] ?? '—' ?>
                <div style="font-size:0.35em; color:var(--text3);">Rank <?= $zacksScore['rank'] ?? '—' ?>/5</div>
            </div>
            <div>
                <div style="font-size:1.2em; font-weight:700;">Composite <?= $zacksScore['composite'] ?? '—' ?>/100</div>
                <div style="font-size:0.9em;">
                    VGM: <?= $zacksScore['vgm_grade'] ?? '—' ?> (<?= $zacksScore['vgm_pct'] ?? '—' ?>%)
                </div>
            </div>
        </div>
        <div class="stats-grid" style="margin-bottom:12px;">
            <div class="stat-card">
                <div class="stat-value"><?= $zacksScore['value_grade'] ?? '—' ?></div>
                <div class="stat-label">Value (<?= $zacksScore['value_pct'] ?? '—' ?>%)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value"><?= $zacksScore['growth_grade'] ?? '—' ?></div>
                <div class="stat-label">Growth (<?= $zacksScore['growth_pct'] ?? '—' ?>%)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value"><?= $zacksScore['momentum_grade'] ?? '—' ?></div>
                <div class="stat-label">Momentum (<?= $zacksScore['momentum_pct'] ?? '—' ?>%)</div>
            </div>
        </div>
        <div>
            <?php foreach (($zacksScore['checks'] ?? []) as $check => $passed): ?>
                <span style="display:inline-block; padding:2px 8px; margin:2px; border-radius:4px; font-size:0.8em; background:<?= $passed ? 'var(--green-bg)' : 'var(--red-bg)' ?>; color:<?= $passed ? 'var(--green)' : 'var(--red)' ?>;">
                    <?= $passed ? '✓' : '✗' ?> <?= htmlspecialchars($check) ?>
                </span>
            <?php endforeach; ?>
        </div>
    <?php else: ?>
        <p class="text-muted">Zacks score not yet available for this symbol.</p>
    <?php endif; ?>
</div>
