<?php
/**
 * Stock Screener - TradingView Integration
 * Displays screener results from TradingView API
 */
$results = $data['screener_results'] ?? [];
$presets = $data['presets'] ?? [];
$presetName = $data['preset_name'] ?? 'dividend_stocks';
$presetLabel = $data['preset_label'] ?? 'Dividend Stocks';
?>

<div class="card" id="screener-card">
    <div class="card-header">📊 TradingView Stock Screener</div>

    <div style="margin-bottom: 16px;">
        <label for="screener-preset" style="margin-right:8px;">Preset:</label>
        <select id="screener-preset" style="padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <?php foreach ($presets as $key => $info): ?>
                <option value="<?php echo $key; ?>" <?php echo $presetName === $key ? 'selected' : ''; ?>><?php echo htmlspecialchars($info['label']); ?></option>
            <?php endforeach; ?>
        </select>
        <span style="color:var(--text3);font-size:0.85em;margin-left:12px;">
            Last run: <?php echo htmlspecialchars($results[0]['run_at'] ?? 'Never'); ?>
        </span>
    </div>

    <div id="screener-results">
        <?php if (empty($results)): ?>
            <p class="text-muted">No screener results found. Cron job runs daily at 6:30 AM.</p>
        <?php else: ?>
            <p style="margin-top:12px;font-size:0.85em;color:var(--text3);">
                Showing <?php echo count($results); ?> results for <?php echo htmlspecialchars($presetLabel); ?>.
                <a href="?action=screener&preset=<?php echo urlencode($presetName); ?>" style="color:var(--accent);">Refresh</a>
            </p>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Name</th>
                            <th class="r">Price</th>
                            <th class="r">Change %</th>
                            <th class="r">1Y Perf</th>
                            <th class="r">Yield %</th>
                            <th class="r">P/E</th>
                            <th class="r">ROE %</th>
                            <th class="r">Gross Margin %</th>
                            <th>Sector</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($results as $r):
                            $m = $r['metrics'] ?? []; ?>
                            <tr>
                                <td><a href="?action=detail&symbol=<?php echo urlencode(str_replace(['NASDAQ:', 'NYSE:', 'TSE:', 'TSX:', 'NEO:'], '', $r['symbol'])); ?>">
                                    <?php echo htmlspecialchars($r['symbol']); ?></a></td>
                                <td><?php echo htmlspecialchars($m['name'] ?? ''); ?></td>
                                <td class="r">$<?php echo number_format($m['close'] ?? 0, 2); ?></td>
                                <td class="r" style="color:<?php echo ($m['change'] ?? 0) >= 0 ? 'var(--green)' : 'var(--red)'; ?>">
                                    <?php echo number_format($m['change'] ?? 0, 2); ?>%
                                </td>
                                <td class="r"><?php echo number_format($m['Perf.Y'] ?? 0, 1); ?>%</td>
                                <td class="r"><?php echo $presetName === 'dividend_stocks' ? number_format($m['dividends_yield_current'] ?? 0, 2) . '%' : '-'; ?></td>
                                <td class="r"><?php echo number_format($m['price_earnings_ttm'] ?? 0, 1); ?></td>
                                <td class="r"><?php echo number_format($m['return_on_equity'] ?? 0, 1); ?>%</td>
                                <td class="r"><?php echo number_format($m['gross_margin_ttm'] ?? 0, 1); ?>%</td>
                                <td><?php echo htmlspecialchars($m['sector'] ?? ''); ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    </div>
</div>

<script>
(function() {
    const select = document.getElementById('screener-preset');
    const target = document.getElementById('screener-results');
    if (!select || !target) return;

    function updateScreener() {
        const url = new URL(window.location.href);
        url.searchParams.set('action', 'api_screener');
        url.searchParams.set('preset', select.value);
        fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(function(res) { return res.text(); })
        .then(function(html) {
            target.innerHTML = html;
        })
        .catch(function(err) {
            console.error('Screener update failed', err);
            target.innerHTML = '<p class="text-muted">Failed to load screener results.</p>';
        });
    }

    select.addEventListener('change', function() {
        updateScreener();
    });
})();
</script>
