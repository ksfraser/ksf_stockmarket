<?php
$result = $data['result'] ?? [];
$message = $data['message'] ?? '';
$get = $data['get'] ?? [];
$drift = $data['drift'] ?? null;
?>
<h1>Rebalancing</h1>

<?php if ($message): ?>
    <div class="alert info"><?= htmlspecialchars($message) ?></div>
<?php endif; ?>

<div class="grid-2">
    <div class="card">
        <h3>Create Rebalance Target</h3>
        <form method="post">
            <input type="hidden" name="action" value="create">
            <label>Name <input type="text" name="name" required></label>
            <label>Target Type
                <select name="target_type">
                    <option value="taxonomy">Taxonomy</option>
                    <option value="symbol">Symbol List</option>
                    <option value="strategy">Strategy</option>
                </select>
            </label>
            <label>Tolerance (%) <input type="number" name="tolerance_pct" value="5" min="0" max="20" step="0.5"></label>
            <label>Frequency
                <select name="rebalance_frequency">
                    <option value="monthly">Monthly</option>
                    <option value="quarterly">Quarterly</option>
                    <option value="weekly">Weekly</option>
                </select>
            </label>
            <label>Strategy name (optional) <input type="text" name="strategy_name"></label>
            <div>
                <h4>Target allocations</h4>
                <div id="alloc-rows">
                    <div class="alloc-row"><input name="symbols[]" placeholder="SYMBOL" style="width:110px"> <input name="target_allocations[]" placeholder="%" style="width:80px"> <input name="min_pct[]" placeholder="min%" style="width:70px"> <input name="max_pct[]" placeholder="max%" style="width:70px"></div>
                </div>
                <button type="button" onclick="addAllocRow()">+ Add row</button>
            </div>
            <button type="submit" class="primary">Create target</button>
        </form>
    </div>

    <div class="card">
        <h3>Active Targets</h3>
        <?php if (empty($result)): ?>
            <p class="text-muted">No targets found. Create one or load existing.</p>
        <?php else: ?>
            <table>
                <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Tolerance</th><th>Action</th></tr></thead>
                <tbody>
                <?php foreach (($result['targets'] ?? $result) as $t): ?>
                    <tr>
                        <td><?= htmlspecialchars($t['name'] ?? $t['target_name'] ?? '—') ?></td>
                        <td><?= htmlspecialchars($t['target_type'] ?? '—') ?></td>
                        <td><?= htmlspecialchars($t['active'] ? 'active' : 'paused') ?></td>
                        <td class="r"><?= htmlspecialchars($t['tolerance_pct'] ?? '5') ?>%</td>
                        <td>
                            <form method="post" style="display:inline">
                                <input type="hidden" name="action" value="toggle">
                                <input type="hidden" name="target_id" value="<?= (int)($t['id'] ?? $t['target_id']) ?>">
                                <button type="submit">Toggle</button>
                            </form>
                            <form method="post" style="display:inline" onsubmit="return confirm('Delete?')">
                                <input type="hidden" name="action" value="delete">
                                <input type="hidden" name="target_id" value="<?= (int)($t['id'] ?? $t['target_id']) ?>">
                                <button type="submit" class="danger">Delete</button>
                            </form>
                        </td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        <?php endif; ?>
    </div>
</div>

<?php if ($drift): ?>
<div class="card" style="margin-top:16px">
    <h3>Drift / Suggested trades</h3>
    <table>
        <thead><tr><th>Symbol</th><th class="r">Current%</th><th class="r">Target%</th><th class="r">Drift%</th><th>Action</th></tr></thead>
        <tbody>
        <?php foreach ($drift as $row): ?>
            <tr>
                <td><?= htmlspecialchars($row['symbol'] ?? $row['taxonomy_name'] ?? '—') ?></td>
                <td class="r"><?= number_format(($row['current_pct'] ?? 0) * 100, 1) ?>%</td>
                <td class="r"><?= number_format(($row['target_pct'] ?? 0) * 100, 1) ?>%</td>
                <td class="r"><?= number_format(($row['drift_pct'] ?? 0) * 100, 1) ?>%</td>
                <td><?= htmlspecialchars($row['action'] ?? 'hold') ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>

<script>
function addAllocRow() {
  const c = document.getElementById('alloc-rows');
  const row = document.createElement('div');
  row.className = 'alloc-row';
  row.innerHTML = `<input name="symbols[]" placeholder="SYMBOL" style="width:110px"> <input name="target_allocations[]" placeholder="%" style="width:80px"> <input name="min_pct[]" placeholder="min%" style="width:70px"> <input name="max_pct[]" placeholder="max%" style="width:70px">`;
  c.appendChild(row);
}
</script>
<style>
.alloc-row { display:flex; gap:8px; margin-bottom:6px; }
</style>
