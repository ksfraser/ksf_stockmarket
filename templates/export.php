<?php
/**
 * Export page — Download transactions as OFX/QFX.
 */
$accounts = $data['accounts'] ?? [];
$error    = $data['error'] ?? '';
?>
<div class="card">
    <div class="card-header">&#x1F4E4; Export Transactions (OFX/QFX)</div>
    <p style="font-size:0.85em;color:var(--text3);margin-bottom:12px;">
        Download your transactions in OFX 2.2 format for import into FrontAccounting
        (via ksf_qfxparser), GnuCash, Quicken, or other financial software.
    </p>

    <?php if ($error): ?>
        <div style="background:#3a1a1a;border:1px solid #5a2a2a;padding:10px 14px;border-radius:6px;margin-bottom:12px;color:#a44;">
            &#x274C; <?php echo htmlspecialchars($error); ?>
        </div>
    <?php endif; ?>

    <form method="POST" action="?action=export">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
            <div>
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Account</label>
                <select name="account_type" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text1);border-radius:4px;">
                    <option value="ALL">All Accounts</option>
                    <?php foreach ($accounts as $a): ?>
                        <option value="<?php echo htmlspecialchars($a['account_type']); ?>">
                            <?php echo htmlspecialchars($a['account_type']); ?>
                            (<?php echo $a['cnt']; ?> txns, <?php echo $a['earliest']; ?> to <?php echo $a['latest']; ?>)
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div>
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Format</label>
                <select name="format" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text1);border-radius:4px;">
                    <option value="ofx">OFX 2.2 (XML)</option>
                    <option value="qfx">QFX (Quicken)</option>
                </select>
            </div>
            <div>
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Start Date</label>
                <input type="date" name="start_date" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text1);border-radius:4px;">
            </div>
            <div>
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">End Date</label>
                <input type="date" name="end_date" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text1);border-radius:4px;">
            </div>
        </div>

        <button type="submit" style="padding:10px 24px;background:var(--accent);color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:600;">
            &#x1F4E4; Download OFX
        </button>
    </form>
</div>

<!-- Account Summary -->
<div class="card">
    <div class="card-header">&#x1F4C8; Account Summary</div>
    <?php if (empty($accounts)): ?>
        <p class="text-muted">No transactions found. Upload some statements first.</p>
    <?php else: ?>
    <table style="font-size:0.85em;">
        <thead>
            <tr>
                <th>Account</th>
                <th>Transactions</th>
                <th>Date Range</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($accounts as $a): ?>
            <tr>
                <td><strong><?php echo htmlspecialchars($a['account_type']); ?></strong></td>
                <td class="r"><?php echo $a['cnt']; ?></td>
                <td style="color:var(--text3);"><?php echo $a['earliest']; ?> &mdash; <?php echo $a['latest']; ?></td>
                <td>
                    <a href="?action=export" onclick="document.querySelector('select[name=account_type]').value='<?php echo htmlspecialchars($a['account_type']); ?>'; this.closest('form').submit(); return false;" style="color:var(--accent);font-size:0.85em;">Export</a>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>
</div>
