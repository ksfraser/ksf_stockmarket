<?php
$result = $data['result'] ?? [];
$message = $data['message'] ?? '';
$get = $data['get'] ?? [];
?>
<h1>Rebalancing</h1>

<?php if ($message): ?>
    <div class="alert info"><?= htmlspecialchars($message) ?></div>
<?php endif; ?>

<div class="card">
    <h3>Create Rebalance Target</h3>
    <form method="post">
        <input type="hidden" name="action" value="create">
        <label>Name <input type="text" name="name" required></label>
        <label>Target Type
            <select name="target_type">
                <option value="taxonomy">Taxonomy</option>
                <option value="symbol">Symbol List</option>
            </select>
        </label>
        <label>Tolerance % <input type="number" name="tolerance_pct" value="5" step="0.5"></label>
        <label>Frequency
            <select name="rebalance_frequency">
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
            </select>
        </label>
        <fieldset>
            <legend>Target Allocations (symbol → %)</legend>
            <div id="allocations">
                <input type="text" name="target_allocations[SYMBOL]" placeholder="SYMBOL" value="">
                <input type="number" name="target_allocations_pct[]" placeholder="%" step="0.01" value="">
            </div>
        </fieldset>
        <button type="submit">Create Target</button>
    </form>
</div>

<?php if (isset($result['target'])): ?>
    <div class="card">
        <h3>Drift Analysis: <?= htmlspecialchars($result['target']['name']) ?></h3>
        <p>Needs rebalance: <strong><?= $result['needs_rebalance'] ? 'Yes' : 'No' ?></strong></p>
        <table class="table">
            <thead><tr><th>Symbol</th><th>Target %</th><th>Actual %</th><th>Drift</th><th>Action</th></tr></thead>
            <tbody>
            <?php foreach ($result['drifts'] ?? [] as $d): ?>
                <tr>
                    <td><?= htmlspecialchars($d['symbol']) ?></td>
                    <td><?= htmlspecialchars($d['target_pct']) ?>%</td>
                    <td><?= htmlspecialchars($d['actual_pct']) ?>%</td>
                    <td><?= htmlspecialchars($d['drift']) ?>%</td>
                    <td><?= $d['needs_rebalance'] ? '<span class="badge warn">Rebalance</span>' : 'OK' ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </div>
<?php endif; ?>

<?php if (isset($result['count'])): ?>
    <div class="card">
        <h3>Targets</h3>
        <p><?= (int)$result['count'] ?> targets</p>
        <pre><?= htmlspecialchars(json_encode($result['targets'] ?? [], JSON_PRETTY_PRINT)) ?></pre>
    </div>
<?php endif; ?>
