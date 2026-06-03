<?php
/**
 * Admin — Symbol & Exchange Management.
 * Expects: $data from SymbolAdminController::listSymbols()
 */
$data = $data ?? [];
$symbols   = $data['symbols']   ?? [];
$filter    = $data['filter']    ?? 'all';
$search    = $data['search']    ?? '';
$total_active   = $data['total_active']   ?? 0;
$total_inactive = $data['total_inactive'] ?? 0;
$total_all      = $data['total_all']      ?? 0;
?>

<div class="card">
    <div class="card-header">Symbol Management</div>

    <!-- Filter bar -->
    <form method="GET" class="search-bar" style="margin-bottom:12px">
        <input type="hidden" name="action" value="admin_symbols">
        <select name="filter" onchange="this.form.submit()">
            <option value="all"     <?= $filter === 'all'     ? 'selected' : '' ?>>All (<?= $total_all ?>)</option>
            <option value="active"  <?= $filter === 'active'  ? 'selected' : '' ?>>Active (<?= $total_active ?>)</option>
            <option value="inactive" <?= $filter === 'inactive' ? 'selected' : '' ?>>Inactive (<?= $total_inactive ?>)</option>
            <option value="no_exchange" <?= $filter === 'no_exchange' ? 'selected' : '' ?>>No Exchange</option>
        </select>
        <input type="text" name="search" value="<?= htmlspecialchars($search) ?>" placeholder="Search symbol or name...">
        <button type="submit" class="btn btn-sm">Filter</button>
    </form>

    <!-- Inline deactivate reason form (shown via JS) -->
    <div id="deactivate-form" style="display:none; margin-bottom:16px; padding:16px; background:rgba(0,0,0,0.2); border-radius:8px;">
        <form method="POST" action="?action=admin_symbols&subaction=deactivate">
            <input type="hidden" id="deactivate-symbol" name="symbol" value="">
            <label style="font-size:0.85em; color:var(--text3)">Reason for deactivating <strong id="deactivate-symbol-label"></strong>:</label>
            <textarea name="reason" rows="2" style="width:100%; margin:8px 0; background:rgba(0,0,0,0.2); border:1px solid var(--border); color:var(--text); padding:8px; border-radius:4px;" placeholder="e.g. Taken private, delisted, acquired, data unreliable..."></textarea>
            <p style="font-size:0.75em; color:var(--text3); margin-bottom:8px;">
                ℹ️ Inactive symbols keep all historical data for backtesting &amp; After Action Reports. Only new price fetching stops.
            </p>
            <button type="submit" class="btn btn-sm" style="background:var(--red)">Deactivate</button>
            <button type="button" class="btn btn-sm" onclick="document.getElementById('deactivate-form').style.display='none'">Cancel</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Exchange</th>
                <th>Sector</th>
                <th>Status</th>
                <th>Deactivated</th>
                <th>Reason</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($symbols as $s): ?>
            <tr>
                <td><strong><?= htmlspecialchars($s['symbol']) ?></strong></td>
                <td><?= htmlspecialchars($s['name'] ?? '—') ?></td>
                <td><?= htmlspecialchars($s['exchange'] ?? '<span class="text-muted">—</span>') ?></td>
                <td><?= htmlspecialchars($s['sector'] ?? '—') ?></td>
                <td>
                    <?php if ((int)$s['is_active'] === 1): ?>
                        <span style="color:var(--green)">&#x2713; Active</span>
                    <?php else: ?>
                        <span style="color:var(--red)">&#x2717; Inactive</span>
                    <?php endif; ?>
                </td>
                <td style="font-size:0.85em; color:var(--text3)">
                    <?= $s['deactivated_at'] ? date('Y-m-d', strtotime($s['deactivated_at'])) : '—' ?>
                </td>
                <td style="font-size:0.8em; max-width:200px; color:var(--text3)">
                    <?= htmlspecialchars(mb_strimwidth($s['deactivated_reason'] ?? '', 0, 60, '...')) ?>
                </td>
                <td>
                    <?php if ((int)$s['is_active'] === 1): ?>
                        <button class="btn btn-sm" style="background:var(--orange); padding:2px 8px; font-size:0.8em;"
                                onclick="showDeactivate('<?= htmlspecialchars($s['symbol']) ?>')">
                            Deactivate
                        </button>
                    <?php else: ?>
                        <a href="?action=admin_symbols&subaction=reactivate&symbol=<?= urlencode($s['symbol']) ?>"
                           class="btn btn-sm" style="padding:2px 8px; font-size:0.8em; background:var(--green)">
                            Reactivate
                        </a>
                    <?php endif; ?>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>

