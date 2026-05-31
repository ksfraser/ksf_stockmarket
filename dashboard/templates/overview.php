<?php
/**
 * Dashboard Overview template.
 * Expects: $data = stats, portfolio, gainers, losers, active, freshness
 */
?>
<!-- Portfolio Summary -->
<div class="card">
    <div class="card-header">Portfolio Summary</div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($data['stats']['portfolio_value'], 2) ?></div>
            <div class="stat-label">Current Value</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($data['stats']['portfolio_cost'], 2) ?></div>
            <div class="stat-label">Cost Basis</div>
        </div>
        <div class="stat-card">
            <div class="stat-value <?= ($data['stats']['portfolio_pnl'] >= 0) ? 'pnl-positive' : 'pnl-negative' ?>">
                <?= ($data['stats']['portfolio_pnl'] >= 0) ? '+' : '' ?>$<?= number_format($data['stats']['portfolio_pnl'], 2) ?>
            </div>
            <div class="stat-label">Unrealized P&amp;L</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?= $data['stats']['portfolio_holdings'] ?></div>
            <div class="stat-label">Holdings</div>
        </div>
    </div>
</div>

<!-- Portfolio Holdings Quick View -->
<?php if (!empty($data['portfolio'])): ?>
<div class="card">
    <div class="card-header">Current Holdings <a href="?action=portfolio" class="btn btn-sm" style="float:right">Full View</a></div>
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Account</th>
                <th class="r">Shares</th>
                <th class="r">Cost Basis</th>
                <th class="r">Current</th>
                <th class="r">Value</th>
                <th class="r">P&amp;L</th>
                <th class="r">P&amp;L %</th>
                <th>Strategy</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($data['portfolio'] as $h):
            $currentValue = $h['shares'] * ($h['current_price'] ?? 0);
            $pnl = $currentValue - ($h['shares'] * $h['cost_basis']);
            $pnlPct = ($h['cost_basis'] > 0) ? ($pnl / ($h['shares'] * $h['cost_basis'])) * 100 : 0;
        ?>
            <tr>
                <td><a href="?action=detail&symbol=<?= urlencode($h['symbol']) ?>"><strong><?= htmlspecialchars($h['symbol']) ?></strong></a></td>
                <td><?= htmlspecialchars($h['account_type']) ?></td>
                <td class="r"><?= number_format($h['shares'], 2) ?></td>
                <td class="r">$<?= number_format($h['cost_basis'], 2) ?></td>
                <td class="r"><?= fmt_price($h['current_price'] ?? null) ?></td>
                <td class="r">$<?= number_format($currentValue, 2) ?></td>
                <td class="r <?= $pnl >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= $pnl >= 0 ? '+' : '' ?>$<?= number_format($pnl, 2) ?></td>
                <td class="r <?= $pnlPct >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= fmt_pct($pnlPct) ?></td>
                <td><?= htmlspecialchars($h['strategy']) ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php endif; ?>

<!-- Market Overview -->
<div class="grid-3">
    <div class="card">
        <div class="card-header">Data Coverage</div>
        <div class="stats-grid" style="grid-template-columns:1fr 1fr">
            <div class="stat-card">
                <div class="stat-value"><?= $data['stats']['total_symbols'] ?></div>
                <div class="stat-label">Symbols w/ Prices</div>
            </div>
            <div class="stat-card">
                <div class="stat-value"><?= $data['stats']['with_indicators'] ?></div>
                <div class="stat-label">With Indicators</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="font-size:1.2em"><?= $data['stats']['total_prices'] ?></div>
                <div class="stat-label">Price Rows</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:<?= $data['freshness']['stale'] > 0 ? 'var(--yellow)' : 'var(--green)' ?>">
                    <?= $data['freshness']['fresh'] ?> / <?= $data['freshness']['fresh'] + $data['freshness']['stale'] ?>
                </div>
                <div class="stat-label">Fresh / Total</div>
            </div>
        </div>
    </div>

    <?php if (!empty($data['gainers'])): ?>
    <div class="card">
        <div class="card-header">Top Gainers</div>
        <table>
            <thead><tr><th>Symbol</th><th class="r">Close</th><th class="r">Change</th></tr></thead>
            <tbody>
            <?php foreach (array_slice($data['gainers'], 0, 5) as $g): ?>
                <tr>
                    <td><a href="?action=detail&symbol=<?= urlencode($g['symbol']) ?>"><?= htmlspecialchars($g['symbol']) ?></a></td>
                    <td class="r">$<?= number_format($g['close'], 2) ?></td>
                    <td class="r green">+<?= number_format($g['change_pct'], 2) ?>%</td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </div>
    <?php endif; ?>

    <?php if (!empty($data['losers'])): ?>
    <div class="card">
        <div class="card-header">Top Losers</div>
        <table>
            <thead><tr><th>Symbol</th><th class="r">Close</th><th class="r">Change</th></tr></thead>
            <tbody>
            <?php foreach (array_slice($data['losers'], 0, 5) as $l): ?>
                <tr>
                    <td><a href="?action=detail&symbol=<?= urlencode($l['symbol']) ?>"><?= htmlspecialchars($l['symbol']) ?></a></td>
                    <td class="r">$<?= number_format($l['close'], 2) ?></td>
                    <td class="r red"><?= number_format($l['change_pct'], 2) ?>%</td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </div>
    <?php endif; ?>
</div>

<!-- Data Freshness Notice -->
<?php if ($data['freshness']['stale'] > 0): ?>
<div class="card" style="border-color:var(--yellow); background:rgba(234,179,8,0.1)">
    <strong style="color:var(--yellow)">&#x26A0; Data Freshness Warning:</strong>
    <?= $data['freshness']['stale'] ?> symbols have data older than 3 days.
    <a href="http://fhsws002.ksfraser.com/ksf_stockmarket/python/daily_pipeline.py" target="_blank">Run data fetch</a> to update.
</div>
<?php endif; ?>
