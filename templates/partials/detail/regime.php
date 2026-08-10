<?php if (!empty($regime['current_regime'])): ?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Markov Regime Analysis (20-day rolling return)</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start;">
        <div>
            <h4>Current Regime: 
                <span style="padding:4px 12px;border-radius:4px;font-weight:600;
                    <?= $regime['current_regime'] === 'Bull' ? 'background:#84bba1;color:#1a1a1a;' : 
                        ($regime['current_regime'] === 'Bear' ? 'background:#c57f86;color:#1a1a1a;' : 
                        'background:#a4abb7;color:#1a1a1a;') ?>">
                    <?= htmlspecialchars($regime['current_regime']) ?>
                </span>
            </h4>
            <p style="font-size:0.85em;color:var(--text3);margin-top:8px;">
                Market state detection using 5% rolling return threshold.
            </p>
        </div>
        <div>
            <h4 style="margin-top:0;">Stationary Distribution</h4>
            <table style="width:100%;font-size:0.9em;">
                <tr><td>Bear</td><td class="r"><?= ($regime['stationary_distribution']['Bear'] ?? 0) * 100 ?>%</td></tr>
                <tr><td>Sideways</td><td class="r"><?= ($regime['stationary_distribution']['Sideways'] ?? 0) * 100 ?>%</td></tr>
                <tr><td>Bull</td><td class="r"><?= ($regime['stationary_distribution']['Bull'] ?? 0) * 100 ?>%</td></tr>
            </table>
        </div>
    </div>
    
    <?php if (!empty($regime['transition_matrix'])): ?>
    <div style="margin-top:12px;">
        <h4 style="margin-bottom:8px;">Transition Matrix (3×3)</h4>
        <table style="width:100%;font-size:0.85em;border-collapse:collapse;">
            <thead>
                <tr>
                    <th></th>
                    <th class="c">Bear</th>
                    <th class="c">Sideways</th>
                    <th class="c">Bull</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach (['Bear', 'Sideways', 'Bull'] as $from): ?>
                <tr>
                    <td style="font-weight:600;"><?= $from ?></td>
                    <?php foreach (['Bear', 'Sideways', 'Bull'] as $to): ?>
                    <td class="c" style="background:<?= ($from === $to) ? 'rgba(128,128,128,0.2)' : 'rgba(255,255,255,0.05)' ?>;">
                        <?= round(($regime['transition_matrix'][$from][$to] ?? 0) * 100, 1) ?>%
                    </td>
                    <?php endforeach; ?>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
    <?php endif; ?>
</div>
<?php endif; ?>
