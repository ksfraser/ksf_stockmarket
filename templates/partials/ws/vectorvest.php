<?php
/**
 * VectorVest detail partial
 *
 * Expects: $vectorvest['points'] or legacy $vectorvest array
 */
$vv = $vectorvest ?? [];
if (empty($vv)) return;
?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">VectorVest 5-Point Checklist</div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value"><?= (int)($vv['points'] ?? 0) ?>/5</div>
            <div class="stat-label">Composite</div>
        </div>
        <?php if (!empty($vv['details'])): foreach ($vv['details'] as $k => $v): ?>
            <div class="stat-card">
                <div class="stat-value" style="color: <?= $v ? 'var(--green)' : 'var(--red)' ?>">
                    <?= $v ? '✓' : '✗' ?>
                </div>
                <div class="stat-label"><?= htmlspecialchars(ucwords(str_replace('_',' ', $k))) ?></div>
            </div>
        <?php endforeach; endif; ?>
    </div>
</div>
