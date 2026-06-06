<?php
/**
 * Stop Orders page — list stop loss / trailing stop orders with prices.
 * Expects: $orders, $total_orders, $account_filter, $account_types
 */
$orders = $data['orders'] ?? [];
$totalOrders = $data['total_orders'] ?? 0;
$accountFilter = $data['account_filter'] ?? 'all';
$accountTypes = $data['account_types'] ?? [];
?>

<div class="card">
    <div class="card-header">Stop Loss / Trailing Stop Orders</div>

    <!-- Account filter -->
    <form method="GET" class="search-bar" style="margin-bottom:16px">
        <input type="hidden" name="action" value="stop_orders">
        <label style="font-size:0.85em; color:var(--text3); margin-right:8px">Account:</label>
        <select name="account" onchange="this.form.submit()">
            <option value="all" <?= $accountFilter === 'all' ? 'selected' : '' ?>>All Accounts</option>
            <?php foreach ($accountTypes as $at): ?>
                <option value="<?= htmlspecialchars($at) ?>" <?= $accountFilter === $at ? 'selected' : '' ?>>
                    <?= htmlspecialchars($at) ?>
                </option>
            <?php endforeach; ?>
        </select>
    </form>

    <?php if (empty($orders)): ?>
        <p class="text-muted">No holdings with stop orders found.</p>
    <?php else: ?>
    <div style="overflow-x:auto;">
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Account</th>
                <th class="r">Shares</th>
                <th class="r">Cost Basis</th>
                <th class="r">Current</th>
                <th class="r">Mkt Value</th>
                <th class="r">Trailing %</th>
                <th class="r">Trailing Stop $</th>
                <th class="r">Stop Loss %</th>
                <th class="r">Stop Loss $</th>
                <th class="r">ATR(14)</th>
                <th class="r">ATR Stop $</th>
                <th class="r">Effective Stop $</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($orders as $o):
            // Stop color: green=safe, yellow=warning, red=breach
            $stopColor = match($o['stop_status'] ?? 'safe') {
                'breach' => 'var(--red)',
                'warning' => 'var(--yellow)',
                default => 'var(--green)'
            };
            $stopIcon = match($o['stop_status'] ?? 'safe') {
                'breach', 'warning' => '&#x26A0;',
                default => '&#x2713;'
            };
        ?>
            <tr>
                <td><strong><a href="?action=detail&symbol=<?= urlencode($o['symbol']) ?>"><?= htmlspecialchars($o['symbol']) ?></a></strong></td>
                <td><?= htmlspecialchars(str_replace(',', '/', $o['accounts'])) ?></td>
                <td class="r"><?= number_format($o['shares'], 2) ?></td>
                <td class="r">$<?= number_format($o['cost_basis'], 2) ?></td>
                <td class="r">$<?= number_format($o['current_price'], 2) ?></td>
                <td class="r">$<?= number_format($o['market_value'], 2) ?></td>
                <td class="r"><?= number_format($o['trailing_stop_pct'] * 100, 1) ?>%</td>
                <td class="r">$<?= number_format($o['trailing_stop_price'], 2) ?></td>
                <td class="r"><?= number_format($o['stop_loss_pct'] * 100, 1) ?>%</td>
                <td class="r">$<?= number_format($o['stop_loss_price'], 2) ?></td>
                <td class="r"><?= $o['atr_14'] ? '$' . number_format($o['atr_14'], 2) : '—' ?></td>
                <td class="r"><?= $o['atr_stop_price'] ? '$' . number_format($o['atr_stop_price'], 2) : '—' ?></td>
                <td class="r"><strong style="color:<?= $stopColor ?>">$<?= number_format($o['effective_stop_price'], 2) ?></strong></td>
                <td style="color:<?= $stopColor ?>;">
                    <?= $stopIcon ?> <?= ucfirst($o['stop_status']) ?>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    </div>
    <?php endif; ?>

    <div style="margin-top:16px; font-size:0.85em; color:var(--text3);">
        Total positions with stops: <?= $totalOrders ?>
    </div>
</div>