<div class="card" style="margin-top:12px;">
    <div class="card-header">Buffett Quality Analysis</div>
    <?php if (!empty($buffettScore)): ?>
    <div style="display:flex; gap:20px; align-items:center; margin-bottom:12px;">
        <div style="font-size:2.5em; font-weight:700; color:<?= ($buffettScore['total'] ?? 0) >= 70 ? 'var(--green)' : (($buffettScore['total'] ?? 0) >= 50 ? 'var(--yellow)' : 'var(--red)') ?>"><?= $buffettScore['total'] ?? '—' ?>/100</div>
        <div>
            <?php foreach ($buffettScore['checks'] ?? [] as $check => $passed): ?>
                <span style="display:inline-block; padding:2px 8px; margin:2px; border-radius:4px; font-size:0.8em; background:<?= $passed ? 'var(--green-bg)' : 'var(--red-bg)' ?>; color:<?= $passed ? 'var(--green)' : 'var(--red)' ?>;">
                    <?= $passed ? '✓' : '✗' ?> <?= htmlspecialchars($check) ?>
                </span>
            <?php endforeach; ?>
        </div>
    </div>
    <?php else: ?>
    <p class="text-muted">Buffett analysis not yet generated for this symbol.</p>
    <?php endif; ?>
</div>
