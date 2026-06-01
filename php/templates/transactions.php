<?php
/**
 * Transactions page — filterable transaction history.
 */
$txns = $data['transactions'] ?? [];
$summary = $data['summary'] ?? [];
$accounts = $data['accounts'] ?? [];
$symbols = $data['symbols'] ?? [];
$note = $data['note'] ?? '';
$acf = $data['account_filter'] ?? '';
$sf = $data['symbol_filter'] ?? '';
$tf = $data['type_filter'] ?? '';
$df = $data['date_from'] ?? '';
$dt = $data['date_to'] ?? '';
?>

<?php if ($note): ?>
    <div class="card">
        <div class="card-header">Note</div>
        <p class="text-muted"><?php echo htmlspecialchars($note); ?></p>
    </div>
<?php endif; ?>

<!-- Filters -->
<div class="card">
    <div class="card-header">&#x1F50D; Filters</div>
    <form method="GET" action="">
        <input type="hidden" name="action" value="transactions">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;align-items:end;">
            <div>
                <label style="display:block;font-size:0.75em;color:var(--text3);margin-bottom:3px;text-transform:uppercase;">Account</label>
                <select name="account" style="width:100%;">
                    <option value="">All Accounts</option>
                    <?php foreach ($accounts as $a): ?>
                        <option value="<?php echo $a; ?>" <?php echo $acf === $a ? 'selected' : ''; ?>><?php echo $a; ?></option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div>
                <label style="display:block;font-size:0.75em;color:var(--text3);margin-bottom:3px;text-transform:uppercase;">Symbol</label>
                <select name="symbol" style="width:100%;">
                    <option value="">All Symbols</option>
                    <?php foreach ($symbols as $s): ?>
                        <option value="<?php echo $s; ?>" <?php echo $sf === $s ? 'selected' : ''; ?>><?php echo $s; ?></option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div>
                <label style="display:block;font-size:0.75em;color:var(--text3);margin-bottom:3px;text-transform:uppercase;">Type</label>
                <select name="type" style="width:100%;">
                    <option value="">All Types</option>
                    <option value="BUY" <?php echo $tf === 'BUY' ? 'selected' : ''; ?>>Buy</option>
                    <option value="SELL" <?php echo $tf === 'SELL' ? 'selected' : ''; ?>>Sell</option>
                    <option value="DIVIDEND" <?php echo $tf === 'DIVIDEND' ? 'selected' : ''; ?>>Dividend</option>
                    <option value="SPLIT" <?php echo $tf === 'SPLIT' ? 'selected' : ''; ?>>Split</option>
                </select>
            </div>
            <div>
                <label style="display:block;font-size:0.75em;color:var(--text3);margin-bottom:3px;text-transform:uppercase;">Date From</label>
                <input type="date" name="date_from" value="<?php echo htmlspecialchars($df); ?>" style="width:100%;">
            </div>
            <div>
                <label style="display:block;font-size:0.75em;color:var(--text3);margin-bottom:3px;text-transform:uppercase;">Date To</label>
                <input type="date" name="date_to" value="<?php echo htmlspecialchars($dt); ?>" style="width:100%;">
            </div>
            <div>
                <button type="submit" class="btn btn-sm" style="width:100%;">Apply</button>
            </div>
        </div>
    </form>
</div>

<!-- Summary -->
<div class="stats-grid">
    <?php if (!empty($summary)): ?>
    <div class="stat-card">
        <div class="stat-value"><?php echo number_format($summary['total_count'] ?? 0); ?></div>
        <div class="stat-label">Total Txns</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" style="color:var(--green);"><?php echo number_format($summary['buy_count'] ?? 0); ?></div>
        <div class="stat-label">Buys</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" style="color:var(--red);"><?php echo number_format($summary['sell_count'] ?? 0); ?></div>
        <div class="stat-label">Sells</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?php echo '$' . number_format($summary['total_dividends'] ?? 0, 2); ?></div>
        <div class="stat-label">Dividends</div>
    </div>
    <?php endif; ?>
</div>

<!-- Transactions Table -->
<div class="card">
    <div class="card-header">&#x1F4CB; Transaction History</div>
    <?php if (empty($txns)): ?>
        <p class="text-muted">No transactions found matching your filters.</p>
    <?php else: ?>
    <div style="overflow-x:auto;">
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Symbol</th>
                <th class="c">Account</th>
                <th class="r">Qty</th>
                <th class="r">Price</th>
                <th class="r">Total</th>
                <th class="r">Commission</th>
                <th>Notes</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($txns as $t):
            $rowClass = match($t['type'] ?? '') {
                'BUY' => 'green',
                'SELL' => 'red',
                'DIVIDEND' => '',
                default => ''
            };
        ?>
            <tr>
                <td><?php echo htmlspecialchars($t['trade_date'] ?? ''); ?></td>
                <td class="<?php echo $rowClass; ?>"><?php echo htmlspecialchars($t['type'] ?? ''); ?></td>
                <td><a href="?action=detail&symbol=<?php echo $t['symbol']; ?>"><?php echo htmlspecialchars($t['symbol']); ?></a></td>
                <td class="c"><?php echo htmlspecialchars($t['account_type'] ?? ''); ?></td>
                <td class="r"><?php echo number_format($t['quantity'] ?? 0, 4); ?></td>
                <td class="r">$<?php echo number_format($t['price'] ?? 0, 4); ?></td>
                <td class="r">$<?php echo number_format($t['total'] ?? 0, 2); ?></td>
                <td class="r">$<?php echo number_format($t['commission'] ?? 0, 2); ?></td>
                <td style="font-size:0.82em;color:var(--text3);"><?php echo htmlspecialchars($t['notes'] ?? ''); ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    </div>
    <?php endif; ?>
</div>
