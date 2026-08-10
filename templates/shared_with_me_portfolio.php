<?php
/** @var array $portfolioData */
$rows = $portfolioData['rows'] ?? [];
$totalCost = $portfolioData['total_cost'] ?? 0;
$totalValue = $portfolioData['total_value'] ?? 0;
$totalPnl = $portfolioData['total_pnl'] ?? 0;
$totalPnlPct = $portfolioData['total_pnl_pct'] ?? 0;
$cashBalance = $portfolioData['cash_balance'] ?? 0;
$netWorth = $portfolioData['net_worth'] ?? ($cashBalance + $totalValue);
?>

<div style="margin-bottom:10px;">
    <a href="?action=shared_with_me&user_id=<?php echo (int)($GLOBALS['selected_user_id'] ?? 0); ?>&tab=portfolio" class="btn btn-sm">Portfolio</a>
    <a href="?action=shared_with_me&user_id=<?php echo (int)($GLOBALS['selected_user_id'] ?? 0); ?>&tab=transactions" class="btn btn-sm">Transactions</a>
</div>

<div style="display:flex; gap:12px; margin-bottom:12px;">
    <div class="card" style="flex:1; padding:8px;">
        <strong>Cash</strong><br>
        $<?php echo number_format($cashBalance, 2); ?>
    </div>
    <div class="card" style="flex:1; padding:8px;">
        <strong>Value</strong><br>
        $<?php echo number_format($totalValue, 2); ?>
    </div>
    <div class="card" style="flex:1; padding:8px;">
        <strong>Net Worth</strong><br>
        $<?php echo number_format($netWorth, 2); ?>
    </div>
    <div class="card" style="flex:1; padding:8px;">
        <strong>P&L</strong><br>
        <span style="color:<?php echo $totalPnl >= 0 ? '#2ecc71' : '#e74c3c'; ?>">
            $<?php echo number_format($totalPnl, 2); ?> (<?php echo number_format($totalPnlPct, 2); ?>%)
        </span>
    </div>
</div>

<table class="table">
    <thead>
        <tr>
            <th>Symbol</th>
            <th>Account</th>
            <th>Shares</th>
            <th>Avg Cost</th>
            <th>Cost Total</th>
            <th>Price</th>
            <th>Value</th>
            <th>P&L</th>
            <th>Strategy</th>
        </tr>
    </thead>
    <tbody>
        <?php foreach ($rows as $r): ?>
            <?php $pnlClass = ($r['pnl'] ?? 0) >= 0 ? 'positive' : 'negative'; ?>
            <tr>
                <td><a href="?action=detail&symbol=<?php echo urlencode($r['symbol']); ?>"><?php echo htmlspecialchars($r['symbol']); ?></a></td>
                <td><?php echo htmlspecialchars($r['account_type'] ?? ''); ?></td>
                <td><?php echo htmlspecialchars($r['shares'] ?? 0); ?></td>
                <td>$<?php echo number_format($r['cost_basis'] ?? 0, 4); ?></td>
                <td>$<?php echo number_format($r['cost_total'] ?? 0, 2); ?></td>
                <td>$<?php echo number_format($r['current_price'] ?? 0, 2); ?></td>
                <td>$<?php echo number_format($r['current_value'] ?? 0, 2); ?></td>
                <td class="<?php echo $pnlClass; ?>">
                    $<?php echo number_format($r['pnl'] ?? 0, 2); ?>
                    (<?php echo number_format($r['pnl_pct'] ?? 0, 2); ?>%)
                </td>
                <td><?php echo htmlspecialchars($r['strategy'] ?? ''); ?></td>
            </tr>
        <?php endforeach; ?>
    </tbody>
</table>
