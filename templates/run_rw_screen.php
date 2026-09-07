<?php
/**
 * Zacks RW Screen — run result for one stored screen.
 */
$screen = $data['screen'] ?? null;
$error = $data['error'] ?? null;
$result = $data['result'] ?? null;
$source = $data['source'] ?? null;
?>
<div class="card">
    <div class="card-header">
        <h3>Run Zacks RW Screen</h3>
        <span class="text-muted"><a href="?action=rw_screens">&laquo; back</a></span>
    </div>
    <div class="card-body">
        <?php if ($error): ?>
            <p class="text-danger"><?= htmlspecialchars($error); ?></p>
        <?php elseif ($screen && $result): ?>
            <p>
                <strong><?= htmlspecialchars($screen['name']); ?></strong>
                — owned by <?= htmlspecialchars($screen['owner'] ?? ''); ?>
                <?php if ($source): ?>
                    <br><span class="text-muted">source: <?= htmlspecialchars($source); ?></span>
                <?php endif; ?>
            </p>
            <p>
                <?= (int)$result['rule_count']; ?> rule(s) evaluated over
                <?= (int)$result['universe_size']; ?> active symbols » matched
                <strong><?= count($result['symbols']); ?></strong>.
                Fully executed: <?= $result['fully_executed'] ? 'yes' : 'no'; ?>
            </p>

            <?php if (!empty($result['skipped'])): ?>
                <div class="card">
                    <div class="card-header"><h4>Skipped rules (no live data source)</h4></div>
                    <div class="card-body">
                        <ul>
                            <?php foreach ($result['skipped'] as $s): ?>
                                <li>
                                    <?= htmlspecialchars(($s['rule']['name'] ?? '') ?: 'rule');
                                    ?> — <?= htmlspecialchars($s['reason']); ?>
                                </li>
                            <?php endforeach; ?>
                        </ul>
                    </div>
                </div>
            <?php endif; ?>

            <?php if (empty($result['symbols'])): ?>
                <p class="text-muted">No symbols matched.</p>
            <?php else: ?>
                <table class="table table-striped">
                    <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Name</th>
                        <th>Exchange</th>
                        <th>Close</th>
                        <th>Price Date</th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php foreach ($result['symbols'] as $r): ?>
                        <tr>
                            <td><a href="?action=detail&symbol=<?= urlencode($r['symbol']); ?>">
                                    <?= htmlspecialchars($r['symbol']); ?></a></td>
                            <td><?= htmlspecialchars($r['name'] ?? ''); ?></td>
                            <td><?= htmlspecialchars($r['exchange'] ?? ''); ?></td>
                            <td><?= $r['close'] !== null ? number_format((float)$r['close'], 2) : '—'; ?></td>
                            <td><?= htmlspecialchars($r['price_date'] ?? ''); ?></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        <?php endif; ?>
    </div>
</div>