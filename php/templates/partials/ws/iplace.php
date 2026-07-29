<?php
/**
 * IPlace scores detail partial
 *
 * Expects: $iplace = ['composite_score'=>..., 'recommendation'=>..., 'criteria_json'=>...]
 */
$ip = $iplace ?? [];
if (empty($ip)) return;
?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">InvestorPlace (IPlace) Score</div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value"><?= htmlspecialchars($ip['composite_score'] ?? '—') ?></div>
            <div class="stat-label">Composite Score</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: var(--accent);">
                <?= htmlspecialchars($ip['recommendation'] ?? '—') ?>
            </div>
            <div class="stat-label">Recommendation</div>
        </div>
    </div>
    <?php if (!empty($ip['criteria_json'])): ?>
        <?php $criteria = json_decode($ip['criteria_json'], true) ?: []; ?>
        <?php if (!empty($criteria)): ?>
            <div style="margin-top:10px;">
                <strong>Criteria</strong>
                <table style="width:100%;margin-top:6px;border-collapse:collapse;">
                    <thead><tr><th>Criterion</th><th>Score</th></tr></thead>
                    <tbody>
                        <?php foreach ($criteria as $k => $v): ?>
                            <tr>
                                <td><?= htmlspecialchars(ucwords(str_replace('_',' ', $k))) ?></td>
                                <td class="r"><?= htmlspecialchars($v) ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    <?php endif; ?>
</div>
