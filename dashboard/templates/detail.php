<?php
/**
 * Symbol Detail template.
 * Expects: $data = symbol, latest, history, indicators, ind_history, portfolio, performance
 */
$s = $data['symbol'] ?? 'Unknown';
$latest = $data['latest'] ?? [];
$history = $data['history'] ?? [];
$indicators = $data['indicators'] ?? [];
$indHistory = $data['ind_history'] ?? [];
$portfolio = $data['portfolio'] ?? null;
$perf = $data['performance'] ?? [];
$error = $data['error'] ?? null;

if ($error): ?>
    <div class="card" style="border-color:var(--red)">
        <strong>Error:</strong> <?= htmlspecialchars($error) ?>
    </div>
<?php return; endif;

// Prepare chart data as JSON for the JS charting library
$chartData = json_encode($history, JSON_NUMERIC_CHECK);
$rsiData = json_encode(array_map(function($d) {
    return ['price_date' => $d['price_date'], 'rsi' => $d['rsi_14'] ?? null];
}, $indHistory));
$atrData = json_encode(array_map(function($d) {
    return ['price_date' => $d['price_date'], 'atr' => $d['atr_14'] ?? null];
}, $indHistory));
?>

<!-- Header -->
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px">
    <div>
        <h1 style="font-size:2em; margin-bottom:4px">
            <a href="?action=detail&symbol=<?= urlencode($s) ?>"><?= htmlspecialchars($s) ?></a>
            <?php if ($portfolio): ?>
                <span style="font-size:0.4em; background:var(--accent); color:#fff; padding:2px 8px; border-radius:4px; vertical-align:middle; margin-left:8px">IN PORTFOLIO</span>
            <?php endif; ?>
        </h1>
        <div style="color:var(--text2)"><?= htmlspecialchars($latest['name'] ?? '') ?></div>
        <div style="color:var(--text3); font-size:0.9em">
            <?= htmlspecialchars($latest['exchange'] ?? '') ?> |
            <?= htmlspecialchars($latest['sector'] ?? '') ?> |
            <?= htmlspecialchars($latest['industry'] ?? '') ?>
        </div>
    </div>
    <div style="text-align:right">
        <div style="font-size:2.2em; font-weight:700"><?= fmt_price($latest['close'] ?? null) ?></div>
        <div style="color:var(--text3); font-size:0.85em">As of <?= htmlspecialchars($latest['price_date'] ?? 'unknown') ?></div>
        <?php if ($portfolio): ?>
            <div style="margin-top:8px; font-size:0.9em">
                <span class="text-muted">Cost:</span> $<?= number_format($portfolio['cost_basis'], 2) ?>
                | <span class="text-muted">Shares:</span> <?= number_format($portfolio['shares'], 2) ?>
                <?php
                    $curVal = $portfolio['shares'] * ($latest['close'] ?? 0);
                    $costTot = $portfolio['shares'] * $portfolio['cost_basis'];
                    $pnl = $curVal - $costTot;
                    $pnlPct = $costTot > 0 ? ($pnl / $costTot) * 100 : 0;
                ?>
                <br><span class="<?= $pnl >= 0 ? 'pnl-positive' : 'pnl-negative' ?>">
                    P&amp;L: <?= $pnl >= 0 ? '+' : '' ?>$<?= number_format($pnl, 2) ?> (<?= fmt_pct($pnlPct) ?>)
                </span>
            </div>
        <?php endif; ?>
    </div>
</div>

<!-- Performance -->
<div class="stats-grid" style="grid-template-columns:repeat(5,1fr); margin-bottom:20px">
    <div class="stat-card">
        <div class="stat-value" style="font-size:1.3em"><?= fmt_pct($perf['ytd'] ?? null) ?></div>
        <div class="stat-label">YTD</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" style="font-size:1.3em"><?= fmt_pct($perf['1y'] ?? null) ?></div>
        <div class="stat-label">1 Year</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" style="font-size:1.3em"><?= fmt_pct($perf['3y'] ?? null) ?></div>
        <div class="stat-label">3 Year</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" style="font-size:1.3em"><?= fmt_pct($perf['5y'] ?? null) ?></div>
        <div class="stat-label">5 Year</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" style="font-size:1.3em"><?= fmt_pct($perf['10y'] ?? null) ?></div>
        <div class="stat-label">10 Year</div>
    </div>
</div>

<!-- Price Chart -->
<div class="card">
    <div class="card-header">Price History (250 days)</div>
    <div class="chart-container chart-lg">
        <canvas id="priceChart" data-chart='<?= $chartData ?>' data-type="price"></canvas>
    </div>
</div>

<!-- Indicator Charts -->
<?php if (!empty($indHistory)): ?>
<div class="grid-2">
    <div class="card">
        <div class="card-header">RSI (14)</div>
        <div class="chart-container">
            <canvas id="rsiChart" data-chart='<?= json_encode(array_values(array_filter($rsiData ? json_decode($rsiData, true) : [], fn($d) => $d['rsi'] !== null))) ?>' data-type="indicator" data-key="rsi" data-color="#eab308" data-min="0" data-max="100"></canvas>
        </div>
    </div>
    <div class="card">
        <div class="card-header">ATR (14) — Volatility</div>
        <div class="chart-container">
            <canvas id="atrChart" data-chart='<?= json_encode(array_values(array_filter($atrData ? json_decode($atrData, true) : [], fn($d) => $d['atr'] !== null))) ?>' data-type="indicator" data-key="atr" data-color="#f97316"></canvas>
        </div>
    </div>
