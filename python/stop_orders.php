<?php
/**
 * Stop Orders page — list stop loss / trailing stop orders with prices.
 * Expects: $orders, $total_orders, $account_filter, $account_types
 */
$orders = $data['orders'] ?? [];
$totalOrders = $data['total_orders'] ?? 0;
$accountFilter = $data['account_filter'] ?? 'all';
$accountTypes = $data['account_types'] ?? [];

// Calculate total portfolio stats for liquidity pool analysis
$totalMarketValue = array_sum(array_column($orders, 'market_value'));
$totalLiquidityPool = 0;
foreach ($orders as $o) {
    $effStop = $o['effective_stop_price'] ?? 0;
    $shares = $o['shares'] ?? 0;
    $currentPrice = $o['current_price'] ?? 0;
    // Liquidity pool: value at risk if stop is hit (shares × effective stop)
    $totalLiquidityPool += $shares * $effStop;
}
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
                <th title="Ticker symbol">Symbol</th>
                <th title="Account(s) holding this position">Account</th>
                <th class="r" title="Number of shares currently held">Shares</th>
                <th class="r" title="Average purchase price per share">Cost Basis</th>
                <th class="r" title="Most recent closing price">Current</th>
                <th class="r" title="Date/time of the current price data">Price Date</th>
                <th class="r" title="Market value = shares × current price">Mkt Value</th>
                <th class="r" title="Trailing stop percentage - locks in to highest price since purchase, resets if additional shares bought at lower price">Trailing %</th>
                <th class="r" title="Calculated trailing stop price (current price × (1 - trailing %))">Trailing Stop $</th>
                <th class="r" title="Static stop loss percentage - fixed threshold, does not auto-adjust">Stop Loss %</th>
                <th class="r" title="Calculated stop loss price (cost basis × (1 - stop loss %))">Stop Loss $</th>
                <th class="r" title="Average True Range (14-day) - volatility measure in dollars">ATR(14)</th>
                <th class="r" title="ATR multiplier used for stop calculation">ATR Mult</th>
                <th class="r" title="ATR-based stop (current price - multiplier× ATR). Resets daily based on current volatility.">ATR Stop $</th>
                <th class="r" title="Lowest of trailing stop, static stop loss, and ATR stop - the effective protection level">Effective Stop $</th>
                <th class="r" title="Liquidity pool: Value that would be sold if effective stop is hit (shares × effective stop price)">Liquidity Pool $</th>
                <th title="Stop status: Safe (far from trigger), Warning (near trigger), Breach (stop triggered)">Status</th>
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
                <td style="font-size:0.75em; color:var(--text3);"><?= htmlspecialchars($o['price_date'] ?? '—') ?><?= !empty($o['price_date']) ? ' ' . date('H:i', strtotime($o['price_date'])) : '' ?></td>
                <td class="r">$<?= number_format($o['market_value'], 2) ?></td>
                <td class="r"><?= number_format($o['trailing_stop_pct'] * 100, 1) ?>%</td>
                <td class="r">$<?= number_format($o['trailing_stop_price'], 2) ?></td>
                <td class="r"><?= number_format($o['stop_loss_pct'] * 100, 1) ?>%</td>
                <td class="r">$<?= number_format($o['stop_loss_price'], 2) ?></td>
                <td class="r"><?= $o['atr_14'] ? '$' . number_format($o['atr_14'], 2) : '—' ?></td>
                <td class="r"><?= number_format($o['atr_multiplier'], 1) ?>×</td>
                <td class="r"><?= $o['atr_stop_price'] ? '$' . number_format($o['atr_stop_price'], 2) : '—' ?></td>
                <td class="r"><strong style="color:<?= $stopColor ?>">$<?= number_format($o['effective_stop_price'], 2) ?></strong></td>
                <td class="r" style="color:var(--text3); font-size:0.85em;">
                    $<?= number_format($o['shares'] * $o['effective_stop_price'], 2) ?>
                </td>
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
        Total positions with stops: <?= $totalOrders ?> | 
        Portfolio Value: $<?= number_format($totalMarketValue, 2) ?> |
        Liquidity Pool (stop losses): $<?= number_format($totalLiquidityPool, 2) ?> 
        <span style="font-size:0.75em; color:var(--text3);">(value that would be sold if stops trigger)</span>
    </div>
</div>