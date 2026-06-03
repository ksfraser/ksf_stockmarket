<?php
/**
 * Stock Selection Strategies page — organized by portfolio sleeve.
 *
 * Data:
 *   $bySleeve  — array keyed by sleeve name, each containing strategy arrays
 *   $timing    — array of timing/technical strategy arrays available for all sleeves
 *   $totalCount — total number of registered strategies
 */
$bySleeve   = $data['bySleeve'] ?? ['core' => [], 'tactical' => [], 'income' => [], 'satellite' => []];
$timing     = $data['timing'] ?? [];
$totalCount = $data['totalCount'] ?? 0;

$sleeveLabels = [
    'core'     => ['label' => 'Core Sleeve (40%)',     'icon' => '&#x1F3E6;', 'desc' => 'Buy & hold 5+ years. Wide moat, quality compounders.'],
    'tactical' => ['label' => 'Tactical Sleeve (30%)',  'icon' => '&#x1F3AF;', 'desc' => 'Hold 1-6 months. Momentum, earnings, breakouts.'],
    'income'   => ['label' => 'Income Sleeve (20%)',    'icon' => '&#x1F4B0;', 'desc' => 'Hold 1-3 years. Dividends, aristocrats, REITs.'],
    'satellite'=> ['label' => 'Satellite Sleeve (10%)', 'icon' => '&#x1F680;', 'desc' => 'Hold 3-12 months. Deep value, moonshots, options.'],
];
?>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4CA; Stock Selection Strategies — Overview <span style="float:right;font-size:0.7em;color:var(--text3);"><?= (int)$totalCount ?> strategies registered</span></div>
    <p style="margin-bottom:12px;">
        Each strategy below is implemented as a class implementing <code>IStrategy</code>
        and registered via Dependency Injection. Strategies are grouped by the portfolio sleeve
        they are designed for. New strategies can be added by creating a class and registering it in
        <code>StrategyFactory</code>.
    </p>
    <p style="font-size:0.85em;color:var(--text3);">
        <span style="color:var(--green);">&#x25CF;</span> Battle Tested &nbsp;
        <span style="color:var(--yellow);">&#x25CF;</span> Promising &nbsp;
        <span style="color:var(--accent);">&#x25CF;</span> Active / Screening Tool &nbsp;
        <span style="color:var(--blue);">&#x25CF;</span> Other
    </p>
</div>