</div>
<?php endif; ?>

<!-- Current Indicators -->
<?php if (!empty($indicators)): ?>
<div class="card">
    <div class="card-header">Technical Indicators (Latest — <?= htmlspecialchars($latest['price_date'] ?? '') ?>)</div>
    <div class="ind-grid">
        <?php
        $displayIndicators = [
            'rsi_14' => ['RSI (14)', null, null],
            'rsi_7' => ['RSI (7)', null, null],
            'atr_14' => ['ATR (14)', null, null],
            'natr_14' => ['NATR (14)', null, null],
            'adx_14' => ['ADX (14)', null, null],
            'bb_20_2_0_upper' => ['BB Upper', null, null],
            'bb_20_2_0_lower' => ['BB Lower', null, null],
            'sma_50' => ['SMA 50', null, null],
            'sma_200' => ['SMA 200', null, null],
            'ema_20' => ['EMA 20', null, null],
            'stoch_k_14' => ['Stoch %K', null, null],
            'stoch_d_14' => ['Stoch %D', null, null],
            'macd' => ['MACD', null, null],
            'macd_signal' => ['MACD Signal', null, null],
            'macd_hist' => ['MACD Hist', null, null],
            'obv' => ['OBV', null, null],
            'roc_14' => ['ROC (14)', null, null],
            'cmo_14' => ['CMO (14)', null, null],
            'willr_14' => ['Williams %R', null, null],
            'cci_14' => ['CCI (14)', null, null],
        ];

        // Map indicator keys (they're lowercase in the JSON)
        foreach ($displayIndicators as $key => $info) {
            if (isset($indicators[$key])) {
                $val = $indicators[$key];
                if (is_numeric($val)) {
                    if (abs($val) >= 1000000) {
                        $display = number_format($val / 1000000, 2) . 'M';
                    } elseif (abs($val) >= 100) {
                        $display = number_format($val, 2);
                    } elseif (abs($val) >= 1) {
                        $display = number_format($val, 4);
                    } else {
                        $display = number_format($val, 6);
                    }
                } else {
                    $display = htmlspecialchars((string)$val);
                }

                // Color RSI
                $style = '';
                if (strpos($key, 'rsi') === 0 && is_numeric($val)) {
                    if ($val > 70) $style = ' style="color:var(--red)"';
                    elseif ($val < 30) $style = ' style="color:var(--green)"';
                }
                // Color MACD hist
                if ($key === 'macd_hist' && is_numeric($val)) {
                    $style = $val >= 0 ? ' style="color:var(--green)"' : ' style="color:var(--red)"';
                }
                ?>
                <div class="ind-item">
                    <div class="ind-name"><?= $info[0] ?></div>
                    <div class="ind-value"<?= $style ?>><?= $display ?></div>
                </div>
                <?php
            }
        }
        ?>
    </div>

    <!-- All Indicators Expandable -->
    <details style="margin-top:16px">
        <summary style="cursor:pointer; color:var(--text3); font-size:0.9em">
            Show all <?= count($indicators) ?> indicators
        </summary>
        <div class="ind-grid" style="margin-top:12px">
        <?php foreach ($indicators as $k => $v): if (!is_numeric($v)) continue; ?>
            <div class="ind-item">
                <div class="ind-name"><?= htmlspecialchars($k) ?></div>
                <div class="ind-value" style="font-size:1em"><?= is_numeric($v) ? (abs($v) > 100 ? number_format($v, 2) : number_format($v, 4)) : htmlspecialchars($v) ?></div>
            </div>
        <?php endforeach; ?>
        </div>
    </details>
</div>
<?php endif; ?>

<!-- Recent Price History Table -->
<div class="card">
    <div class="card-header">Recent Price History (Last 30 Days)</div>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th class="r">Open</th>
                <th class="r">High</th>
                <th class="r">Low</th>
                <th class="r">Close</th>
                <th class="r">Volume</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach (array_slice($history, -30) as $row): ?>
            <tr>
                <td><?= fmt_date($row['price_date']) ?></td>
                <td class="r">$<?= number_format($row['open'], 2) ?></td>
                <td class="r">$<?= number_format($row['high'], 2) ?></td>
                <td class="r">$<?= number_format($row['low'], 2) ?></td>
                <td class="r">$<?= number_format($row['close'], 2) ?></td>
                <td class="r"><?= fmt_num($row['volume']) ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>

<!-- Full JSON Download -->
<div class="card">
    <div class="card-header">Raw Data (JSON)</div>
    <a href="?action=api_chart&symbol=<?= urlencode($s) ?>&days=250" target="_blank" class="btn btn-sm">Download Chart Data (JSON)</a>
    <span class="text-muted" style="font-size:0.85em; margin-left:12px">Use this data to import into spreadsheets or external tools</span>
</div>
