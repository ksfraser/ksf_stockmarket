<?php
/**
 * Forex Pairs Page
 */
$pairs = $data['pairs'] ?? [];
?>
<div class="card">
    <div class="card-header">Forex Pairs</div>
    <?php if (empty($pairs)): ?>
        <p class="text-muted">No Forex pairs found in symbol_master. Import symbols like EUR.CAD, USD.CAD.</p>
    <?php else: ?>
    <div style="overflow-x:auto;">
    <table>
        <thead>
            <tr>
                <th>Pair</th>
                <th>Name</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($pairs as $sym => $name): ?>
            <tr>
                <td><a href="?action=detail&symbol=<?php echo urlencode($sym); ?>"><?php echo htmlspecialchars($sym); ?></a></td>
                <td><?php echo htmlspecialchars($name); ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    </div>
    <?php endif; ?>
</div>