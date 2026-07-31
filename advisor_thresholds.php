<?php
/** Advisor Risk Thresholds */
$t = $data['thresholds'] ?? [];
$readonly = $data['readonly'] ?? true;
?>
<div class="card">
    <div class="card-header">&#x1F6A1; Risk Thresholds</div>
    <p style="margin-bottom:16px;">
        These thresholds govern all paper/live trading decisions.
        Only the Board (human) can modify them.
    </p>

    <div class="stats-grid" style="margin-bottom:20px;">
        <div class="stat-card" style="background:rgba(0,0,0,0.15);">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;">Sharpe Minimum</div>
            <div style="font-size:1.8em;font-weight:700;"><?= htmlspecialchars($t['sharpe_minimum'] ?? '-') ?></div>
        </div>
        <div class="stat-card" style="background:rgba(104,211,145,0.1);">
            <div style="font-size:0.7em;color:var(--green);text-transform:uppercase;">Max Drawdown</div>
            <div style="font-size:1.8em;font-weight:700;color:var(--green);"><?= htmlspecialchars($t['max_drawdown_pct'] ?? '-') ?>%</div>
        </div>
        <div class="stat-card" style="background:rgba(246,224,94,0.1);">
            <div style="font-size:0.7em;color:var(--accent);text-transform:uppercase;">Mode</div>
            <div style="font-size:1.8em;font-weight:700;color:var(--accent);">
                <?= !empty($t['paper_trading_default']) ? 'Paper' : 'Live' ?>
            </div>
        </div>
    </div>

    <?php if (!empty($t['strategy_gates'])): ?>
    <h3 style="margin-top:0;">Strategy Gates</h3>
    <table>
        <thead><tr><th>Gate</th><th>Value</th></tr></thead>
        <tbody>
        <?php foreach ($t['strategy_gates'] as $k => $v): ?>
            <tr>
                <td><?= htmlspecialchars($k) ?></td>
                <td><?= htmlspecialchars(is_bool($v) ? ($v ? 'Yes' : 'No') : $v) ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>

    <?php if (!empty($t['sleeves'])): ?>
    <h3 style="margin-top:24px;">Sleeves</h3>
    <table>
        <thead><tr><th>Sleeve</th><th>Enabled</th><th>Max DD</th><th>Min Sharpe</th></tr></thead>
        <tbody>
        <?php foreach ($t['sleeves'] as $name => $s): ?>
            <tr>
                <td><?= htmlspecialchars($name) ?></td>
                <td><?= !empty($s['enabled']) ? '&#x2705;' : '&#x274C;' ?></td>
                <td><?= htmlspecialchars($s['max_drawdown_pct'] ?? '-') ?>%</td>
                <td><?= htmlspecialchars($s['sharpe_minimum'] ?? '-') ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>

    <p style="margin-top:16px;color:var(--text3);font-size:0.85em;">
        <?= htmlspecialchars($t['note'] ?? '') ?>
    </p>
</div>
