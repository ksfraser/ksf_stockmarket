<div class="card" style="margin-top:12px;">
    <div class="card-header">Buffett Quality Analysis</div>
    <?php if (!empty($buffettScore)): ?>
    <div style="display:flex; gap:20px; align-items:center; margin-bottom:12px;">
        <div style="font-size:2.5em; font-weight:700; color:<?= ($buffettScore['total'] ?? 0) >= 70 ? 'var(--green)' : (($buffettScore['total'] ?? 0) >= 50 ? 'var(--yellow)' : 'var(--red)') ?>">
            <?= $buffettScore['total'] ?? '—' ?>/100
        </div>
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

    <?php
    $tenets = [];
    if (!empty($ws_fundamentals['checks'])) {
        $tenets = $ws_fundamentals['checks'];
    }
    ?>
    <?php if (!empty($tenets)): ?>
        <div style="margin-top:10px; border-top:1px solid var(--border); padding-top:10px;">
            <strong>12 Tenets Detail</strong>
            <table style="width:100%; margin-top:6px; border-collapse:collapse;">
                <thead><tr><th>Tenet</th><th>Passed</th><th>Detail</th></tr></thead>
                <tbody>
                    <?php foreach ($tenets as $idx => $tenet): ?>
                        <tr>
                            <td><?= htmlspecialchars($tenet['name'] ?? ('Tenet ' . ($idx + 1))) ?></td>
                            <td class="r"><?= !empty($tenet['passed']) ? '✓' : '✗' ?></td>
                            <td><?= htmlspecialchars($tenet['detail'] ?? '') ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    <?php endif; ?>
</div>
