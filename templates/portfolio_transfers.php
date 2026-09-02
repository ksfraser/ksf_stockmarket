<?php
/**
 * Portfolio Transfer Totals
 * Expects: accounts, totals, cost_grand, value_grand, transfers
 */
$accounts = $data['accounts'] ?? [];
$totals = $data['totals'] ?? [];
$costGrand = $data['cost_grand'] ?? 0;
$valueGrand = $data['value_grand'] ?? 0;
$transfers = $data['transfers'] ?? [];
?>
<div class="card">
    <div class="card-header">Transfer Totals</div>

    <div class="stats-grid" style="margin-bottom:20px">
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($costGrand, 2) ?></div>
            <div class="stat-label">Total Cost Basis</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($valueGrand, 2) ?></div>
            <div class="stat-label">Total Market Value</div>
        </div>
    </div>

    <table style="width:100%; margin-bottom:20px;">
        <thead>
            <tr><th>Account</th><th>Institution</th><th>Nickname</th><th>Registration</th><th class="r">Cost Basis</th><th class="r">Market Value</th></tr>
        </thead>
        <tbody>
            <?php foreach ($accounts as $a): ?>
                <?php $t = $totals[$a['id']] ?? []; ?>
                <tr>
                    <td><?= (int)$a['id'] ?></td>
                    <td><?= htmlspecialchars($a['institution']) ?></td>
                    <td><?= htmlspecialchars($a['account_nickname']) ?></td>
                    <td><?= htmlspecialchars($a['registration_type']) ?></td>
                    <td class="r">$<?= number_format((float)($t['cost_total'] ?? 0), 2) ?></td>
                    <td class="r">$<?= number_format((float)($t['value_total'] ?? 0), 2) ?></td>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <div class="card-header">Recent Transfers</div>
    <?php if (empty($transfers)): ?>
        <p class="text-muted">No transfer transactions recorded.</p>
    <?php else: ?>
        <table>
            <thead><tr><th>Date</th><th>Account</th><th>Symbol</th><th class="r">Qty</th><th class="r">Price</th><th class="r">Total</th><th>Notes</th></tr></thead>
            <tbody>
                <?php foreach ($transfers as $tr): ?>
                    <tr>
                        <td><?= htmlspecialchars($tr['date'] ?? '') ?></td>
                        <td><?= htmlspecialchars(($tr['institution'] ?? '') . ' / ' . ($tr['account_nickname'] ?? '')) ?></td>
                        <td><?= htmlspecialchars($tr['symbol'] ?? '') ?></td>
                        <td class="r"><?= number_format((float)($tr['quantity'] ?? 0), 2) ?></td>
                        <td class="r">$<?= number_format((float)($tr['price'] ?? 0), 4) ?></td>
                        <td class="r">$<?= number_format((float)($tr['total'] ?? 0), 2) ?></td>
                        <td><?= htmlspecialchars($tr['notes'] ?? '') ?></td>
                    </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    <?php endif; ?>
</div>