<!-- Exchange Mapping section -->
<?php
$exchangeCtrl = new SymbolAdminController();
$mappings = $exchangeCtrl->listExchangeMappings();
?>
<div class="card">
    <div class="card-header">Exchange Mapping <span style="font-size:0.7em; color:var(--text3); font-weight:normal">(user-editable symbol-to-exchange mappings)</span></div>
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Exchange</th>
                <th>Data Source</th>
                <th>Yahoo Ticker</th>
                <th>Notes</th>
                <th>Updated</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($appings as $m): ?>
            <tr>
                <td><strong><?= htmlspecialchars($m['symbol']) ?></strong></td>
                <td><?= htmlspecialchars($m['exchange']) ?></td>
                <td><?= htmlspecialchars($m['data_source']) ?></td>
                <td><?= htmlspecialchars($m['yahoo_ticker'] ?? $m['symbol']) ?></td>
                <td><?= htmlspecialchars($m['notes'] ?? '—') ?></td>
                <td style="font-size:0.85em"><?= date('Y-m-d H:i', strtotime($m['updated_at'])) ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>

    <!-- Add new mapping -->
    <h4 style="margin-top:20px; font-size:0.9em; color:var(--text2)">Add / Update Mapping</h4>
    <form method="POST" action="?action=admin_symbols&subaction=save_mapping" style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr 2fr auto; gap:8px; align-items:end">
        <div>
            <label style="font-size:0.75em; color:var(--text3)">Symbol</label>
            <input type="text" name="symbol" placeholder="e.g. KEG-UN.TO" style="width:100%">
        </div>
        <div>
            <label style="font-size:0.75em; color:var(--text3)">Exchange</label>
            <select name="exchange" style="width:100%">
                <option value="TSX">TSX</option>
                <option value="TSXV">TSXV</option>
                <option value="NYSE">NYSE</option>
                <option value="NASDAQ">NASDAQ</option>
                <option value="AMEX">AMEX</option>
                <option value="LSE">LSE</option>
                <option value="HKEX">HKEX</option>
                <option value="ASX">ASX</option>
                <option value="Other">Other</option>
            </select>
        </div>
        <div>
            <label style="font-size:0.75em; color:var(--text3)">Data Source</label>
            <select name="data_source" style="width:100%">
                <option value="yahoo">Yahoo Finance</option>
                <option value="alpha_vantage">Alpha Vantage</option>
                <option value="manual">Manual</option>
            </select>
        </div>
        <div>
            <label style="font-size:0.75em; color:var(--text3)">Yahoo Ticker</label>
            <input type="text" name="yahoo_ticker" placeholder="(override)" style="width:100%">
        </div>
        <div>
            <label style="font-size:0.75em; color:var(--text3)">Notes</label>
            <input type="text" name="notes" placeholder="Optional" style="width:100%">
        </div>
        <button type="submit" class="btn btn-sm">Save</button>
    </form>
</div>

<script>
function showDeactivate(symbol) {
    document.getElementById('deactivate-symbol').value = symbol;
    document.getElementById('deactivate-symbol-label').textContent = symbol;
    document.getElementById('deactivate-form').style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>
