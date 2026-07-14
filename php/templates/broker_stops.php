<?php
/**
 * Broker Stop Orders - Track stops you've actually placed with your broker.
 * Data: $stops — array of your active stop orders
 */
$stops = $data['stops'] ?? [];
$accountFilter = $data['account_filter'] ?? 'all';
$accountTypes = $data['account_types'] ?? [];
$message = $data['message'] ?? '';
$error = $data['error'] ?? '';
?>

<div class="card">
    <div class="card-header">&#x1F4E3; Broker Stop Orders</div>

    <?php if ($message): ?>
        <div style="background:rgba(104,211,145,0.15);border:1px solid var(--green);color:var(--green);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
            <?= htmlspecialchars($message) ?>
        </div>
    <?php endif; ?>
    <?php if ($error): ?>
        <div style="background:rgba(252,129,129,0.15);border:1px solid var(--red);color:var(--red);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
            <?= htmlspecialchars($error) ?>
        </div>
    <?php endif; ?>

    <!-- Place New Stop Form -->
    <div style="margin-bottom:24px;padding:16px;background:rgba(0,0,0,0.15);border-radius:8px;">
        <h4 style="margin:0 0 12px 0;font-size:0.9em;color:var(--text2);">Place New Stop Order</h4>
        <form method="POST" action="?action=broker_stops" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;align-items:end;">
            <div>
                <label style="font-size:0.75em;color:var(--text3);">Symbol</label>
                <input type="text" name="symbol" placeholder="RY.TO" required style="width:100%;">
            </div>
            <div>
                <label style="font-size:0.75em;color:var(--text3);">Account</label>
                <select name="account_type" style="width:100%;">
                    <option value="TFSA">TFSA</option>
                    <option value="RRSP">RRSP</option>
                    <option value="MARGIN">Margin</option>
                </select>
            </div>
            <div>
                <label style="font-size:0.75em;color:var(--text3);">Stop Type</label>
                <select name="stop_type" style="width:100%;">
                    <option value="trailing_pct">Trailing %</option>
                    <option value="trailing_price">Trailing $</option>
                    <option value="stop_loss">Stop Loss %</option>
                    <option value="stop_limit">Stop Limit $</option>
                </select>
            </div>
            <div>
                <label style="font-size:0.75em;color:var(--text3);">Value</label>
                <input type="text" name="stop_value" placeholder="10.00 or 55.50" required style="width:100%;">
            </div>
            <div>
                <label style="font-size:0.75em;color:var(--text3);">Sell Quantity</label>
                <select name="sell_mode" id="sellMode" onchange="document.getElementById('sellPct').disabled=this.value==='all';document.getElementById('sellQty').disabled=this.value==='all';" style="width:100%;">
                    <option value="all">All Shares</option>
                    <option value="portion">Portion</option>
                </select>
            </div>
            <div id="sellQty">
                <label style="font-size:0.75em;color:var(--text3);">Shares</label>
                <input type="number" name="shares" value="0" min="0" step="0.01" style="width:100%;">
            </div>
            <div id="sellPct">
                <label style="font-size:0.75em;color:var(--text3);">% of Position</label>
                <input type="number" name="sell_pct" value="100" min="1" max="100" step="1" style="width:100%;">
            </div>
            <button type="submit" name="action" value="place" class="btn btn-sm">Place Stop</button>
        </form>
    </div>

    <!-- Account Filter -->
    <form method="GET" class="search-bar" style="margin-bottom:12px">
        <input type="hidden" name="action" value="broker_stops">
        <label style="font-size:0.85em;color:var(--text3);margin-right:8px;">Account:</label>
        <select name="account" onchange="this.form.submit()">
            <option value="all" <?= $accountFilter === 'all' ? 'selected' : '' ?>>All Accounts</option>
            <?php foreach ($accountTypes as $at): ?>
                <option value="<?= htmlspecialchars($at) ?>" <?= $accountFilter === $at ? 'selected' : '' ?>><?= htmlspecialchars($at) ?></option>
            <?php endforeach; ?>
        </select>
    </form>

    <?php if (empty($stops)): ?>
        <p class="text-muted">No active broker stops. Place one above to track your actual orders.</p>
    <?php else: ?>
    <div style="overflow-x:auto;">
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Account</th>
                <th>Stop Type</th>
                <th class="r">Stop Value</th>
                <th class="r">Sell</th>
                <th class="r">Shares</th>
                <th class="r">Current $</th>
                <th class="r">Distance %</th>
                <th class="r">Placed</th>
                <th>Notes</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($stops as $s): $statusColor = match($s['status']) { 'active' => 'var(--green)', 'triggered' => 'var(--red)', default => 'var(--text3)' }; ?>
            <tr>
                <td><strong><a href="?action=detail&symbol=<?= urlencode($s['symbol']) ?>"><?= htmlspecialchars($s['symbol']) ?></a></strong></td>
                <td><?= htmlspecialchars($s['account_type']) ?></td>
                <td><?= htmlspecialchars(str_replace('_', ' ', $s['stop_type'])) ?></td>
                <td class="r"><?= number_format($s['stop_value'], 2) ?><?= in_array($s['stop_type'], ['trailing_pct', 'stop_loss']) ? '%' : '' ?></td>
                <td class="r"><?= strpos($s['notes'] ?? '', '[sell_pct=') !== false ? (int)filter_var($s['notes'] ?? '', FILTER_SANITIZE_NUMBER_INT) . '%' : '100%' ?></td>
                <td class="r"><?= $s['shares'] > 0 ? number_format($s['shares'], 2) : 'All' ?></td>
                <td class="r">$<?= number_format($s['current_price'] ?? 0, 2) ?></td>
                <td class="r" style="color:var(--<?= $s['distance_pct'] < 3 ? 'red' : ($s['distance_pct'] < 6 ? 'yellow' : 'green') ?>);">
                    <?= $s['distance_pct'] !== null ? number_format($s['distance_pct'], 1) . '%' : '—' ?>
                </td>
                <td style="font-size:0.85em;color:var(--text3)"><?= date('Y-m-d', strtotime($s['placed_at'])) ?></td>
                <td style="font-size:0.8em;color:var(--text2)"><?= htmlspecialchars($s['notes'] ?? '') ?></td>
                <td>
                    <?php if ($s['status'] === 'active'): ?>
                        <form method="POST" style="display:inline" onsubmit="return confirm('Mark this stop as triggered?');">
                            <input type="hidden" name="stop_id" value="<?= $s['id'] ?>">
                            <input type="hidden" name="action" value="trigger">
                            <button type="submit" class="btn btn-sm" style="background:var(--orange);padding:2px 6px;font-size:0.75em;">Trigger</button>
                        </form>
                    <?php endif; ?>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    </div>
    <?php endif; ?>

    <?php if (!empty($history)): ?>
    <div style="margin-top:24px;">
        <h3 style="margin-bottom:12px;color:var(--text3);">Historical Stops (triggered / cancelled / expired)</h3>
        <div style="overflow-x:auto;">
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Account</th>
                    <th>Stop Type</th>
                    <th class="r">Stop Value</th>
                    <th class="r">Sell</th>
                    <th class="r">Shares</th>
                    <th class="r">Placed</th>
                    <th class="r">Triggered / Closed</th>
                    <th>Status</th>
                    <th>Notes</th>
                </tr>
            </thead>
            <tbody>
            <?php foreach ($history as $s): ?>
                <tr>
                    <td><strong><a href="?action=detail&symbol=<?= urlencode($s['symbol']) ?>"><?= htmlspecialchars($s['symbol']) ?></a></strong></td>
                    <td><?= htmlspecialchars($s['account_type']) ?></td>
                    <td><?= htmlspecialchars(str_replace('_', ' ', $s['stop_type'])) ?></td>
                    <td class="r"><?= number_format($s['stop_value'], 2) ?><?= in_array($s['stop_type'], ['trailing_pct', 'stop_loss']) ? '%' : '' ?></td>
                    <td class="r"><?= strpos($s['notes'] ?? '', '[sell_pct=') !== false ? (int)filter_var($s['notes'] ?? '', FILTER_SANITIZE_NUMBER_INT) . '%' : '100%' ?></td>
                    <td class="r"><?= $s['shares'] > 0 ? number_format($s['shares'], 2) : 'All' ?></td>
                    <td style="font-size:0.85em;color:var(--text3)"><?= date('Y-m-d H:i', strtotime($s['placed_at'])) ?></td>
                    <td style="font-size:0.85em;color:var(--text3)"><?= date('Y-m-d H:i', strtotime($s['triggered_at'] ?? $s['placed_at'])) ?></td>
                    <td><span class="badge" style="background:var(--<?= $s['status'] === 'triggered' ? 'red' : 'yellow' ?>);color:#fff;font-size:0.8em;padding:2px 8px;border-radius:10px;"><?= htmlspecialchars($s['status']) ?></span></td>
                    <td style="font-size:0.8em;color:var(--text2)"><?= htmlspecialchars($s['notes'] ?? '') ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        </div>
    </div>
    <?php endif; ?>

    <div style="margin-top:12px;font-size:0.85em;color:var(--text3);">
        Showing <?= count($stops) ?> stop orders.
        <br><br>
        <strong>Stop Type Legend:</strong>
        <span title="Trailing percentage stop - broker trails stop below highest price since placement">Trailing %</span> |
        <span title="Trailing dollar stop - fixed price that follows the market">Trailing $</span> |
        <span title="Stop loss percentage - triggers if price drops by this percentage from current">Stop Loss %</span> |
        <span title="Stop limit - triggers only at or above this price level">Stop Limit $</span>
    </div>
</div>

<div style="display:flex;gap:12px;margin-top:20px;justify-content:center;">
    <a href="?action=stop_orders" class="btn">&larr; Suggested Stops</a>
    <a href="?action=portfolio" class="btn">Portfolio</a>
</div>