<!-- Strategy Cards by Sleeve -->
<?php foreach ($sleeveLabels as $sleeveKey => $sleeveInfo): ?>
    <?php if (empty($bySleeve[$sleeveKey])) continue; ?>

    <h2 style="color:var(--accent);margin:24px 0 12px;border-bottom:1px solid rgba(99,179,237,0.3);padding-bottom:8px;">
        <?= $sleeveInfo['icon'] ?> <?= htmlspecialchars($sleeveInfo['label']) ?>
        <span style="font-size:0.65em;color:var(--text3);font-weight:400;">
            — <?= htmlspecialchars($sleeveInfo['desc']) ?>
        </span>
    </h2>

    <?php foreach ($bySleeve[$sleeveKey] as $s):
        $statusColor = $s['status_color'] ?? 'blue';
        $statusBg = match($statusColor) {
            'green' => 'rgba(104,211,145,0.2)',
            'yellow' => 'rgba(246,224,94,0.2)',
            'red' => 'rgba(252,129,129,0.2)',
            'accent' => 'rgba(99,179,237,0.2)',
            default => 'rgba(99,179,237,0.2)',
        };
        $statusFg = match($statusColor) {
            'green' => 'var(--green)',
            'yellow' => 'var(--yellow)',
            'red' => 'var(--red)',
            'accent' => 'var(--accent)',
            default => 'var(--accent)',
        };
    ?>
    <div class="card" style="margin-bottom:16px;">
        <div class="card-header" style="display:flex;align-items:center;gap:10px;">
            <span style="background:<?= $statusBg ?>;color:<?= $statusFg ?>;padding:2px 10px;border-radius:12px;font-size:0.75em;">
                <?= htmlspecialchars($s['status'] ?? 'N/A') ?>
            </span>
            <span><?= htmlspecialchars($s['name']) ?></span>
            <span style="margin-left:auto;font-size:0.7em;color:var(--text3);background:rgba(0,0,0,0.15);padding:2px 8px;border-radius:8px;">
                <?= htmlspecialchars($s['time_horizon'] ?? '') ?> &middot; <?= htmlspecialchars($s['risk_level'] ?? '') ?> risk
            </span>
        </div>

        <p style="color:var(--text2);margin-bottom:12px;font-size:0.9em;"><?= htmlspecialchars($s['description']) ?></p>

        <!-- Screening Criteria -->
        <?php if (!empty($s['criteria'])): ?>
        <div style="background:rgba(0,0,0,0.1);border-radius:var(--radius);padding:10px 14px;margin-bottom:12px;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;margin-bottom:6px;">&#x1F50D; Screening Criteria</div>
            <ul style="margin:0 0 0 16px;font-size:0.85em;color:var(--text2);line-height:1.6;">
                <?php foreach ($s['criteria'] as $c): ?>
                    <li><?= htmlspecialchars($c) ?></li>
                <?php endforeach; ?>
            </ul>
        </div>
        <?php endif; ?>

        <!-- Backtest Results -->
        <?php $bt = $s['backtest'] ?? []; ?>
        <?php if (!empty($bt['win_rate'])): ?>
        <div class="grid-3" style="margin-bottom:12px;">
            <div style="background:rgba(0,0,0,0.1);padding:10px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Win Rate</div>
                <div style="font-size:1.3em;font-weight:700;"><?= htmlspecialchars($bt['win_rate']) ?></div>
            </div>
            <div style="background:rgba(0,0,0,0.1);padding:10px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Profit Factor</div>
                <div style="font-size:1.3em;font-weight:700;"><?= htmlspecialchars($bt['profit_factor']) ?></div>
            </div>
            <div style="background:rgba(0,0,0,0.1);padding:10px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Max Drawdown</div>
                <div style="font-size:1.3em;font-weight:700;color:var(--red);"><?= htmlspecialchars($bt['max_drawdown']) ?></div>
            </div>
            <?php if (isset($bt['total_trades']) && $bt['total_trades'] > 0): ?>
            <div style="background:rgba(0,0,0,0.1);padding:10px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Total Trades</div>
                <div style="font-size:1.3em;font-weight:700;"><?= number_format($bt['total_trades']) ?></div>
            </div>
            <?php endif; ?>
            <?php if (!empty($bt['avg_win'])): ?>
            <div style="background:rgba(0,0,0,0.1);padding:10px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Avg Win</div>
                <div style="font-size:1.3em;font-weight:700;color:var(--green);"><?= htmlspecialchars($bt['avg_win']) ?></div>
            </div>
            <?php endif; ?>
            <?php if (!empty($bt['avg_loss'])): ?>
            <div style="background:rgba(0,0,0,0.1);padding:10px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Avg Loss</div>
                <div style="font-size:1.3em;font-weight:700;color:var(--red);"><?= htmlspecialchars($bt['avg_loss']) ?></div>
            </div>
            <?php endif; ?>
        </div>
        <?php endif; ?>

        <!-- Implications -->
        <?php if (!empty($bt['implications'])): ?>
        <div style="background:rgba(0,0,0,0.1);border-left:3px solid var(--accent);padding:10px 14px;border-radius:0 var(--radius) var(--radius) 0;margin-bottom:10px;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;margin-bottom:4px;">&#x1F4A1; Implications</div>
            <p style="font-size:0.85em;color:var(--text2);margin:0;"><?= htmlspecialchars($bt['implications']) ?></p>
        </div>
        <?php endif; ?>

        <!-- Sources -->
        <?php if (!empty($s['sources'])): ?>
        <div style="font-size:0.7em;color:var(--text3);">
            Sources: <?= htmlspecialchars(implode(' &middot; ', $s['sources'])) ?>
        </div>
        <?php endif; ?>

        <!-- Required Data -->
        <?php if (!empty($s['required_data'])): ?>
        <div style="font-size:0.7em;color:var(--text3);margin-top:4px;">
            Data required: <?= htmlspecialchars(implode(', ', $s['required_data'])) ?>
        </div>
        <?php endif; ?>
    </div>
    <?php endforeach; ?>

<?php endforeach; ?>

