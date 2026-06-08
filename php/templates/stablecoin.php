<?php
/**
 * Stablecoin Yields Page
 */
$positions = $data['positions'] ?? [];
?>
<div class="card">
    <div class="card-header">💰 Stablecoin Yields</div>
    <?php if (empty($positions)): ?>
        <p class="text-muted">No stablecoin positions tracked yet. Add positions via import or manual entry.</p>
    <?php else: ?>
    <div class="overflow-x-auto">
    <table>
        <thead>
            <tr>
                <th>Chain</th>
                <th>Protocol</th>
                <th>Pool</th>
                <th class="r">Shares</th>
                <th class="r">APY</th>
                <th>Entry Date</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($positions as $p): ?>
            <tr>
                <td><?php echo htmlspecialchars($p['chain'] ?? ''); ?></td>
                <td><?php echo htmlspecialchars($p['protocol'] ?? ''); ?></td>
                <td><?php echo htmlspecialchars($p['pool'] ?? ''); ?></td>
                <td class="r"><?php echo number_format($p['shares'] ?? 0, 2); ?></td>
                <td class="r" style="color:#4a4;"><?php echo number_format($p['apy'] ?? 0, 2); ?>%</td>
                <td><?php echo htmlspecialchars($p['entry_date'] ?? ''); ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    </div>
    <?php endif; ?>
</div>