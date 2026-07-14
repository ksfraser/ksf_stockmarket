<?php
// advisor_backtest_trades.php — trade list for one advisor backtest run
require_once __DIR__ . '/helpers.php';
$run = $data['run'] ?? null;
$trades = $data['trades'] ?? [];
if (!$run) {
    echo '<div class="card"><p>No backtest run selected.</p></div>';
    return;
}
$advisor = htmlspecialchars($run['strategy'] ?? '');
$runId = (int)($run['id'] ?? 0);
?>
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">🧾 Trades — <?= $advisor ?> (Run #<?= $runId ?>)</div>
    <p class="muted">
        Seeded $<?= number_format($run['initial_capital'] ?? 0, 2) ?>
        on <?= htmlspecialchars($run['start_date'] ?? '') ?>.
        Ended <?= htmlspecialchars($run['end_date'] ?? '') ?> with $<?= number_format($run['final_value'] ?? 0, 2) ?>.
        <?= (int)($run['num_trades'] ?? 0) ?> trades.
    </p>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Symbol</th>
                <th>Side</th>
                <th class="r">Price</th>
                <th class="r">Qty</th>
                <th class="r">Total Cost</th>
                <th>Trigger Reason</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($trades as $t): ?>
            <tr>
                <td><?= htmlspecialchars($t['trade_date'] ?? '') ?></td>
                <td><strong><?= htmlspecialchars($t['symbol'] ?? '') ?></strong></td>
                <td><?= htmlspecialchars($t['trade_type'] ?? '') ?></td>
                <td class="r">$<?= number_format($t['price'] ?? 0, 2) ?></td>
                <td class="r"><?= (int)($t['quantity'] ?? 0) ?></td>
                <td class="r">$<?= number_format(abs($t['total_cost'] ?? 0), 2) ?></td>
                <td style="font-size:0.88em;color:var(--text2);"><?= htmlspecialchars($t['signal_reasons'] ?? '') ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
