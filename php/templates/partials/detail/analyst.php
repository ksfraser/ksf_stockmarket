<div class="card" style="margin-top:12px;">
    <div class="card-header">Analyst Predictions</div>
    <?php if ($consensusPrice): ?>
    <div class="stats-grid" style="margin-bottom:12px;">
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($consensusPrice, 2) ?></div>
            <div class="stat-label">Consensus Target</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?= $consensusPrice > $close ? '↑' : '↓' ?> <?= number_format((($consensusPrice / $close) - 1) * 100, 1) ?>%</div>
            <div class="stat-label">Upside/Downside</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?= $numTargets ?></div>
            <div class="stat-label">Analysts</div>
        </div>
    </div>
    <?php endif; ?>
    <?php if (!empty($analystRatings)): ?>
    <table style="width:100%; font-size:0.9em;">
        <thead><tr><th>Date</th><th>Firm</th><th>Analyst</th><th>Rating</th><th>Action</th><th class="r">Target</th></tr></thead>
        <tbody>
        <?php foreach (array_slice($analystRatings, 0, 20) as $ar): ?>
            <tr>
                <td><?= $ar['date'] ?></td>
                <td><?= htmlspecialchars($ar['firm'] ?? '') ?></td>
                <td><?= htmlspecialchars($ar['analyst_name'] ?? '') ?></td>
                <td><?= htmlspecialchars($ar['rating'] ?? '') ?></td>
                <td><?= htmlspecialchars($ar['action'] ?? '') ?></td>
                <td class="r"><?= $ar['price_target'] ? '$' . number_format($ar['price_target'], 2) : '—' ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php else: ?>
    <p class="text-muted">No analyst data available yet. Data is being fetched.</p>
    <?php endif; ?>
</div>
