<?php
/**
 * Transactions page — filterable transaction history + record form + validation.
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
// Check for flash message from session (used after redirects from delete/edit)
$txnResult = $data['txn_result'] ?? ($_SESSION['flash_message'] ?? null);
if ($txnResult && isset($_SESSION['flash_message'])) {
    unset($_SESSION['flash_message']);
}
$txnForm = $data['txn_form'] ?? [];
$discrepancies = $data['holding_discrepancies'] ?? [];
?>

<!-- Record Transaction Form -->
<div class="card">
    <div class="card-header">&#x1F4DD; Record Transaction</div>
    <?php if ($txnResult): ?>
        <?php if ($txnResult['success']): ?>
            <div style="background:#1a3a1a;border:1px solid #2a5a2a;padding:10px 14px;border-radius:6px;margin-bottom:12px;color:#4a4;">
                &#x2705; <?php echo htmlspecialchars($txnResult['message'] ?? 'Transaction recorded.'); ?>
            </div>
        <?php else: ?>
            <div style="background:#3a1a1a;border:1px solid #5a2a2a;padding:10px 14px;border-radius:6px;margin-bottom:12px;color:#a44;">
                &#x274C; <?php echo htmlspecialchars(implode(' ', $txnResult['errors'] ?? ['Unknown error'])); ?>
            </div>
        <?php endif; ?>
    <?php endif; ?>
    <form method="POST" action="?action=transactions" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;">
        <input type="hidden" name="action" value="record">
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Symbol</label>
            <input type="text" name="symbol" value="<?php echo htmlspecialchars($txnForm['symbol'] ?? ''); ?>" placeholder="RY.TO" required style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Exchange</label>
            <select name="exchange" style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                <option value="">Auto-detect</option>
                <option value="TSX" <?php echo ($txnForm['exchange'] ?? '') === 'TSX' ? 'selected' : ''; ?>>TSX (.TO suffix)</option>
                <option value="NASDAQ" <?php echo ($txnForm['exchange'] ?? '') === 'NASDAQ' ? 'selected' : ''; ?>>NASDAQ (no suffix)</option>
                <option value="NYSE" <?php echo ($txnForm['exchange'] ?? '') === 'NYSE' ? 'selected' : ''; ?>>NYSE (no suffix)</option>
            </select>
        </div>
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Type</label>
            <select name="type" required style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                <option value="BUY" <?php echo ($txnForm['type'] ?? '') === 'BUY' ? 'selected' : ''; ?>>BUY</option>
                <option value="SELL" <?php echo ($txnForm['type'] ?? '') === 'SELL' ? 'selected' : ''; ?>>SELL</option>
                <option value="DIVIDEND" <?php echo ($txnForm['type'] ?? '') === 'DIVIDEND' ? 'selected' : ''; ?>>DIVIDEND</option>
                <option value="SPLIT" <?php echo ($txnForm['type'] ?? '') === 'SPLIT' ? 'selected' : ''; ?>>SPLIT</option>
            </select>
        </div>
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Date</label>
            <input type="date" name="trade_date" value="<?php echo htmlspecialchars($txnForm['trade_date'] ?? date('Y-m-d')); ?>" required style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Account</label>
            <select name="account_type" required style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                <option value="RRSP" <?php echo ($txnForm['account_type'] ?? '') === 'RRSP' ? 'selected' : ''; ?>>RRSP</option>
                <option value="TFSA" <?php echo ($txnForm['account_type'] ?? '') === 'TFSA' ? 'selected' : ''; ?>>TFSA</option>
                <option value="MARGIN" <?php echo ($txnForm['account_type'] ?? '') === 'MARGIN' ? 'selected' : ''; ?>>MARGIN</option>
            </select>
        </div>
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Quantity</label>
            <input type="number" name="quantity" step="0.0001" min="0.0001" value="<?php echo htmlspecialchars($txnForm['quantity'] ?? ''); ?>" placeholder="100" required style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Price</label>
            <input type="number" name="price" step="0.0001" min="0.0001" value="<?php echo htmlspecialchars($txnForm['price'] ?? ''); ?>" placeholder="150.00" style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Commission</label>
            <input type="number" name="commission" step="0.01" min="0" value="<?php echo htmlspecialchars($txnForm['commission'] ?? '9.95'); ?>" placeholder="9.95" style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>
        <div>
            <label style="font-size:0.8em;color:var(--text3);">Total (auto-calc if blank)</label>
            <input type="number" name="total" step="0.01" value="<?php echo htmlspecialchars($txnForm['total'] ?? ''); ?>" placeholder="auto" style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>
        <div style="grid-column:1/-1;">
            <label style="font-size:0.8em;color:var(--text3);">Notes</label>
            <input type="text" name="notes" value="<?php echo htmlspecialchars($txnForm['notes'] ?? ''); ?>" placeholder="Optional notes" style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>
        <div style="grid-column:1/-1;">
            <button type="submit" style="padding:8px 24px;background:var(--accent);color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:600;">&#x1F4BE; Record Transaction</button>
        </div>
    </form>
</div>

<!-- Holdings Validation -->
<?php if (!empty($discrepancies)): ?>
<div class="card" style="border-color:#5a4a1a;">
    <div class="card-header" style="color:#cc9900;">&#x26A0;&#xFE0F; Holdings / Transaction Mismatch</div>
    <p style="font-size:0.85em;color:var(--text3);margin-bottom:10px;">Portfolio holdings don't match the sum of BUY/SELL transactions. This usually means transactions are missing or holdings were imported from a statement without corresponding trade records.</p>
    <table>
        <thead><tr><th>Symbol</th><th>Account</th><th>Expected (txns)</th><th>Actual (portfolio)</th><th>Difference</th></tr></thead>
        <tbody>
        <?php foreach ($discrepancies as $d): ?>
            <tr>
                <td><strong><a href="?action=detail&symbol=<?php echo urlencode($d['symbol']); ?>" style="color:var(--text);text-decoration:none;"><?php echo htmlspecialchars($d['symbol']); ?></a></strong></td>
                <td><?php echo htmlspecialchars($d['account']); ?></td>
                <td class="r"><?php echo number_format($d['expected'], 2); ?></td>
                <td class="r"><?php echo number_format($d['actual'], 2); ?></td>
                <td class="r" style="color:<?php echo $d['diff'] > 0 ? '#4a4' : '#a44'; ?>;"><?php echo ($d['diff'] > 0 ? '+' : '') . number_format($d['diff'], 2); ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>

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
                <th class="c">Source</th>
                <th class="c">Actions</th>
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
                <td><a href="?action=detail&symbol=<?php echo urlencode($t['symbol'] ?? ''); ?>"><?php echo htmlspecialchars($t['symbol'] ?? ''); ?></a></td>
                <td class="c"><?php echo htmlspecialchars($t['account_type'] ?? ''); ?></td>
                <td class="r"><?php echo number_format($t['quantity'] ?? 0, 4); ?></td>
                <td class="r">$<?php echo number_format($t['price'] ?? 0, 4); ?></td>
                <td class="r">$<?php echo number_format($t['total'] ?? 0, 2); ?></td>
                <td class="r">$<?php echo number_format($t['commission'] ?? 0, 2); ?></td>
                <td style="font-size:0.82em;color:var(--text3);"><?php echo htmlspecialchars($t['notes'] ?? ''); ?></td>
                <td class="c" style="font-size:0.75em;color:var(--text3);">
                <?php 
                $srcFile = $t['source_file'] ?? '';
                if ($srcFile === 'manual_entry') echo 'Manual';
                elseif ($srcFile === '') echo 'Legacy';
                else echo 'Imported';
                ?>
            </td>
            <td class="c">
                <?php
                // Allow edit for ALL transactions
                // Allow delete for manual_entry OR empty/null source_file (legacy manual entries)
                $isManual = ($srcFile === 'manual_entry' || $srcFile === '');
                ?>
                <button type="button" onclick="openEditModal(<?php echo $t['id']; ?>, '<?php echo htmlspecialchars($t['trade_date'] ?? ''); ?>', <?php echo (float)($t['quantity'] ?? 0); ?>, <?php echo (float)($t['price'] ?? 0); ?>, <?php echo (float)($t['commission'] ?? 0); ?>, '<?php echo htmlspecialchars($t['notes'] ?? ''); ?>', '<?php echo htmlspecialchars($t['type'] ?? ''); ?>', '<?php echo htmlspecialchars($srcFile ?: 'manual'); ?>')" style="background:none;border:none;color:#cc9900;cursor:pointer;font-size:0.9em;" title="Edit">&#x270F;&#xFE0F; Edit</button>
                <?php if ($isManual): ?>
                    <form method="POST" style="display:inline;" onsubmit="return confirm('Delete this transaction? This will reverse its effect on your portfolio.');">
                        <input type="hidden" name="action" value="delete">
                        <input type="hidden" name="txn_id" value="<?php echo $t['id']; ?>">
                        <button type="submit" style="background:none;border:none;color:#a44;cursor:pointer;font-size:0.9em;" title="Delete">&#x1F5D1; Delete</button>
                    </form>
                <?php endif; ?>
            </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    </div>
    <?php endif; ?>
</div>

<!-- Edit Transaction Modal -->
<div id="editModal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000;align-items:center;justify-content:center;">
    <div style="background:var(--bg);padding:24px;border-radius:8px;max-width:500px;width:90%;border:1px solid var(--border);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <h3 style="margin:0;">&#x270F;&#xFE0F; Edit Transaction</h3>
            <button type="button" onclick="closeEditModal()" style="background:none;border:none;color:var(--text3);font-size:1.5em;cursor:pointer;">&times;</button>
        </div>
        <form method="POST" action="?action=transactions">
            <input type="hidden" name="action" value="edit">
            <input type="hidden" id="edit_txn_id" name="txn_id">
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.8em;color:var(--text3);margin-bottom:4px;">Date</label>
                <input type="date" id="edit_trade_date" name="trade_date" required style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.8em;color:var(--text3);margin-bottom:4px;">Quantity</label>
                <input type="number" id="edit_quantity" name="quantity" step="0.0001" min="0.0001" required style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.8em;color:var(--text3);margin-bottom:4px;">Price</label>
                <input type="number" id="edit_price" name="price" step="0.0001" min="0.0001" required style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.8em;color:var(--text3);margin-bottom:4px;">Commission</label>
                <input type="number" id="edit_commission" name="commission" step="0.01" min="0" style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            </div>
            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.8em;color:var(--text3);margin-bottom:4px;">Notes</label>
                <input type="text" id="edit_notes" name="notes" style="width:100%;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            </div>
            <div style="margin-bottom:8px;">
                <span id="edit_source_file" style="font-size:0.75em;color:var(--text3);"></span>
            </div>
            <div style="text-align:right;">
                <button type="button" onclick="closeEditModal()" style="padding:6px 16px;background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;cursor:pointer;margin-right:8px;">Cancel</button>
                <button type="submit" style="padding:6px 16px;background:var(--accent);color:#fff;border:none;border-radius:4px;cursor:pointer;">Save Changes</button>
            </div>
        </form>
    </div>
</div>

<script>
function openEditModal(txnId, tradeDate, quantity, price, commission, notes, txnType, sourceFile) {
    document.getElementById('edit_txn_id').value = txnId;
    document.getElementById('edit_trade_date').value = tradeDate;
    document.getElementById('edit_quantity').value = quantity;
    document.getElementById('edit_price').value = price;
    document.getElementById('edit_commission').value = commission || '';
    document.getElementById('edit_notes').value = notes;
    document.getElementById('edit_source_file').textContent = 'Source: ' + sourceFile + ' | Type: ' + txnType;
    document.getElementById('editModal').style.display = 'flex';
}
function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}
// Close modal on escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeEditModal();
});
</script>