<!-- Timing Strategies (available for all sleeves) -->
<?php if (!empty($timing)): ?>
<h2 style="color:var(--orange);margin:32px 0 12px;border-bottom:1px solid rgba(237,137,54,0.3);padding-bottom:8px;">
    &#x23F0; Timing &amp; Technical Strategies — Available for All Sleves
</h2>
<?php foreach ($timing as $s):
    $statusColor = $s['status_color'] ?? 'blue';
    $statusBg = match($statusColor) {
        'green' => 'rgba(104,211,145,0.2)',
        'yellow' => 'rgba(246,224,94,0.2)',
        'red' => 'rgba(252,129,129,0.2)',
        'accent' => 'rgba(99,179,237,0.2)',
        default => 'rgba(99,179,237,0.2)',
    };
    $statusFg = match($statusColor) {
        'green' => 'var(--green)',
        'yellow' => 'var(--yellow)',
        'red' => 'var(--red)',
        'accent' => 'var(--accent)',
        default => 'var(--accent)',
    };
    $bt = $s['backtest'] ?? [];
?>
<div class="card" style="margin-bottom:16px;border-left:3px solid var(--orange);">
    <div class="card-header" style="display:flex;align-items:center;gap:10px;">
        <span style="background:<?= $statusBg ?>;color:<?= $statusFg ?>;padding:2px 10px;border-radius:12px;font-size:0.75em;">
            <?= htmlspecialchars($s['status'] ?? 'N/A') ?>
        </span>
        <span><?= htmlspecialchars($s['name']) ?></span>
    </div>
    <p style="color:var(--text2);margin-bottom:12px;font-size:0.9em;"><?= htmlspecialchars($s['description']) ?></p>
    <?php if (!empty($s['criteria'])): ?>
    <div style="background:rgba(0,0,0,0.1);border-radius:var(--radius);padding:10px 14px;margin-bottom:12px;">
        <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;margin-bottom:6px;">&#x1F50D; Criteria</div>
        <ul style="margin:0 0 0 16px;font-size:0.85em;color:var(--text2);line-height:1.6;">
            <?php foreach ($s['criteria'] as $c): ?><li><?= htmlspecialchars($c) ?></li><?php endforeach; ?>
        </ul>
    </div>
    <?php endif; ?>
    <?php if (!empty($bt['win_rate'])): ?>
    <div class="grid-3" style="margin-bottom:12px;">
        <div style="background:rgba(0,0,0,0.1);padding:8px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.6em;color:var(--text3);text-transform:uppercase;">Win Rate</div>
            <div style="font-size:1.2em;font-weight:700;"><?= htmlspecialchars($bt['win_rate']) ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.1);padding:8px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.6em;color:var(--text3);text-transform:uppercase;">Profit Factor</div>
            <div style="font-size:1.2em;font-weight:700;"><?= htmlspecialchars($bt['profit_factor']) ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.1);padding:8px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.6em;color:var(--text3);text-transform:uppercase;">Max DD</div>
            <div style="font-size:1.2em;font-weight:700;color:var(--red);"><?= htmlspecialchars($bt['max_drawdown']) ?></div>
        </div>
    </div>
    <?php endif; ?>
    <?php if (!empty($bt['implications'])): ?>
    <div style="background:rgba(0,0,0,0.1);border-left:3px solid var(--orange);padding:10px 14px;border-radius:0 var(--radius) var(--radius) 0;font-size:0.85em;color:var(--text2);">
        <strong>Implications:</strong> <?= htmlspecialchars($bt['implications']) ?>
    </div>
    <?php endif; ?>
    <?php if (!empty($s['sources'])): ?>
    <div style="font-size:0.7em;color:var(--text3);margin-top:8px;">
        Sources: <?= htmlspecialchars(implode(' &middot; ', $s['sources'])) ?>
    </div>
    <?php endif; ?>
</div>
<?php endforeach; ?>
<?php endif; ?>

<div style="display:flex;gap:12px;margin-top:24px;justify-content:center;">
    <a href="?action=strategy_money" class="btn">&#x1F4B0; Money &amp; Risk Management</a>
    <a href="?action=strategy_timing" class="btn">&#x23F0; Timing &amp; Technical</a>
</div>
