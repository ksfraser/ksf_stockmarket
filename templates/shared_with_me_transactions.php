<?php
/** @var array $transactions */
$selectedUserId = $GLOBALS['selected_user_id'] ?? 0;
$tab = $GLOBALS['tab'] ?? 'portfolio';
?>

<div style="margin-bottom:10px;">
    <a href="?action=shared_with_me&user_id=<?php echo (int)$selectedUserId; ?>&tab=portfolio" class="btn btn-sm">Portfolio</a>
    <a href="?action=shared_with_me&user_id=<?php echo (int)$selectedUserId; ?>&tab=transactions" class="btn btn-sm">Transactions</a>
</div>

<p class="muted">Showing last <?php echo count($transactions); ?> transactions from this user.</p>

<table class="table">
    <thead>
        <tr>
            <th>Date</th>
            <th>Symbol</th>
            <th>Type</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Total</th>
            <th>Account</th>
            <th>Notes</th>
        </tr>
    </thead>
    <tbody>
        <?php foreach ($transactions as $t): ?>
            <tr>
                <td><?php echo htmlspecialchars($t['trade_date']); ?></td>
                <td><a href="?action=detail&symbol=<?php echo urlencode($t['symbol']); ?>"><?php echo htmlspecialchars($t['symbol']); ?></a></td>
                <td><?php echo htmlspecialchars($t['type']); ?></td>
                <td><?php echo htmlspecialchars($t['quantity']); ?></td>
                <td>$<?php echo number_format($t['price'] ?? 0, 2); ?></td>
                <td>$<?php echo number_format($t['total'] ?? 0, 2); ?></td>
                <td><?php echo htmlspecialchars($t['account_type'] ?? ''); ?></td>
                <td><?php echo htmlspecialchars($t['notes'] ?? ''); ?></td>
            </tr>
        <?php endforeach; ?>
    </tbody>
</table>
