<div class="card" style="margin-top:12px;">
    <div class="card-header">VectorVest Safe Stock — 5-Point Checklist</div>
    <?php if (!empty($vectorvest) && !empty($vectorvest['checks'])): ?>
        <div style="display:flex; gap:20px; align-items:center; margin-bottom:12px;">
            <div style="font-size:2.5em; font-weight:700; color:<?= ($vectorvest['score'] ?? 0) >= 80 ? 'var(--green)' : (($vectorvest['score'] ?? 0) >= 60 ? 'var(--yellow)' : 'var(--red)') ?>">
                <?= $vectorvest['score'] ?? '—' ?>/100
            </div>
            <div>
                <strong><?= $vectorvest['pass_count'] ?? 0 ?>/<?= $vectorvest['max'] ?? 5 ?> criteria passed</strong>
                <?php if (!empty($vectorvest['note'])): ?>
                    <div style="font-size:0.8em;color:var(--text3);"><?= htmlspecialchars($vectorvest['note']) ?></div>
                <?php endif; ?>
            </div>
        </div>
        <div>
            <?php foreach ($vectorvest['checks'] as $key => $check): ?>
                <?php
                    $passed = $check['passed'] ?? null;
                    if ($passed === null):
                        $badgeBg = 'var(--text3)';
                        $color = 'var(--text3)';
                        $icon = '•';
                    elseif ($passed):
                        $badgeBg = 'var(--green-bg)';
                        $color = 'var(--green)';
                        $icon = '✓';
                    else:
                        $badgeBg = 'var(--red-bg)';
                        $color = 'var(--red)';
                        $icon = '✗';
                    endif;
                ?>
                <span style="display:inline-block; padding:2px 8px; margin:2px; border-radius:4px; font-size:0.8em; background:<?= $badgeBg ?>; color:<?= $color ?>;">
                    <?= $icon ?> <?= htmlspecialchars($check['label']) ?>: <?= htmlspecialchars($check['detail']) ?>
                </span>
            <?php endforeach; ?>
        </div>
    <?php else: ?>
        <p class="text-muted">VectorVest checklist not available for this symbol.</p>
    <?php endif; ?>
</div>
