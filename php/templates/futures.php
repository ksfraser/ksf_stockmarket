<?php
/**
 * Futures Contracts Page
 */
$futures = $data['futures'] ?? [];
?>
<div class="card">
    <div class="card-header">📊 Futures Contracts</div>
    <?php if (empty($futures)): ?>
        <p class="text-muted">No futures contracts found in symbol_master. Import symbols like ES, NQ, CL, GC.</p>
    <?php else: ?>
    <div class="overflow-x-auto">
    <table>
        <thead>
            <tr>
                <th>Contract</th>
                <th>Name</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($futures as $sym => $name): ?>
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