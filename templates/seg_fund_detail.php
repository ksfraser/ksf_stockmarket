<?php
/**
 * Segregated Fund detail template.
 * Expects: $data from SegFundsController::detail()
 */
$fund = $data['fund'] ?? null;
$prices = $data['prices'] ?? [];
$error = $data['error'] ?? null;

if (!$fund) {
    echo '<div class="card"><div class="card-body text-muted">Fund not found.</div></div>';
    return;
}
?>

<div class="card">
    <div class="card-header">
        <?= htmlspecialchars($fund['fund_name']) ?>
        <a href="?action=seg_funds" class="btn btn-sm" style="float:right">← Back to Funds</a>
    </div>

    <div class="fund-details">
        <div class="detail-grid">
            <div class="detail-item"><label>Carrier</label><span><?= htmlspecialchars($fund['carrier']) ?></span></div>
            <div class="detail-item"><label>Category</label><span><?= htmlspecialchars($fund['category'] ?? '—') ?></span></div>
            <div class="detail-item"><label>Series</label><span><?= htmlspecialchars($fund['series'] ?? '—') ?></span></div>
            <div class="detail-item"><label>MER</label><span><?= $fund['mer'] !== null ? number_format((float)$fund['mer'], 2) . '%' : '—' ?></span></div>
        </div>

        <h3 style="margin-top:20px">Returns</h3>
        <div class="detail-grid returns">
            <div class="detail-item"><label>1 Year</label><span class="<?= ($fund['return_1yr'] ?? 0) >= 0 ? 'text-green' : 'text-red' ?>"><?= $fund['return_1yr'] !== null ? number_format((float)$fund['return_1yr'], 1) . '%' : '—' ?></span></div>
            <div class="detail-item"><label>3 Year</label><span class="<?= ($fund['return_3yr'] ?? 0) >= 0 ? 'text-green' : 'text-red' ?>"><?= $fund['return_3yr'] !== null ? number_format((float)$fund['return_3yr'], 1) . '%' : '—' ?></span></div>
            <div class="detail-item"><label>5 Year</label><span class="<?= ($fund['return_5yr'] ?? 0) >= 0 ? 'text-green' : 'text-red' ?>"><?= $fund['return_5yr'] !== null ? number_format((float)$fund['return_5yr'], 1) . '%' : '—' ?></span></div>
            <div class="detail-item"><label>10 Year</label><span class="<?= ($fund['return_10yr'] ?? 0) >= 0 ? 'text-green' : 'text-red' ?>"><?= $fund['return_10yr'] !== null ? number_format((float)$fund['return_10yr'], 1) . '%' : '—' ?></span></div>
        </div>
    </div>
</div>

<?php if (!empty($prices)): ?>
<div class="card" style="margin-top:16px">
    <div class="card-header">NAV History</div>
    <table>
        <thead><tr><th>Date</th><th class="r">NAV</th></tr></thead>
        <tbody>
        <?php foreach ($prices as $p): ?>
            <tr>
                <td><?= htmlspecialchars($p['price_date']) ?></td>
                <td class="r"><?= $p['nav'] !== null ? number_format((float)$p['nav'], 4) : '—' ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>

<style>
.fund-details { padding: 16px 0; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.detail-item { background: #f8f9fa; padding: 12px; border-radius: 6px; }
.detail-item label { display: block; font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 4px; }
.detail-item span { font-size: 16px; font-weight: 600; }
.returns .detail-item { text-align: center; }
.text-green { color: #28a745; }
.text-red { color: #dc3545; }
</style>
