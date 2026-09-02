<?php /** @var array $data */ ?>
<div class="card">
    <div class="card-header">Optional Risk Rules — Knowledge Base Rules</div>
    <p class="text-muted" style="margin-bottom:12px;">
        Edit <code>strategy_rules.risk_rules.optional_rules</code> JSON per strategy bucket.
        Zero / empty = disabled. Save validates JSON before writing.
    </p>

    <?php if ($data['message'] ?? ''): ?>
        <div class="alert alert-success"><?php echo htmlspecialchars($data['message']); ?></div>
    <?php endif; ?>
    <?php if ($data['error'] ?? ''): ?>
        <div class="alert alert-error"><?php echo htmlspecialchars($data['error']); ?></div>
    <?php endif; ?>

    <form method="POST">
        <table>
            <thead>
                <tr>
                    <th>Strategy</th>
                    <th>Bucket</th>
                    <th style="width:55%">optional_rules JSON</th>
                    <th>Save</th>
                </tr>
            </thead>
            <tbody>
            <?php foreach (($data['rows'] ?? []) as $row): 
                $decoded = json_decode((string)($row['optional_rules'] ?? '{}'), true);
                if (!is_array($decoded)) { $decoded = []; }
                $json = json_encode($decoded, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
            ?>
                <tr>
                    <td><?php echo htmlspecialchars($row['strategy_name']); ?></td>
                    <td><?php echo htmlspecialchars($row['bucket']); ?></td>
                    <td>
                        <textarea name="optional_rules" rows="12" style="width:100%; font-family:monospace; font-size:0.85em;"><?php echo htmlspecialchars($json); ?></textarea>
                    </td>
                    <td style="vertical-align:top;">
                        <input type="hidden" name="strategy_name" value="<?php echo htmlspecialchars($row['strategy_name']); ?>">
                        <input type="hidden" name="bucket" value="<?php echo htmlspecialchars($row['bucket']); ?>">
                        <button type="submit" class="btn btn-sm">Save</button>
                    </td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </form>
</div>
