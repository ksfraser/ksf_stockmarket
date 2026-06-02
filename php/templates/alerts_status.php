<?php
/**
 * Alerts & Cron Status dashboard.
 *
 * Data:
 *   $jobs       — array of cron job info
 *   $summary    — counts by status
 *   $volumeSnapshots — volume snapshot jobs
 *   $priceAlerts     — price alert jobs
 */
$jobs       = $data['jobs'] ?? [];
$summary    = $data['summary'] ?? [];
$volumeSnapshots = $data['volumeSnapshots'] ?? [];
$priceAlerts = $data['priceAlerts'] ?? [];

function statusBadge(string $status): array
{
    return match ($status) {
        'ok'        => ['green',  '&#x2705; OK'],
        'error'     => ['red',    '&#x274C; Error'],
        'paused'    => ['yellow', '&#x23F8; Paused'],
        'scheduled' => ['accent', '&#x23F0; Scheduled'],
        default     => ['blue',   '&#x2022; Never Run'],
    };
}
?>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4E3; Alerts &amp; Cron Job Status</div>
    <p style="margin-bottom:16px;">
        Monitoring all Hermes cron jobs that track your investments.
        Volume snapshots run 4× daily during market hours (Mon–Fri).
        Price alerts check every 15 minutes.
    </p>

    <!-- Summary Cards -->
    <div class="stats-grid" style="margin-bottom:20px;">
        <div class="stat-card" style="background:rgba(0,0,0,0.15);">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;">Total Jobs</div>
            <div style="font-size:1.8em;font-weight:700;"><?= (int)($summary['total'] ?? 0) ?></div>
        </div>
        <div class="stat-card" style="background:rgba(104,211,145,0.1);">
            <div style="font-size:0.7em;color:var(--green);text-transform:uppercase;">OK</div>
            <div style="font-size:1.8em;font-weight:700;color:var(--green);"><?= (int)($summary['ok'] ?? 0) ?></div>
        </div>
        <div class="stat-card" style="background:rgba(252,129,129,0.1);">
            <div style="font-size:0.7em;color:var(--red);text-transform:uppercase;">Errors</div>
            <div style="font-size:1.8em;font-weight:700;color:var(--red);"><?= (int)($summary['errors'] ?? 0) ?></div>
        </div>
        <div class="stat-card" style="background:rgba(246,224,94,0.1);">
            <div style="font-size:0.7em;color:var(--yellow);text-transform:uppercase;">Paused</div>
            <div style="font-size:1.8em;font-weight:700;color:var(--yellow);"><?= (int)($summary['paused'] ?? 0) ?></div>
        </div>
        <div class="stat-card" style="background:rgba(99,179,237,0.1);">
            <div style="font-size:0.7em;color:var(--accent);text-transform:uppercase;">Scheduled</div>
            <div style="font-size:1.8em;font-weight:700;color:var(--accent);"><?= (int)($summary['scheduled'] ?? 0) ?></div>
        </div>
    </div>
</div>

<!-- Volume Snapshot Schedule -->
<?php if (!empty($volumeSnapshots)): ?>
<h2 style="color:var(--orange);margin:20px 0 12px;border-bottom:1px solid rgba(237,137,54,0.3);padding-bottom:8px;">
    &#x1F4CA; Volume Snapshots (4× Daily)
</h2>
<p style="font-size:0.85em;color:var(--text3);margin-bottom:12px;">
    Mon–Fri: 10:30 AM, 12:00 PM, 3:00 PM, 3:45 PM — Checks intraday volume spikes (2× average threshold).
    Symbols monitored: RY, CM, CNR, BPF.UN, SRV.UN, CDZ, PZA, WJX, MTY, TFII, RUS, PDC, FEZ, IEV, SPEU, MX, RGLD, UL.
</p>
<?php foreach ($volumeSnapshots as $job):
    [$color, $badge] = statusBadge($job['last_status']);
?>
<div class="card" style="margin-bottom:10px;border-left:3px solid var(--orange);">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span style="background:rgba(<?= $color === 'green' ? '104,211,145' : ($color === 'red' ? '252,129,129' : '99,179,237') ?>,0.2);color:var(--<?= $color ?>);padding:2px 10px;border-radius:12px;font-size:0.75em;">
            <?= $badge ?>
        </span>
        <strong><?= htmlspecialchars($job['name']) ?></strong>
        <span style="margin-left:auto;font-size:0.75em;color:var(--text3);">
            Schedule: <code><?= htmlspecialchars($job['schedule']) ?></code>
        </span>
    </div>
    <div style="display:flex;gap:20px;margin-top:8px;font-size:0.8em;color:var(--text3);">
        <span>Last run: <strong><?= htmlspecialchars($job['last_run']) ?></strong></span>
        <span>Next run: <strong><?= htmlspecialchars($job['next_run']) ?></strong></span>
        <?php if ($job['last_error']): ?>
            <span style="color:var(--red);">Error: <?= htmlspecialchars($job['last_error']) ?></span>
        <?php endif; ?>
    </div>
