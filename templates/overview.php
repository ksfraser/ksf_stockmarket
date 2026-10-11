<?php
/**
 * Dashboard Overview — APP LEVEL dashboard.
 * Shows portfolio summary, all-symbol top gainers/losers, full data coverage.
 * Expects from controller: stats, portfolio, gainers, losers, freshness
 */
?>

<!-- App Dashboard Header -->
<div class="card" style="border-color:var(--accent);">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <h2 style="margin:0;font-size:1.3em;">&#x1F4CA; App Dashboard</h2>
            <p style="margin:4px 0 0;font-size:0.85em;color:var(--text3);">
                System-wide view — all tracked symbols, full coverage stats, market-wide movers.
                <a href="?action=my_dashboard" style="color:var(--accent);">&rarr; Switch to My Dashboard</a> for portfolio-specific view.
            </p>
        </div>
        <div style="text-align:right;font-size:0.8em;color:var(--text3);">
            Last data update: <strong style="color:var(--text);"><?php echo htmlspecialchars($data['stats']['last_update'] ?? 'N/A'); ?></strong>
        </div>
    </div>
</div>

<!-- Top Gainers & Losers — ALL SYMBOLS (App Level) -->
<div class="grid-2">
    <div class="card">
        <div class="card-header">&#x1F4C8; Top Gainers — All Tracked Symbols</div>
        <?php if (empty($data['gainers'])): ?>
            <p class="text-muted">No price data available.</p>
        <?php else: ?>
        <table>
            <thead><tr><th>Symbol</th><th>Name</th><th class="r">Close</th><th class="r">Change</th></tr></thead>
            <tbody>
            <?php foreach (array_slice($data['gainers'], 0, 10) as $g): ?>
                <tr>
                    <td><a href="?action=detail&symbol=<?php echo urlencode($g['symbol']); ?>"><strong><?php echo htmlspecialchars($g['symbol']); ?></strong></a></td>
                    <td style="font-size:0.82em;color:var(--text3);"><?php echo htmlspecialchars(mb_strimwidth($g['name'] ?? '', 0, 25, '…')); ?></td>
                    <td class="r">$<?php echo number_format($g['close'], 2); ?></td>
                    <td class="r green">+<?php echo number_format($g['change_pct'], 2); ?>%</td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        <?php endif; ?>
    </div>
    <div class="card">
        <div class="card-header">&#x1F4C9; Top Losers — All Tracked Symbols</div>
        <?php if (empty($data['losers'])): ?>
            <p class="text-muted">No price data available.</p>
        <?php else: ?>
        <table>
            <thead><tr><th>Symbol</th><th>Name</th><th class="r">Close</th><th class="r">Change</th></tr></thead>
            <tbody>
            <?php foreach (array_slice($data['losers'], 0, 10) as $l): ?>
                <tr>
                    <td><a href="?action=detail&symbol=<?php echo urlencode($l['symbol']); ?>"><strong><?php echo htmlspecialchars($l['symbol']); ?></strong></a></td>
                    <td style="font-size:0.82em;color:var(--text3);"><?php echo htmlspecialchars(mb_strimwidth($l['name'] ?? '', 0, 25, '…')); ?></td>
                    <td class="r">$<?php echo number_format($l['close'], 2); ?></td>
                    <td class="r red"><?php echo number_format($l['change_pct'], 2); ?>%</td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        <?php endif; ?>
    </div>
</div>

<!-- Data Coverage — ALL SYMBOLS (App Level) -->
<div class="card">
    <div class="card-header">&#x1F4CA; Data Coverage — All Tracked Symbols</div>
    <div class="stats-grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));">
        <div class="stat-card">
            <div class="stat-value"><?php echo $data['stats']['total_symbols']; ?></div>
            <div class="stat-label">Total Symbols</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:var(--green);"><?php echo $data['stats']['with_indicators']; ?></div>
            <div class="stat-label">With Indicators</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:var(--accent);"><?php echo $data['stats']['active_fetching']; ?></div>
            <div class="stat-label">Active (Fetching)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="font-size:1.2em;"><?php echo number_format($data['stats']['total_prices']); ?></div>
            <div class="stat-label">Price Rows</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="font-size:1.2em;"><?php echo number_format($data['stats']['total_indicators'] ?? 0); ?></div>
            <div class="stat-label">Indicator Rows</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:<?php echo ($data['freshness']['stale'] ?? 0) > 0 ? 'var(--yellow)' : 'var(--green)'; ?>">
                <?php echo $data['freshness']['fresh']; ?> / <?php echo ($data['freshness']['fresh'] ?? 0) + ($data['freshness']['stale'] ?? 0); ?>
            </div>
            <div class="stat-label">Fresh / Total</div>
        </div>
    </div>
</div>

<!-- Data Freshness Notice -->
<?php if (($data['freshness']['stale'] ?? 0) > 0): ?>
<div class="card" style="border-color:var(--yellow);background:rgba(234,179,8,0.1);">
    <strong style="color:var(--yellow);">&#x26A0;&#xFE0F; Data Freshness Warning:</strong>
    <?php echo $data['freshness']['stale']; ?> symbols have data older than 3 days.
    Check the <a href="?action=admin_symbols">Admin</a> page for details.
</div>
<?php endif; ?>

<!-- Symbol Data Quality -->
<?php $sq = $data['symbol_quality'] ?? []; ?>
<div class="card" style="margin-top:24px;border-color:var(--accent);">
    <div class="card-header">&#x1F50D; Symbol Data Quality</div>
    <div class="stats-grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));">
        <div class="stat-card">
            <div class="stat-value" style="color:<?php echo ($sq['dead_names'] ?? 0) > 0 ? 'var(--yellow)' : 'var(--green)'; ?>">
                <?php echo $sq['dead_names'] ?? 0; ?>
            </div>
            <div class="stat-label">Dead / Synthetic Names</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:<?php echo ($sq['null_exchanges'] ?? 0) > 0 ? 'var(--yellow)' : 'var(--green)'; ?>">
                <?php echo $sq['null_exchanges'] ?? 0; ?>
            </div>
            <div class="stat-label">Missing Exchange</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:<?php echo ($sq['needs_review'] ?? 0) > 0 ? 'var(--orange)' : 'var(--green)'; ?>">
                <?php echo $sq['needs_review'] ?? 0; ?>
            </div>
            <div class="stat-label">Needs Review</div>
        </div>
    </div>
    <p style="font-size:0.8em;color:var(--text3);margin-top:12px;">
        Open <a href="?action=admin_symbols" style="color:var(--accent);">Symbol Admin</a> and select <strong>Needs Review</strong> to batch-fix names, exchanges, and sectors.
    </p>
</div>
