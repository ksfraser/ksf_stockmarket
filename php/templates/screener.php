<?php
/**
 * Stock Screener - TradingView Integration
 * Displays screener results from TradingView API
 */
$results = $data['screener_results'] ?? [];
$presets = $data['presets'] ?? [];
$presetName = $data['preset_name'] ?? 'dividend_stocks';
$presetLabel = $data['preset_label'] ?? 'Dividend Stocks';
$sectors = $data['sectors'] ?? [];
$currentSector = $data['current_sector'] ?? '';
$currentSort = $data['current_sort'] ?? '';

function translate_screener_symbol(string $raw): string {
    $sym = $raw;
    foreach (['NASDAQ:', 'NYSE:', 'TSE:', 'TSX:', 'NEO:'] as $prefix) {
        if (str_starts_with($sym, $prefix)) {
            $sym = substr($sym, strlen($prefix));
            break;
        }
    }
    if (str_ends_with($sym, '.TO') || str_ends_with($sym, '.UN.TO')) {
        return $sym;
    }
    $lower = strtolower($sym);
    if (str_contains($lower, '.un') || (strlen($sym) > 3 && $sym[-3] === '.' && ctype_alpha($sym[-2] . $sym[-1]))) {
        return $sym . '.TO';
    }
    return $sym . '.TO';
}

function screenerSortLink(string $field, string $label, string $preset, string $currentSort, ?string $sector = null): string {
    $url = '?action=screener&preset=' . urlencode($preset) . '&sort=' . urlencode($field);
    if ($sector !== null && $sector !== '') {
        $url .= '&sector=' . urlencode($sector);
    }
    $arrow = '';
    if ($currentSort === $field) {
        $arrow = ' ▲';
    } elseif ($currentSort === $field . '_desc') {
        $arrow = ' ▼';
    }
    return '<a href="' . htmlspecialchars($url) . '" class="sort-link" style="color:var(--text);text-decoration:none;">' . htmlspecialchars($label) . $arrow . '</a>';
}
?>

<div class="card" id="screener-card">
    <div class="card-header">📊 TradingView Stock Screener</div>

    <div style="margin-bottom: 16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
        <label for="screener-preset" style="margin-right:8px;">Preset:</label>
        <select id="screener-preset" style="padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <?php foreach ($presets as $key => $info): ?>
                <option value="<?php echo $key; ?>" <?php echo $presetName === $key ? 'selected' : ''; ?>><?php echo htmlspecialchars($info['label']); ?></option>
            <?php endforeach; ?>
        </select>
        <label for="screener-sector" style="margin-right:8px;">Sector:</label>
        <select id="screener-sector" style="padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <option value="">All Sectors</option>
            <?php foreach ($sectors as $sec): ?>
                <option value="<?php echo htmlspecialchars($sec); ?>" <?php echo $currentSector === $sec ? 'selected' : ''; ?>><?php echo htmlspecialchars($sec); ?></option>
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
                            <th><?php echo screenerSortLink('symbol', 'Symbol', $presetName, $currentSort, $currentSector); ?></th>
                            <th><?php echo screenerSortLink('name', 'Name', $presetName, $currentSort, $currentSector); ?></th>
                            <th class="r"><?php echo screenerSortLink('close', 'Price', $presetName, $currentSort, $currentSector); ?></th>
                            <th class="r"><?php echo screenerSortLink('change', 'Change %', $presetName, $currentSort, $currentSector); ?></th>
                            <th class="r"><?php echo screenerSortLink('Perf.Y', '1Y Perf', $presetName, $currentSort, $currentSector); ?></th>
                            <th class="r"><?php echo screenerSortLink('dividends_yield_current', 'Yield %', $presetName, $currentSort, $currentSector); ?></th>
                            <th class="r"><?php echo screenerSortLink('price_earnings_ttm', 'P/E', $presetName, $currentSort, $currentSector); ?></th>
                            <th class="r"><?php echo screenerSortLink('return_on_equity', 'ROE %', $presetName, $currentSort, $currentSector); ?></th>
                            <th class="r"><?php echo screenerSortLink('gross_margin_ttm', 'Gross Margin %', $presetName, $currentSort, $currentSector); ?></th>
                            <th><?php echo screenerSortLink('sector', 'Sector', $presetName, $currentSort, $currentSector); ?></th>
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
                                <td class="r"><?php echo $m['dividends_yield_current'] !== null && $m['dividends_yield_current'] !== '' ? number_format((float)$m['dividends_yield_current'], 2) . '%' : '-'; ?></td>
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
    const presetSelect = document.getElementById('screener-preset');
    const sectorSelect = document.getElementById('screener-sector');
    const target = document.getElementById('screener-results');
    if (!presetSelect || !target) return;

    function updateScreener() {
        const url = new URL(window.location.href);
        url.searchParams.set('action', 'api_screener');
        url.searchParams.set('preset', presetSelect.value);
        if (sectorSelect && sectorSelect.value) {
            url.searchParams.set('sector', sectorSelect.value);
        } else {
            url.searchParams.delete('sector');
        }
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

    presetSelect.addEventListener('change', updateScreener);
    if (sectorSelect) {
        sectorSelect.addEventListener('change', updateScreener);
    }
})();
</script>
