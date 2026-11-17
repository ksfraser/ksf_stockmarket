<?php
/**
 * Timing & Technical Strategies page.
 *
 * Data:
 *   $tested      — array of battle-tested strategies
 *   $development — strategies still being refined
 *   $totalCount
 */
$tested      = $data['tested'] ?? [];
$development = $data['development'] ?? [];
$totalCount  = $data['totalCount'] ?? 0;
?>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x23F0; Timing &amp; Technical Strategies <span style="float:right;font-size:0.7em;color:var(--text3);"><?= (int)$totalCount ?> strategies</span></div>
    <p>These strategies generate entry/excise signals. They can be combined with any stock selection '
        . 'strategy above. The ensemble approach (2/3 agreement) outperforms any individual signal.</p>
</div>

<style>
.strategy-table { width:100%; border-collapse:collapse; margin:8px 0; font-size:0.85em; }
.strategy-table th { background:rgba(0,0,0,0.2); padding:8px 12px; text-align:left; font-size:0.75em; text-transform:uppercase; color:var(--text3); }
.strategy-table td { padding:8px 12px; border-bottom:1px solid rgba(255,255,255,0.05); }
</style>

<?php if (!empty($tested)): ?>
<h2 style="color:var(--green);margin:20px 0 12px;">&#x2705; Battle Tested (Use in Production)</h2>
<?php foreach ($tested as $s):
    $statusColor = $s['status_color'] ?? 'green';
    $statusBg = match($statusColor) {
        'green' => 'rgba(104,211,145,0.2)',
        'yellow' => 'rgba(246,224,94,0.2)',
        'accent' => 'rgba(99,179,237,0.2)',
        default => 'rgba(99,179,237,0.2)',
    };
    $statusFg = match($statusColor) {
        'green' => 'var(--green)',
        'yellow' => 'var(--yellow)',
        'accent' => 'var(--accent)',
        default => 'var(--accent)',
    };
    $bt = $s['backtest'] ?? [];
?>
<div class="card" style="margin-bottom:16px;">
    <div class="card-header">
        <span style="background:<?= $statusBg ?>;color:<?= $statusFg ?>;padding:2px 10px;border-radius:12px;font-size:0.75em;">
            <?= htmlspecialchars($s['status']) ?>
        </span>
        <?= htmlspecialchars($s['name']) ?>
    </div>
    <p style="color:var(--text2);font-size:0.9em;"><?= htmlspecialchars($s['description']) ?></p>
    <?php if (!empty($s['criteria'])): ?>
    <div style="background:rgba(0,0,0,0.1);border-radius:var(--radius);padding:10px 14px;margin:10px 0;">
        <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;margin-bottom:4px;">Criteria</div>
        <ul style="margin:0 0 0 16px;font-size:0.85em;line-height:1.6;">
            <?php foreach ($s['criteria'] as $c): ?><li><?= htmlspecialchars($c) ?></li><?php endforeach; ?>
        </ul>
    </div>
    <?php endif; ?>
    <table class="strategy-table">
        <tr>
            <th>Win Rate</td>
            <th>Profit Factor</td>
            <th>Max DD</td>
            <th>Avg Win</td>
            <th>Avg Loss</td>
            <th>Trades</td>
        </tr>
        <tr>
            <td style="font-weight:700;"><?= htmlspecialchars($bt['win_rate'] ?? 'N/A') ?></td>
            <td style="font-weight:700;"><?= htmlspecialchars($bt['profit_factor'] ?? 'N/A') ?></td>
            <td style="font-weight:700;color:var(--red);"><?= htmlspecialchars($bt['max_drawdown'] ?? 'N/A') ?></td>
            <td style="color:var(--green);"><?= htmlspecialchars($bt['avg_win'] ?? 'N/A') ?></td>
            <td style="color:var(--red);"><?= htmlspecialchars($bt['avg_loss'] ?? 'N/A') ?></td>
            <td><?= isset($bt['total_trades']) ? number_format($bt['total_trades']) : 'N/A' ?></td>
        </tr>
    </table>
    <?php if (!empty($bt['implications'])): ?>
    <div style="background:rgba(0,0,0,0.1);border-left:3px solid var(--green);padding:8px 14px;margin-top:8px;font-size:0.85em;border-radius:0 var(--radius) var(--radius) 0;">
        <?= htmlspecialchars($bt['implications']) ?>
    </div>
    <?php endif; ?>
    <?php if (!empty($s['sources'])): ?>
    <div style="font-size:0.7em;color:var(--text3);margin-top:6px;">
        <?= htmlspecialchars(implode(' &middot; ', $s['sources'])) ?>
    </div>
    <?php endif; ?>
</div>
<?php endforeach; ?>
<?php endif; ?>

<?php if (!empty($development)): ?>
<h2 style="color:var(--yellow);margin:20px 0 12px;">&#x26A0;&#xFE0F; Development — Use with Caution</h2>
<?php foreach ($development as $s):
    $statusColor = $s['status_color'] ?? 'yellow';
    $bt = $s['backtest'] ?? [];
?>
<div class="card" style="margin-bottom:12px;border-left:3px solid var(--yellow);">
    <div class="card-header">
        <span style="background:rgba(246,224,94,0.2);color:var(--yellow);padding:2px 10px;border-radius:12px;font-size:0.75em;">
            <?= htmlspecialchars($s['status']) ?>
        </span>
        <?= htmlspecialchars($s['name']) ?>
    </div>
    <p style="color:var(--text2);font-size:0.85em;margin-bottom:8px;"><?= htmlspecialchars($s['description']) ?></p>
    <table class="strategy-table">
        <tr><th>Win Rate</th><th>PF</th><th>Max DD</th><th>Trades</th></tr>
        <tr>
            <td><?= htmlspecialchars($bt['win_rate'] ?? 'N/A') ?></td>
            <td><?= htmlspecialchars($bt['profit_factor'] ?? 'N/A') ?></td>
            <td style="color:var(--red);"><?= htmlspecialchars($bt['max_drawdown'] ?? 'N/A') ?></td>
            <td><?= isset($bt['total_trades']) ? number_format($bt['total_trades']) : 'N/A' ?></td>
        </tr>
    </table>
    <?php if (!empty($bt['implications'])): ?>
    <div style="font-size:0.8em;color:var(--text3);margin-top:6px;font-style:italic;"><?= htmlspecialchars($bt['implications']) ?></div>
    <?php endif; ?>
</div>
<?php endforeach; ?>
<?php endif; ?>

<div style="display:flex;gap:12px;margin-top:24px;justify-content:center;">
    <a href="?action=strategy_stock" class="btn">&#x1F4CA; Stock Selection Strategies</a>
    <a href="?action=strategy_money" class="btn">&#x1F4B0; Money &amp; Risk Management</a>
</div>
