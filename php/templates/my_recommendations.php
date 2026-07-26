<?php
require_once __DIR__ . '/partials/helpers.php';
$recs = $data['recommendations'] ?? [];
?>
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">📬 My Advisor Recommendations</div>
    <p class="muted">Latest BUY/SELL/HOLD recommendations from your hired advisors.</p>

<?php if (!$recs): ?>
    <p>No recommendations yet. <a href="?action=hire_advisors">Hire an advisor</a> to get started.</p>
<?php else: ?>
    <table style="width:100%;">
        <thead>
            <tr>
                <th>Date</th><th>Advisor</th><th>Symbol</th><th>Action</th>
                <th class="r">Price</th><th class="r">Max</th><th class="r">Stop</th>
                <th>Notes</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($recs as $r): ?>
            <tr>
                <td><?= htmlspecialchars($r['recommended_at'] ?? '') ?></td>
                <td><strong><?= htmlspecialchars($r['advisor_name'] ?? '') ?></strong><br>
                    <small class="muted"><?= htmlspecialchars($r['advisor_slug'] ?? '') ?></small>
                </td>
                <td><a href="?action=detail&symbol=<?= urlencode($r['symbol']) ?>"><?= htmlspecialchars($r['symbol']) ?></a></td>
                <td><?= htmlspecialchars($r['action'] ?? '') ?></td>
                <td class="r">$<?= number_format((float)($r['price'] ?? 0), 2) ?></td>
                <td class="r"><?= $r['max_price'] ? '$' . number_format((float)$r['max_price'], 2) : '—' ?></td>
                <td class="r"><?= $r['stop_limit'] ? '$' . number_format((float)$r['stop_limit'], 2) : '—' ?></td>
                <td style="font-size:0.85em;color:var(--text2);"><?= nl2br(htmlspecialchars($r['notes'] ?? '')) ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
<?php endif; ?>
</div>

<div style="margin-top:16px;text-align:center;">
    <a class="btn" href="?action=hire_advisors">Hire Advisors</a>
    <a class="btn" href="?action=advisor_preferences" style="background:var(--bg2);color:var(--text);margin-left:8px;">Notification Settings</a>
    <a class="btn" href="?action=my_advisors" style="background:var(--bg2);color:var(--text);margin-left:8px;">My Advisors</a>
</div>
