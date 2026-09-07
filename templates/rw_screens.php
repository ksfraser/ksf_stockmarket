<?php
/**
 * Zacks RW Screens — data-driven screens imported from Research Wizard .und files.
 */
$screens = $data['screens'] ?? [];
$currentUser = $data['current_user'] ?? null;
?>
<div class="card">
    <div class="card-header">
        <h3>Zacks Research Wizard Screens</h3>
        <span class="text-muted"><?= count($screens); ?> stock screens imported from .und files</span>
    </div>
    <div class="card-body">
        <?php if (!$screens): ?>
            <p class="text-muted">No imported screens yet. Run:
                <code>php scripts/import_zacks_screens.php</code></p>
        <?php else: ?>
            <table class="table table-striped">
                <thead>
                <tr>
                    <th>Screen</th>
                    <th>Owner</th>
                    <th>Description</th>
                    <th>Updated</th>
                    <th></th>
                </tr>
                </thead>
                <tbody>
                <?php foreach ($screens as $s): ?>
                    <tr>
                        <td>
                            <?= htmlspecialchars($s['name']); ?>
                            <?php if ((int)($s['is_public'] ?? 0) === 1): ?>
                                <span class="badge">public</span>
                            <?php endif; ?>
                        </td>
                        <td><?= htmlspecialchars($s['owner'] ?? ''); ?></td>
                        <td><?= htmlspecialchars($s['description'] ?? ''); ?></td>
                        <td><?= htmlspecialchars($s['updated_at'] ?? ''); ?></td>
                        <td>
                            <a class="btn btn-sm"
                               href="?action=run_rw_screen&id=<?= (int)$s['id']; ?>">Run</a>
                        </td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
            <p class="text-muted">
                Screens are stored per-rule (field code, operator, value, timeframe) and
                evaluated live against the active symbol universe. Rules without a data
                source in this app are reported as skipped at run time.
            </p>
        <?php endif; ?>
    </div>
</div>