<?php
$taxonomies = $data['taxonomies'] ?? [];
$assignments = $data['assignments'] ?? [];
$message = $data['message'] ?? '';
?>
<h1>Taxonomies</h1>

<?php if ($message): ?>
    <div class="alert info"><?= htmlspecialchars($message) ?></div>
<?php endif; ?>

<div class="card">
    <h3>Create Taxonomy</h3>
    <form method="post">
        <input type="hidden" name="action" value="create">
        <label>Name <input type="text" name="name" required></label>
        <label>Type
            <select name="type">
                <option value="custom">Custom</option>
                <option value="region">Region</option>
                <option value="sector">Sector</option>
                <option value="strategy">Strategy</option>
            </select>
        </label>
        <label>Parent ID <input type="number" name="parent_id" min="0" placeholder="optional"></label>
        <button type="submit">Create</button>
    </form>
</div>

<div class="card">
    <h3>Assign Symbol to Taxonomy</h3>
    <form method="post">
        <input type="hidden" name="action" value="assign">
        <label>Taxonomy
            <select name="taxonomy_id">
                <?php foreach ($taxonomies as $t): ?>
                    <option value="<?= (int)$t['id'] ?>"><?= htmlspecialchars($t['name']) ?> (<?= htmlspecialchars($t['type']) ?>)</option>
                <?php endforeach; ?>
            </select>
        </label>
        <label>Symbol <input type="text" name="symbol" required maxlength="12"></label>
        <label>Weight <input type="number" name="weight" value="0" step="0.01"></label>
        <label>Notes <input type="text" name="notes"></label>
        <button type="submit">Assign</button>
    </form>
</div>

<div class="card">
    <h3>Existing Assignments</h3>
    <table class="table">
        <thead><tr><th>Assignment</th><th>Taxonomy</th><th>Symbol</th><th>Weight</th><th>Notes</th><th>Action</th></tr></thead>
        <tbody>
        <?php foreach ($assignments as $a): ?>
            <tr>
                <td><?= (int)$a['id'] ?></td>
                <td><?= htmlspecialchars($a['taxonomy_name'] ?? '') ?></td>
                <td><?= htmlspecialchars($a['symbol']) ?></td>
                <td><?= htmlspecialchars($a['weight']) ?></td>
                <td><?= htmlspecialchars($a['notes']) ?></td>
                <td>
                    <form method="post" onsubmit="return confirm('Unassign?')">
                        <input type="hidden" name="action" value="unassign">
                        <input type="hidden" name="assignment_id" value="<?= (int)$a['id'] ?>">
                        <button type="submit" class="small">Unassign</button>
                    </form>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
