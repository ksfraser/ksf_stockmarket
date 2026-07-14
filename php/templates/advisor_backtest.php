<?php
// advisor_backtest.php — top-level leaderboard

require_once __DIR__ . '/partials/helpers.php';
$summary = $data['summary'] ?? ['generated_at' => '', 'advisors' => []];
$advisors = $summary['advisors'] ?? [];
usort($advisors, function($a,$b){
    return ($b['final_value'] ?? 0) <=> ($a['final_value'] ?? 0);
});
?>
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">&#x1F3AF; Advisor Backtest Performance</div>
    <p style="margin-bottom:12px;">
        Each advisor started with $<?= number_format($summary['initial_capital'] ?? 100000, 2) ?>
        on <?= htmlspecialchars($summary['start'] ?? '2022-01-01') ?>
        and ran their strategy through <?= htmlspecialchars($summary['end'] ?? 'present') ?>.
        Click an advisor name to view their shared portfolio.
    </p>
    <div class="stats-grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:16px;">
        <div class="stat-card"><div class="stat-value"><?= count($advisors) ?></div><div class="stat-label">Advisors Tested</div></div>
        <div class="stat-card"><div class="stat-value" style="color:var(--green);"><?= $advisors ? number_format(array_sum(array_column($advisors,'total_return')) / count($advisors), 2) . '%' : '—' ?></div><div class="stat-label">Avg Return</div></div>
        <div class="stat-card"><div class="stat-value" style="color:var(--yellow);"><?= number_format(array_sum(array_column($advisors,'num_trades')), 0) ?></div><div class="stat-label">Total Trades</div></div>
        <div class="stat-card"><div class="stat-value"><?= htmlspecialchars($summary['generated_at'] ?? '') ?></div><div class="stat-label">Last Run</div></div>
    </div>
    <table>
        <thead>
            <tr>
                <th>#</th><th>Advisor</th><th>Strategy</th><th class="r">Start</th><th class="r">Current</th><th class="r">Return</th>
                <th class="r">Max DD</th><th class="r">Win Rate</th><th class="r">Trades</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($advisors as $i => $a): $return = $a['total_return'] ?? 0; $color = $return >= 0 ? 'green' : 'red'; ?>
            <tr>
                <td><?= $i+1 ?></td>
                <td><a href="?action=shared_with_me&user_id=<?= (int)($a['user_id'] ?? ($a['run_id'] ?? 0)) ?>"><?= htmlspecialchars($a['display_name'] ?? $a['slug']) ?></a>
                    <a href="?action=advisor_backtest_trades&run_id=<?= (int)($a['run_id'] ?? 0) ?>" style="font-size:0.75em;color:var(--text3);margin-left:8px;">[trades]</a>
                </td>
                <td><?= htmlspecialchars($a['strategy'] ?? '') ?></td>
                <td class="r">$<?= number_format($a['initial_capital'] ?? 0, 2) ?></td>
                <td class="r"><strong>$<?= number_format($a['final_value'] ?? 0, 2) ?></strong></td>
                <td class="r <?= $color ?>"><?= ($return >= 0 ? '+' : '') . number_format($return, 2) ?>%</td>
                <td class="r"><?= number_format($a['max_drawdown'] ?? 0, 2) ?>%</td>
                <td class="r"><?= number_format($a['win_rate'] ?? 0, 2) ?>%</td>
                <td class="r"><?= (int)($a['num_trades'] ?? 0) ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>

<?php if (!empty($advisors)): ?>
<div class="card" style="margin-top:24px;">
    <div class="card-header">🧩 Strategy Explanations</div>
    <div class="grid-2">
        <?php
        $seen = [];
        foreach ($advisors as $a) {
            $key = $a['strategy'] ?? '';
            if (in_array($key, $seen, true)) continue; $seen[] = $key;
        ?>
        <div style="padding:10px;background:rgba(0,0,0,0.15);border-radius:var(--radius);">
            <strong><?= htmlspecialchars($a['display_name'] ?? $key) ?></strong>
            <small style="color:var(--text3);"> — <?= htmlspecialchars($a['strategy'] ?? '') ?></small>
            <p style="font-size:0.88em;color:var(--text2);margin-top:6px;">
                Seeded with $<?= number_format($summary['initial_capital'] ?? 100000, 2) ?>
                on <?= htmlspecialchars($summary['start'] ?? '2022-01-01') ?>.
                Rebalances on schedule, equal-weighted up to 20 positions,
                1% max per holding, $9.95 commission per trade.
            </p>
        </div>
        <?php } ?>
    </div>
</div>
<?php endif; ?>

<div style="margin-top:20px;text-align:center;">
    <a class="btn" href="python/advisor_backtest.py">Run Backtest Now</a>
</div>
