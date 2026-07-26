<?php
// reports.php — Reports hub
$report = $data['report'] ?? 'securities';
$start = htmlspecialchars($data['start'] ?? '');
$end = htmlspecialchars($data['end'] ?? '');
$result = $data['result'] ?? null;
$error = $data['error'] ?? null;
?>

<h1>Reports</h1>

<div class="tabs">
    <a href="?action=reports&report=twror" class="<?= $report==='twror'?'active':'' ?>">TTWROR</a>
    <a href="?action=reports&report=securities" class="<?= $report==='securities'?'active':'' ?>">Securities</a>
    <a href="?action=reports&report=payments" class="<?= $report==='payments'?'active':'' ?>">Payments</a>
    <a href="?action=reports&report=tax_lots" class="<?= $report==='tax_lots'?'active':'' ?>">Tax Lots</a>
    <a href="?action=reports&report=heatmap" class="<?= $report==='heatmap'?'active':'' ?>">Heat Map</a>
    <a href="?action=reports&report=rebalance" class="<?= $report==='rebalance'?'active':'' ?>">Rebalance</a>
</div>

<form method="get" class="report-form">
    <input type="hidden" name="action" value="reports">
    <input type="hidden" name="report" value="<?= htmlspecialchars($report) ?>">
    <label>Start <input type="date" name="start" value="<?= $start ?>"></label>
    <label>End <input type="date" name="end" value="<?= $end ?>"></label>
    <?php if ($report === 'rebalance'): ?>
        <label>Target ID <input type="number" name="target_id" value="<?= htmlspecialchars($data['target_id'] ?? '') ?>"></label>
    <?php endif; ?>
    <button type="submit">Run</button>
</form>

<?php if ($error): ?>
    <div class="alert error"><?= htmlspecialchars($error) ?></div>
<?php endif; ?>

<?php if ($result): ?>
    <?php if (isset($result['twror'])): ?>
        <div class="card">
            <h3>TTWROR</h3>
            <p>Total: <strong><?= htmlspecialchars($result['twror']) ?>%</strong></p>
            <p>Annualized: <strong><?= htmlspecialchars($result['annualized']) ?>%</strong></p>
            <p>Period: <?= htmlspecialchars($result['start']) ?> → <?= htmlspecialchars($result['end']) ?> (<?= htmlspecialchars($result['years']) ?> yrs)</p>
        </div>
    <?php endif; ?>

    <?php if (isset($result['securities'])): ?>
        <table class="table">
            <thead>
                <tr><th>Symbol</th><th>Account</th><th>Shares</th><th>Cost Basis</th><th>Market Value</th><th>P&L</th><th>P&L %</th></tr>
            </thead>
            <tbody>
            <?php foreach ($result['securities'] ?? [] as $row): ?>
                <tr>
                    <td><?= htmlspecialchars($row['symbol']) ?></td>
                    <td><?= htmlspecialchars($row['account_type']) ?></td>
                    <td><?= htmlspecialchars($row['shares']) ?></td>
                    <td><?= htmlspecialchars($row['cost_basis']) ?></td>
                    <td><?= htmlspecialchars($row['market_value']) ?></td>
                    <td class="<?= ($row['pnl'] ?? 0) >= 0 ? 'positive' : 'negative' ?>"><?= htmlspecialchars($row['pnl']) ?></td>
                    <td class="<?= ($row['pnl_pct'] ?? 0) >= 0 ? 'positive' : 'negative' ?>"><?= htmlspecialchars($row['pnl_pct']) ?>%</td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    <?php endif; ?>

    <?php if (isset($result['dividends']) || isset($result['by_type'])): ?>
        <div class="card">
            <h3>Payments Summary</h3>
            <p>Dividends: <?= htmlspecialchars($result['dividends']['total'] ?? 0) ?> (<?= htmlspecialchars($result['dividends']['count'] ?? 0) ?>)</p>
            <p>Interest: <?= htmlspecialchars($result['interest'] ?? 0) ?></p>
            <p>Fees/Tax: <?= htmlspecialchars($result['fees'] ?? 0) ?></p>
        </div>
    <?php endif; ?>

    <?php if (isset($result['lots'])): ?>
        <table class="table">
            <thead><tr><th>Symbol</th><th>Open Lots</th><th>Open Qty</th><th>Realized P&L</th></tr></thead>
            <tbody>
            <?php foreach ($result['lots'] ?? [] as $lot): ?>
                <tr>
                    <td><?= htmlspecialchars($lot['symbol']) ?></td>
                    <td><?= (int)$lot['open_lots'] ?></td>
                    <td><?= htmlspecialchars($lot['open_qty']) ?></td>
                    <td class="<?= ($lot['realized_pnl'] ?? 0) >= 0 ? 'positive' : 'negative' ?>"><?= htmlspecialchars($lot['realized_pnl']) ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    <?php endif; ?>

    <?php if (isset($result['securities']) && $report === 'heatmap'): ?>
        <div class="heat-grid">
            <?php foreach ($result['securities'] as $sec): 
                $max_mom = max(abs($sec['mom_1m']), 0.01);
                $r = $sec['mom_1m'] > 0 ? min(255, 100 + intval(($sec['mom_1m'] / $max_mom) * 155)) : 80;
                $g = $sec['mom_1m'] > 0 ? 80 : min(255, 100 + intval((abs($sec['mom_1m']) / $max_mom) * 155));
                $b = 80;
            ?>
                <div class="heat-cell" style="background:rgb(<?= $r ?>,<?= $g ?>,<?= $b ?>)">
                    <div class="heat-sym"><?= htmlspecialchars($sec['symbol']) ?></div>
                    <div class="heat-mom"><?= htmlspecialchars($sec['mom_1m']) ?>%</div>
                    <div class="heat-mv"><?= htmlspecialchars($sec['market_value']) ?></div>
                </div>
            <?php endforeach; ?>
        </div>
    <?php endif; ?>

    <?php if (isset($result['needs_rebalance'])): ?>
        <div class="card">
            <h3>Rebalance Analysis</h3>
            <p>Needs rebalance: <strong><?= $result['needs_rebalance'] ? 'Yes' : 'No' ?></strong></p>
            <table class="table">
                <thead><tr><th>Symbol</th><th>Target %</th><th>Actual %</th><th>Drift</th><th>Action</th></tr></thead>
                <tbody>
                <?php foreach ($result['drifts'] ?? [] as $d): ?>
                    <tr>
                        <td><?= htmlspecialchars($d['symbol']) ?></td>
                        <td><?= htmlspecialchars($d['target_pct']) ?>%</td>
                        <td><?= htmlspecialchars($d['actual_pct']) ?>%</td>
                        <td><?= htmlspecialchars($d['drift']) ?>%</td>
                        <td><?= $d['needs_rebalance'] ? '<span class="badge warn">Rebalance</span>' : 'OK' ?></td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    <?php endif; ?>
<?php endif; ?>

<style>
.report-form { margin: 10px 0; }
.report-form label { margin-right: 15px; }
.tabs a { margin-right: 10px; }
.tabs a.active { font-weight: bold; text-decoration: underline; }
.heat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; margin-top: 12px; }
.heat-cell { padding: 10px; border-radius: 6px; color: #fff; text-align: center; }
.heat-sym { font-weight: bold; }
.heat-mom { font-size: 0.9em; }
.heat-mv { font-size: 0.8em; opacity: 0.8; }
</style>