</div>
<?php endforeach; ?>
<?php endif; ?>

<!-- Price Alerts -->
<?php if (!empty($priceAlerts)): ?>
<h2 style="color:var(--green);margin:20px 0 12px;border-bottom:1px solid rgba(104,211,145,0.3);padding-bottom:8px;">
    &#x1F4B0; Price Alerts
</h2>
<?php foreach ($priceAlerts as $job):
    [$color, $badge] = statusBadge($job['last_status']);
?>
<div class="card" style="margin-bottom:10px;border-left:3px solid var(--green);">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span style="background:rgba(<?= $color === 'green' ? '104,211,145' : ($color === 'red' ? '252,129,129' : '99,179,237') ?>,0.2);color:var(--<?= $color ?>);padding:2px 10px;border-radius:12px;font-size:0.75em;">
            <?= $badge ?>
        </span>
        <strong><?= htmlspecialchars($job['name']) ?></strong>
        <span style="margin-left:auto;font-size:0.75em;color:var(--text3);">
            <code><?= htmlspecialchars($job['schedule']) ?></code>
        </span>
    </div>
    <div style="display:flex;gap:20px;margin-top:8px;font-size:0.8em;color:var(--text3);">
        <span>Last: <strong><?= htmlspecialchars($job['last_run']) ?></strong></span>
        <span>Next: <strong><?= htmlspecialchars($job['next_run']) ?></strong></span>
    </div>
</div>
<?php endforeach; ?>
<?php endif; ?>

<!-- All Jobs Table -->
<h2 style="color:var(--accent);margin:24px 0 12px;border-bottom:1px solid rgba(99,179,237,0.3);padding-bottom:8px;">
    &#x23F0; All Cron Jobs
</h2>

<?php if (empty($jobs)): ?>
<div class="card">
    <p style="color:var(--text3);text-align:center;padding:20px;">No cron jobs found.</p>
</div>
<?php else: ?>
<div style="overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;font-size:0.82em;">
    <thead>
        <tr style="background:rgba(0,0,0,0.2);">
            <th style="padding:8px 12px;text-align:left;">Status</th>
            <th style="padding:8px 12px;text-align:left;">Job Name</th>
            <th style="padding:8px 12px;text-align:left;">Schedule</th>
            <th style="padding:8px 12px;text-align:left;">Last Run</th>
            <th style="padding:8px 12px;text-align:left;">Next Run</th>
            <th style="padding:8px 12px;text-align:left;">Deliver</th>
        </tr>
    </thead>
    <tbody>
    <?php foreach ($jobs as $job):
        [$color, $badge] = statusBadge($job['last_status']);
        $rowBg = $job['last_status'] === 'error' ? 'rgba(252,129,129,0.05)' : '';
    ?>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.04);background:<?= $rowBg ?>;">
        <td style="padding:8px 12px;">
            <span style="color:var(--<?= $color ?>);"><?= $badge ?></span>
        </td>
        <td style="padding:8px 12px;">
            <strong><?= htmlspecialchars($job['name']) ?></strong>
            <?php if ($job['prompt']): ?>
            <div style="font-size:0.8em;color:var(--text3);margin-top:2px;"><?= htmlspecialchars($job['prompt']) ?></div>
            <?php endif; ?>
        </td>
        <td style="padding:8px 12px;"><code style="font-size:0.85em;"><?= htmlspecialchars($job['schedule']) ?></code></td>
        <td style="padding:8px 12px;color:var(--text2);"><?= htmlspecialchars($job['last_run']) ?></td>
        <td style="padding:8px 12px;color:var(--text2);"><?= htmlspecialchars($job['next_run']) ?></td>
        <td style="padding:8px 12px;color:var(--text3);"><?= htmlspecialchars($job['deliver']) ?></td>
    </tr>
    <?php endforeach; ?>
    </tbody>
</table>
</div>
<?php endif; ?>

<!-- Inactive Symbols Note -->
<div class="card" style="margin-top:24px;border-color:var(--yellow);">
    <div class="card-header">&#x26A0;&#xFE0F; Inactive Symbols</div>
    <p style="font-size:0.85em;color:var(--text2);">
        The following symbols are marked <strong>is_active = 0</strong> in <code>symbol_master</code>
        and are excluded from price fetching and volume monitoring:
    </p>
    <ul style="margin:8px 0 0 20px;font-size:0.85em;color:var(--text3);">
        <li><strong>KEG-UN.TO</strong> — Taken private/delisted. Historical data preserved. Price fetchers and volume snapshots skip this symbol.</li>
    </ul>
    <p style="font-size:0.8em;color:var(--text3);margin-top:8px;">
        To deactivate a symbol: <a href="?action=admin_symbols">Symbol Admin → Deactivate</a>.
        Inactive symbols keep their historical prices but no new data is fetched.
    </p>
</div>

<div style="display:flex;gap:12px;margin-top:24px;justify-content:center;">
    <a href="?action=overview" class="btn">&larr; Dashboard</a>
    <a href="?action=admin_symbols" class="btn">&#x1F4B0; Symbol Admin</a>
</div>
