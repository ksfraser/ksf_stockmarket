<?php
/**
 * Enhanced Symbol Detail Template
 * 
 * Sections:
 * 1. Header: Symbol, Company Name, Sector, Price, Change
 * 2. Key Stats: Market Cap, P/E, EPS, Div Yield, Beta, etc.
 * 3. Price/Volume Chart with: Trailing Stop line, Entry Point, Analyst targets, News markers
 * 4. Oscillator Charts: RSI, MACD, Stochastic
 * 5. Volatility Chart: ATR, Bollinger Bands, VIX ratio
 * 6. Dividend Details: History, Safety Score, Growth
 * 7. Analyst Predictions: Individual and Average price targets, Ratings
 * 8. Options Data: Open Interest, IV, Put/Call ratio
 * 9. Buffett Analysis: Quality Score, Checklist
 * 10. Recent News
 * 11. Fundamental Data Deep Dive
 */

$sym = $data['symbol'] ?? 'Unknown';
$latest = $data['latest'] ?? [];
$history = $data['history'] ?? [];
$indicators = $data['indicators'] ?? [];
$indHistory = $data['ind_history'] ?? [];
$portfolio = $data['portfolio'] ?? null;
$fundamentals = $data['fundamentals'] ?? [];
$dividendSafety = $data['dividend_safety'] ?? [];
$dividends = $data['dividends'] ?? [];
$analystTargets = $data['analyst_targets'] ?? [];
$analystRatings = $data['analyst_ratings'] ?? [];
$news = $data['news'] ?? [];
$optionsData = $data['options'] ?? [];
$buffettScore = $data['buffett_score'] ?? [];
$sectorRank = $data['sector_rank'] ?? [];
$ws_fundamentals = $data['ws_fundamentals'] ?? [];
$ws_indicators = $data['ws_indicators'] ?? [];
$ws_llm_analysis = $data['ws_llm_analysis'] ?? [];
$ws_evaluations = $data['ws_evaluations'] ?? [];
$iplace = $data['iplace'] ?? [];
$vectorvest = $data['vectorvest'] ?? [];

$close = $latest['close'] ?? 0;
$prevClose = $latest['prev_close'] ?? 0;
$changePct = $prevClose > 0 ? (($close - $prevClose) / $prevClose) * 100 : 0;
$changeClass = $changePct >= 0 ? 'pnl-positive' : 'pnl-negative';
$changeSign = $changePct >= 0 ? '+' : '';

// Portfolio info
$entryPrice = $portfolio['cost_basis'] ?? null;
$shares = $portfolio['shares'] ?? null;
$trailingStop = $portfolio['trailing_stop_pct'] ?? 0.10;
$stopPrice = $entryPrice ? $entryPrice * (1 - $trailingStop) : null;

// Analyst consensus
$consensusPrice = 0;
$numTargets = count($analystTargets);
if ($numTargets > 0) {
    $consensusPrice = array_sum(array_column($analystTargets, 'price_target')) / $numTargets;
}

// Prepare chart data as JSON
$chartData = [];
foreach ($history as $h) {
    $chartData[] = [
        'date' => $h['price_date'],
        'open' => (float)$h['open'],
        'high' => (float)$h['high'],
        'low' => (float)$h['low'],
        'close' => (float)$h['close'],
        'volume' => (int)$h['volume'],
    ];
}
$chartJson = json_encode($chartData);

// Prepare oscillator history
$rsiData = [];
$macdData = [];
$stochData = [];
foreach ($indHistory as $ih) {
    $date = $ih['price_date'];
    if (isset($ih['rsi_14'])) $rsiData[] = ['date' => $date, 'value' => round((float)$ih['rsi_14'], 2)];
    if (isset($ih['macd_12_26_9_macd'])) $macdData[] = ['date' => $date, 'macd' => round((float)$ih['macd_12_26_9_macd'], 4), 'signal' => round((float)($ih['macd_12_26_9_signal'] ?? 0), 4)];
    if (isset($ih['stoch_14_3_3_k'])) $stochData[] = ['date' => $date, 'k' => round((float)$ih['stoch_14_3_3_k'], 2), 'd' => round((float)($ih['stoch_14_3_3_d'] ?? 0), 2)];
}

// News markers for chart
$newsMarkers = [];
foreach ($news as $n) {
    $newsMarkers[] = ['date' => $n['date'], 'title' => $n['title'], 'url' => $n['url'] ?? '#'];
}

// Analyst target markers
$targetMarkers = [];
foreach ($analystTargets as $t) {
    $targetMarkers[] = ['date' => $t['date'], 'price' => (float)$t['price_target'], 'firm' => $t['firm'] ?? '', 'analyst' => $t['analyst_name'] ?? ''];
}

// ATR data for volatility chart
$atrData = [];
foreach ($indHistory as $ih) {
    if (isset($ih['atr_14'])) $atrData[] = ['date' => $ih['price_date'], 'atr' => round((float)$ih['atr_14'], 4)];
}

// Bollinger Band data
$bbData = [];
foreach ($indHistory as $ih) {
    if (isset($ih['bb_20_2_0_mid'])) $bbData[] = ['date' => $ih['price_date'], 'upper' => round((float)$ih['bb_20_2_0_upper'], 4), 'mid' => round((float)$ih['bb_20_2_0_mid'], 4), 'lower' => round((float)$ih['bb_20_2_0_lower'], 4)];
}
?>
<script>
// Global chart data
window.chartData = <?= $chartJson ?>;
window.newsMarkers = <?= json_encode($newsMarkers) ?>;
window.analystTargets = <?= json_encode($targetMarkers) ?>;
window.entryPrice = <?= $entryPrice ? (float)$entryPrice : 'null' ?>;
window.stopPrice = <?= $stopPrice ? (float)$stopPrice : 'null' ?>;
window.consensusPrice = <?= $consensusPrice ? (float)$consensusPrice : 'null' ?>;
window.rsiData = <?= json_encode($rsiData) ?>;
window.macdData = <?= json_encode($macdData) ?>;
window.stochData = <?= json_encode($stochData) ?>;
window.atrData = <?= json_encode($atrData) ?>;
window.bbData = <?= json_encode($bbData) ?>;
window.currentPrice = <?= (float)$close ?>;
</script>

<!-- ===== HEADER ===== -->
<div class="card">
    <div class="card-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div>
            <span style="font-size:1.6em; font-weight:700;"><?= htmlspecialchars($sym) ?></span>
            <span style="font-size:1.1em; color:var(--text2); margin-left:12px;"><?= htmlspecialchars($fundamentals['name'] ?? $latest['name'] ?? '') ?></span>
            <div style="font-size:0.9em; color:var(--text3); margin-top:4px;">
                <?= htmlspecialchars($fundamentals['sector'] ?? $latest['sector'] ?? '') ?> • 
                <?= htmlspecialchars($fundamentals['industry'] ?? $latest['industry'] ?? '') ?> • 
                <?= htmlspecialchars($fundamentals['exchange'] ?? $latest['exchange'] ?? '') ?>
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:1.8em; font-weight:700;">$<?= number_format($close, 2) ?></div>
            <div class="<?= $changeClass ?>" style="font-size:1.1em;">
                <?= $changeSign ?>$<?= number_format($close - $prevClose, 2) ?> (<?= $changeSign ?><?= number_format($changePct, 2) ?>%)
            </div>
            <div style="font-size:0.8em; color:var(--text3);">Vol: <?= number_format($latest['volume'] ?? 0) ?> • As of <?= $latest['price_date'] ?? 'N/A' ?></div>
        </div>
    </div>
</div>

<!-- ===== KEY STATS BAR ===== -->
<div class="stats-grid" style="margin-top:12px;">
    <div class="stat-card">
        <div class="stat-value">$<?= fmt_large_num($fundamentals['market_cap'] ?? null) ?></div>
        <div class="stat-label">Market Cap</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= !empty($fundamentals['trailing_pe']) ? number_format($fundamentals['trailing_pe'], 1) : '—' ?></div>
        <div class="stat-label">P/E (TTM)</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= !empty($fundamentals['forward_pe']) ? number_format($fundamentals['forward_pe'], 1) : '—' ?></div>
        <div class="stat-label">Forward P/E</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= !empty($fundamentals['dividend_yield']) ? number_format($fundamentals['dividend_yield'], 2) . '%' : '—' ?></div>
        <div class="stat-label">Div Yield</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= !empty($fundamentals['beta']) ? number_format($fundamentals['beta'], 2) : '—' ?></div>
        <div class="stat-label">Beta</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= !empty($fundamentals['roe']) ? number_format($fundamentals['roe'], 1) . '%' : '—' ?></div>
        <div class="stat-label">ROE</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= !empty($fundamentals['debt_to_equity']) ? number_format($fundamentals['debt_to_equity'], 1) : '—' ?></div>
        <div class="stat-label">D/E Ratio</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= !empty($fundamentals['profit_margin']) ? number_format($fundamentals['profit_margin'], 1) . '%' : '—' ?></div>
        <div class="stat-label">Profit Margin</div>
    </div>
</div>

<!-- ===== PRICE/VOLUME CHART ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
        <span title="Closing price over 250 trading days. Green line = price; blue bars = volume. Overlays: orange = entry price, red dashed = trailing stop, purple = analyst consensus, yellow triangles = individual analyst targets, red dots = news events.">Price & Volume — 250 Days</span>
        <div style="font-size:0.85em; color:var(--text3);">
            <?php if ($entryPrice): ?>🟢 Entry: $<?= number_format($entryPrice, 2) ?> | <?php endif; ?>
            <?php if ($stopPrice): ?>🔴 Stop: $<?= number_format($stopPrice, 2) ?> | <?php endif; ?>
            <?php if ($consensusPrice): ?>🎯 Consensus: $<?= number_format($consensusPrice, 2) ?><?php endif; ?>
        </div>
    </div>
    <div id="priceChart" style="height:400px; width:100%;"></div>
    <!-- Legend for chart overlays -->
    <div style="display:flex; gap:16px; padding:8px 12px; font-size:0.8em; color:var(--text3); flex-wrap:wrap;">
        <span><span style="color:#4CAF50">━━</span> Price</span>
        <span><span style="color:#2196F3">▍</span> Volume</span>
        <?php if ($entryPrice): ?><span><span style="color:#FF9800">━━</span> Entry $<?= number_format($entryPrice, 2) ?></span><?php endif; ?>
        <?php if ($stopPrice): ?><span><span style="color:#f44336">━━</span> Trailing Stop $<?= number_format($stopPrice, 2) ?></span><?php endif; ?>
        <?php if ($consensusPrice): ?><span><span style="color:#9C27B0">━━</span> Analyst Consensus $<?= number_format($consensusPrice, 2) ?></span><?php endif; ?>
        <span><span style="color:#FFC107">▲</span> Individual Analyst</span>
        <span><span style="color:red">●</span> News Event</span>
    </div>
</div>

<!-- ===== OSCILLATOR CHARTS ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header" title="Momentum oscillators to identify overbought/oversold conditions and trend strength.">Technical Oscillators</div>
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">
        <div>
            <div style="font-size:0.9em; font-weight:600; margin-bottom:4px;" title="Relative Strength Index (14). Measures speed of price changes. Above 70 = overbought; below 30 = oversold.">RSI (14)</div>
            <div id="rsiChart" style="height:180px;"></div>
        </div>
        <div>
            <div style="font-size:0.9em; font-weight:600; margin-bottom:4px;" title="Moving Average Convergence Divergence. Shows relationship between two moving averages. Blue line = MACD; orange line = signal line; green/red bars = histogram (momentum above/below signal).">MACD (12,26,9)</div>
            <div id="macdChart" style="height:180px;"></div>
        </div>
        <div>
            <div style="font-size:0.9em; font-weight:600; margin-bottom:4px;" title="Stochastic Oscillator (14,3,3). Measures current price relative to its range over 14 periods. Blue = %K line; orange = %D signal line. Above 80 = overbought; below 20 = oversold.">Stochastic (14,3,3)</div>
            <div id="stochChart" style="height:180px;"></div>
        </div>
    </div>
</div>

<!-- ===== VOLATILITY & BOLLINGER BANDS ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header" title="Average True Range measures dollar volatility. Bollinger Bands show price volatility envelope (red = upper band, grey dashed = middle SMA, green = lower band). Prices near bands signal potential overextension.">Volatility (ATR) & Bollinger Bands</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
        <div>
            <div id="atrChart" style="height:200px;"></div>
        </div>
        <div>
            <div id="bbChart" style="height:200px;"></div>
        </div>
    </div>
</div>

<!-- ===== DIVIDEND DETAILS ===== -->
<?php if (!empty($dividends) || !empty($dividendSafety)): ?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Dividend Details</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
            <h4>Dividend Safety Score: <span style="color:<?= ($dividendSafety['score'] ?? 0) >= 80 ? 'var(--green)' : (($dividendSafety['score'] ?? 0) >= 60 ? 'var(--yellow)' : 'var(--red)') ?>"><?= $dividendSafety['score'] ?? 'N/A' ?></span> <span style="font-size:0.8em; color:var(--text3)">(<?= $dividendSafety['rating'] ?? 'N/A' ?>)</span></h4>
            <table style="width:100%; font-size:0.9em;">
                <tr><td class="text-muted">Payout Ratio</td><td class="r"><?= !empty($fundamentals['payout_ratio']) ? number_format($fundamentals['payout_ratio'], 1) . '%' : '—' ?></td></tr>
                <tr><td class="text-muted">FCF Coverage</td><td class="r"><?= $dividendSafety['fcf_coverage'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">D/E Ratio</td><td class="r"><?= $dividendSafety['debt_equity'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">Revenue Growth</td><td class="r"><?= $dividendSafety['revenue_growth'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">Annual Dividend</td><td class="r">$<?= number_format($fundamentals['dividend_rate'] ?? 0, 2) ?></td></tr>
                <tr><td class="text-muted">5Y Avg Yield</td><td class="r"><?= !empty($fundamentals['five_year_div_yield']) ? number_format($fundamentals['five_year_div_yield'], 2) . '%' : '—' ?></td></tr>
            </table>
        </div>
        <div>
            <h4>Recent Dividends</h4>
            <table style="width:100%; font-size:0.9em;">
                <thead><tr><th>Date</th><th class="r">Amount</th><th class="r">Yield</th></tr></thead>
                <tbody>
                <?php foreach (array_slice($dividends, 0, 8) as $d): ?>
                    <tr>
                        <td><?= $d['payment_date'] ?></td>
                        <td class="r">$<?= number_format($d['amount'] ?? 0, 4) ?></td>
                        <td class="r"><?= $dividend_yield_at_payment ?? '—' ?></td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
</div>
<?php endif; ?>

<!-- ===== ANALYST PREDICTIONS ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Analyst Predictions</div>
    <?php if ($consensusPrice): ?>
    <div class="stats-grid" style="margin-bottom:12px;">
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($consensusPrice, 2) ?></div>
            <div class="stat-label">Consensus Target</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?= $consensusPrice > $changePct ? '↑' : '↓' ?> <?= number_format((($consensusPrice / $close) - 1) * 100, 1) ?>%</div>
            <div class="stat-label">Upside/Downside</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?= $numTargets ?></div>
            <div class="stat-label">Analysts</div>
        </div>
    </div>
    <?php endif; ?>
    <?php if (!empty($analystRatings)): ?>
    <table style="width:100%; font-size:0.9em;">
        <thead><tr><th>Date</th><th>Firm</th><th>Analyst</th><th>Rating</th><th>Action</th><th class="r">Target</th></tr></thead>
        <tbody>
        <?php foreach (array_slice($analystRatings, 0, 20) as $ar): ?>
            <tr>
                <td><?= $ar['date'] ?></td>
                <td><?= htmlspecialchars($ar['firm'] ?? '') ?></td>
                <td><?= htmlspecialchars($ar['analyst_name'] ?? '') ?></td>
                <td><?= htmlspecialchars($ar['rating'] ?? '') ?></td>
                <td><?= htmlspecialchars($ar['action'] ?? '') ?></td>
                <td class="r"><?= $ar['price_target'] ? '$' . number_format($ar['price_target'], 2) : '—' ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php else: ?>
    <p class="text-muted">No analyst data available yet. Data is being fetched.</p>
    <?php endif; ?>
</div>

<!-- ===== OPTIONS DATA ===== -->
<?php if (!empty($optionsData)): ?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Options Snapshot</div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value"><?= fmt_large_num($optionsData['total_call_oi'] ?? null) ?></div>
            <div class="stat-label">Call Open Interest</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?= fmt_large_num($optionsData['total_put_oi'] ?? null) ?></div>
            <div class="stat-label">Put Open Interest</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?= isset($optionsData['put_call_ratio']) ? number_format($optionsData['put_call_ratio'], 2) : '—' ?></div>
            <div class="stat-label">Put/Call Ratio</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?= isset($optionsData['implied_volatility']) ? number_format($optionsData['implied_volatility'], 1) . '%' : '—' ?></div>
            <div class="stat-label">Implied Volatility</div>
        </div>
    </div>
</div>
<?php endif; ?>

<!-- ===== BUFFETT ANALYSIS ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Buffett Quality Analysis</div>
    <?php if (!empty($buffettScore)): ?>
    <div style="display:flex; gap:20px; align-items:center; margin-bottom:12px;">
        <div style="font-size:2.5em; font-weight:700; color:<?= ($buffettScore['total'] ?? 0) >= 70 ? 'var(--green)' : (($buffettScore['total'] ?? 0) >= 50 ? 'var(--yellow)' : 'var(--red)') ?>"><?= $buffettScore['total'] ?? '—' ?>/100</div>
        <div>
            <?php foreach ($buffettScore['checks'] ?? [] as $check => $passed): ?>
                <span style="display:inline-block; padding:2px 8px; margin:2px; border-radius:4px; font-size:0.8em; background:<?= $passed ? 'var(--green-bg)' : 'var(--red-bg)' ?>; color:<?= $passed ? 'var(--green)' : 'var(--red)' ?>;">
                    <?= $passed ? '✓' : '✗' ?> <?= htmlspecialchars($check) ?>
                </span>
            <?php endforeach; ?>
        </div>
    </div>
    <?php else: ?>
    <p class="text-muted">Buffett analysis not yet generated for this symbol.</p>
    <?php endif; ?>
</div>

<!-- ===== RECENT NEWS ===== -->
<?php if (!empty($news)): ?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Recent News</div>
    <div style="display:flex; flex-direction:column; gap:8px;">
    <?php foreach (array_slice($news, 0, 10) as $n): ?>
        <div style="display:flex; gap:12px; padding:8px 0; border-bottom:1px solid var(--border);">
            <div style="min-width:100px; color:var(--text3); font-size:0.85em;"><?= htmlspecialchars($n['date'] ?? '') ?></div>
            <div>
                <a href="<?= htmlspecialchars($n['url'] ?? '#') ?>" target="_blank" style="color:var(--text1); font-weight:500;"><?= htmlspecialchars($n['title'] ?? '') ?></a>
                <span style="color:var(--text3); font-size:0.8em; margin-left:8px;"><?= htmlspecialchars($n['source'] ?? '') ?></span>
            </div>
        </div>
    <?php endforeach; ?>
    </div>
</div>
<?php endif; ?>

<!-- ===== ZACKS STYLE SCORE ===== -->
<?php
$z = $zacks_score ?? [];
if (!empty($z)):
    $rankColors = [1=>'var(--green)', 2=>'var(--green)', 3=>'var(--yellow)', 4=>'var(--red)', 5=>'var(--red)'];
    $rankColor = $rankColors[$z['rank'] ?? 5] ?? 'var(--text3)';
    $gradeColors = ['A'=>'var(--green)', 'B'=>'#4caf50', 'C'=>'var(--yellow)', 'D'=>'var(--red)', 'F'=>'var(--red)'];
?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Zacks-Style Score</div>
    <div style="display:flex; gap:20px; align-items:center; margin-bottom:12px;">
        <div style="font-size:2.5em; font-weight:700; color:<?= $rankColor ?>">
            <?= htmlspecialchars($z['rank_text'] ?? '—') ?>
        </div>
        <div style="font-size:0.9em; color:var(--text3);">
            Composite <?= htmlspecialchars($z['composite'] ?? '—') ?>/100
        </div>
    </div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value" style="color:<?= $gradeColors[$z['value_grade'] ?? 'C'] ?? 'var(--text1)' ?>"><?= htmlspecialchars($z['value_grade'] ?? '—') ?></div>
            <div class="stat-label">Value (<?= htmlspecialchars($z['value_pct'] ?? '—') ?>/100)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:<?= $gradeColors[$z['growth_grade'] ?? 'C'] ?? 'var(--text1)' ?>"><?= htmlspecialchars($z['growth_grade'] ?? '—') ?></div>
            <div class="stat-label">Growth (<?= htmlspecialchars($z['growth_pct'] ?? '—') ?>/100)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:<?= $gradeColors[$z['momentum_grade'] ?? 'C'] ?? 'var(--text1)' ?>"><?= htmlspecialchars($z['momentum_grade'] ?? '—') ?></div>
            <div class="stat-label">Momentum (<?= htmlspecialchars($z['momentum_pct'] ?? '—') ?>/100)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:<?= $gradeColors[$z['vgm_grade'] ?? 'C'] ?? 'var(--text1)' ?>"><?= htmlspecialchars($z['vgm_grade'] ?? '—') ?></div>
            <div class="stat-label">VGM (<?= htmlspecialchars($z['vgm_pct'] ?? '—') ?>/100)</div>
        </div>
    </div>
    <?php if (!empty($z['checks'])): ?>
    <div style="margin-top:10px; font-size:0.85em;">
        <?php foreach ($z['checks'] as $label => $passed): ?>
            <span style="display:inline-block; padding:3px 8px; margin:2px; border-radius:4px; background:<?= $passed ? 'var(--green-bg)' : 'var(--red-bg)' ?>; color:<?= $passed ? 'var(--green)' : 'var(--red)' ?>;">
                <?= $passed ? '✓' : '✗' ?> <?= htmlspecialchars($label) ?>
            </span>
        <?php endforeach; ?>
    </div>
    <?php endif; ?>
</div>
<?php endif; ?>

<!-- ===== FUNDAMENTALS DEEP DIVE ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Fundamentals Deep Dive</div>
    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; font-size:0.9em;">
        <div><span class="text-muted">Forward EPS</span><br><strong><?= !empty($fundamentals['forward_eps']) ? '$' . number_format($fundamentals['forward_eps'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">PEG Ratio</span><br><strong><?= !empty($fundamentals['peg_ratio']) ? number_format($fundamentals['peg_ratio'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Price/Book</span><br><strong><?= !empty($fundamentals['price_to_book']) ? number_format($fundamentals['price_to_book'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Price/Sales</span><br><strong><?= !empty($fundamentals['price_to_sales']) ? number_format($fundamentals['price_to_sales'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Book Value</span><br><strong><?= !empty($fundamentals['book_value']) ? '$' . number_format($fundamentals['book_value'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Free Cash Flow</span><br><strong><?= fmt_large_num($fundamentals['free_cash_flow'] ?? null) ?></strong></div>
        <div><span class="text-muted">Operating CF</span><br><strong><?= fmt_large_num($fundamentals['operating_cash_flow'] ?? null) ?></strong></div>
        <div><span class="text-muted">Revenue</span><br><strong><?= fmt_large_num($fundamentals['total_revenue'] ?? null) ?></strong></div>
        <div><span class="text-muted">Revenue Growth</span><br><strong style="color:<?= ($fundamentals['revenue_growth'] ?? 0) > 0 ? 'var(--green)' : 'var(--red)' ?>"><?= !empty($fundamentals['revenue_growth']) ? number_format($fundamentals['revenue_growth'], 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">Gross Margin</span><br><strong><?= !empty($fundamentals['gross_margin']) ? number_format($fundamentals['gross_margin'], 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">Operating Margin</span><br><strong><?= !empty($fundamentals['operating_margin']) ? number_format($fundamentals['operating_margin'], 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">ROA</span><br><strong><?= !empty($fundamentals['roa']) ? number_format($fundamentals['roa'], 1) . '%' : '—' ?></strong></div>
    </div>
</div>

<!-- ===== HELPER FUNCTIONS ===== -->
<?php
function fmt_large_num($val) {
    if ($val === null) return '—';
    $val = (float)$val;
    if (abs($val) >= 1e12) return number_format($val / 1e12, 2) . 'T';
    if (abs($val) >= 1e9) return number_format($val / 1e9, 2) . 'B';
    if (abs($val) >= 1e6) return number_format($val / 1e6, 1) . 'M';
    return number_format($val, 0);
}

$buffett_ws = $buffett_score ?? ($data['buffett_score'] ?? []);
if (empty($buffett_ws) && !empty($ws_fundamentals['checks'])) {
    $buffett_ws = $ws_fundamentals;
}
$motley_ws_raw = [];
if (!empty($data['motley'])) {
    $motley_ws_raw = $data['motley'];
} elseif (!empty($ws_evaluations['motley'])) {
    $motley_ws_raw = ['checks' => []];
    foreach ($ws_evaluations['motley'] as $k => $v) {
        $motley_ws_raw['checks'][$k] = !empty($v['grade']) && $v['grade'] !== 'F';
    }
}
$eval_ws = ['domains' => []];
if (!empty($ws_evaluations)) {
    if (!empty($ws_evaluations['evaluation'])) {
        $eval_ws['domains'] = $ws_evaluations['evaluation'];
    } elseif (!empty($ws_evaluations)) {
        $eval_ws['domains'] = $ws_evaluations;
    }
}
$llm_ws = $ws_llm_analysis;
$ws_save_url = htmlspecialchars($_SERVER['REQUEST_URI']);
$ws_symbol = htmlspecialchars($sym);
?>
<?php if (!empty($buffett_ws) || true): ?>
<!-- ===== WEALTHSYSTEM BUFFETT TENETS ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Buffett — 12 Tenets</div>
    <?php include __DIR__ . '/partials/ws/buffett.php'; ?>
    <form method="post" action="<?php echo $ws_save_url; ?>" style="padding:10px;border-top:1px solid var(--border);margin-top:8px;">
        <input type="hidden" name="ws_subaction" value="save_tenets">
        <input type="hidden" name="symbol" value="<?php echo $ws_symbol; ?>">
        <input type="hidden" name="tenets_list" value="<?php echo htmlspecialchars(json_encode(['Moat','Management','Capital Allocation','ROE','Debt','Margins','FCF','CAGR','Competitive Advantage','Owner Earnings','Economic Moat','Pricing Power'])); ?>">
        <?php foreach (['Moat','Management','Capital Allocation','ROE','Debt','Margins','FCF','CAGR','Competitive Advantage','Owner Earnings','Pricing Power'] as $i => $tenet): ?>
            <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                <input type="checkbox" id="tenet_<?php echo $i; ?>" name="tenet_<?php echo md5($tenet); ?>" value="1" <?php echo (!empty($buffett_ws['checks'][$i]['passed']) || (!empty($buffett_ws['checks']) && !empty($buffett_ws['checks'][$i]['passed']))) ? 'checked' : ''; ?>>
                <label for="tenet_<?php echo $i; ?>" style="flex:1;cursor:pointer;"><?php echo htmlspecialchars($tenet); ?></label>
                <input type="text" name="tenet_detail_<?php echo md5($tenet); ?>" placeholder="Note" value="<?php echo htmlspecialchars($buffett_ws['checks'][$i]['detail'] ?? ''); ?>" style="width:220px;">
            </div>
        <?php endforeach; ?>
        <button type="submit" class="btn btn-primary" style="margin-top:8px;">Save Tenets</button>
    </form>
</div>
<?php endif; ?>

<?php if (!empty($motley_ws_raw) || true): ?>
<!-- ===== WEALTHSYSTEM MOTLEY FOOL 10 ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Motley Fool — 10 Criteria</div>
    <?php include __DIR__ . '/partials/ws/motley_fool.php'; ?>
    <form method="post" action="<?php echo $ws_save_url; ?>" style="padding:10px;border-top:1px solid var(--border);margin-top:8px;">
        <input type="hidden" name="ws_subaction" value="save_motley">
        <input type="hidden" name="symbol" value="<?php echo $ws_symbol; ?>">
        <?php
        $mf_keys = ['simplebusiness','reasonablevaluation','corefocus','doubledigitsales','risingcashflow','risingbookvalue','improvingmargins','risingroe','insiderownership','regulardividend'];
        $mf_labels = ['Simple Business','Reasonable Valuation','Core Focus','Double-Digit Sales','Rising Cash Flow','Rising Book Value','Improving Margins','Rising ROE','Insider Ownership','Regular Dividend'];
        foreach ($mf_keys as $idx => $k):
            $checked = (!empty($motley_ws_raw[$k]) || (!empty($motley_ws_raw['checks'][$k]))) ? 'checked' : '';
        ?>
            <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                <input type="checkbox" id="mf_<?php echo $k; ?>" name="motley[<?php echo $k; ?>]" value="1" <?php echo $checked; ?>>
                <label for="mf_<?php echo $k; ?>" style="flex:1;cursor:pointer;"><?php echo htmlspecialchars($mf_labels[$idx]); ?></label>
            </div>
        <?php endforeach; ?>
        <button type="submit" class="btn btn-primary" style="margin-top:8px;">Save Motley</button>
    </form>
</div>
<?php endif; ?>

<!-- ===== WEALTHSYSTEM TECHNICAL ANALYSIS ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Technical Analysis — Narrative</div>
    <?php include __DIR__ . '/partials/ws/technical_analysis.php'; ?>
</div>

<?php if (!empty($eval_ws['domains']) || true): ?>
<!-- ===== WEALTHSYSTEM EVALUATIONS ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Evaluations — 4 Domains</div>
    <?php include __DIR__ . '/partials/ws/evaluations.php'; ?>
    <form method="post" action="<?php echo $ws_save_url; ?>" style="padding:10px;border-top:1px solid var(--border);margin-top:8px;">
        <input type="hidden" name="ws_subaction" value="save_evals">
        <input type="hidden" name="symbol" value="<?php echo $ws_symbol; ?>">
        <input type="hidden" name="eval_json" id="eval_json_input" value="<?php echo htmlspecialchars(json_encode($eval_ws['domains'])); ?>">
        <?php
        $domains = ['business','financial','management','market'];
        $labels = ['Business','Financial','Management','Market'];
        foreach ($domains as $i => $d):
            $score = $eval_ws['domains'][$d]['score'] ?? 0;
            $max = $eval_ws['domains'][$d]['max_score'] ?? 100;
            $grade = $eval_ws['domains'][$d]['grade'] ?? 'F';
            $note = $eval_ws['domains'][$d]['note'] ?? '';
        ?>
            <div style="display:flex;gap:8px;align-items:center;margin:4px 0;flex-wrap:wrap;">
                <strong><?php echo htmlspecialchars($labels[$i]); ?></strong>
                <input type="number" data-domain="<?php echo $d; ?>" data-field="score" value="<?php echo (int)$score; ?>" style="width:70px;" class="eval-field">
                <span>/</span>
                <input type="number" data-domain="<?php echo $d; ?>" data-field="max" value="<?php echo (int)$max; ?>" style="width:70px;" class="eval-field">
                <select data-domain="<?php echo $d; ?>" data-field="grade" class="eval-field">
                    <?php foreach (['A','B','C','D','F'] as $g): ?>
                        <option value="<?php echo $g; ?>" <?php echo $grade === $g ? 'selected' : ''; ?>><?php echo $g; ?></option>
                    <?php endforeach; ?>
                </select>
                <input type="text" data-domain="<?php echo $d; ?>" data-field="note" value="<?php echo htmlspecialchars($note); ?>" placeholder="Note" style="flex:1;min-width:140px;" class="eval-field">
            </div>
        <?php endforeach; ?>
        <button type="submit" class="btn btn-primary" style="margin-top:8px;">Save Evaluations</button>
    </form>
</div>
<?php endif; ?>

<?php if (!empty($llm_ws) || true): ?>
<!-- ===== WEALTHSYSTEM LLM QUALITATIVE ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">LLM Qualitative Analysis</div>
    <?php include __DIR__ . '/partials/ws/llm_analysis.php'; ?>
    <form method="post" action="<?php echo $ws_save_url; ?>" style="padding:10px;border-top:1px solid var(--border);margin-top:8px;">
        <input type="hidden" name="ws_subaction" value="save_llm">
        <input type="hidden" name="symbol" value="<?php echo $ws_symbol; ?>">
        <div style="margin:6px 0;">
            <label>Summary</label>
            <textarea name="llm_summary" rows="4" style="width:100%;"><?php echo htmlspecialchars($llm_ws['summary'] ?? ''); ?></textarea>
        </div>
        <div style="margin:6px 0;">
            <label>Model</label>
            <input type="text" name="llm_model" value="<?php echo htmlspecialchars($llm_ws['model'] ?? 'manual'); ?>">
        </div>
        <button type="submit" class="btn btn-primary">Save LLM Analysis</button>
    </form>
</div>
<?php endif; ?>

<?php if (!empty($vectorvest)): ?>
<!-- ===== VECTORVEST ===== -->
<?php include __DIR__ . '/partials/ws/vectorvest.php'; ?>
<?php endif; ?>

<?php if (!empty($iplace)): ?>
<!-- ===== IPLACE ===== -->
<?php include __DIR__ . '/partials/ws/iplace.php'; ?>
<?php endif; ?>

<?php if (!empty($data['ws_message'])): ?>
<div class="card" style="margin-top:12px;border-left:4px solid var(--accent);">
    <div style="padding:10px;"><?php echo htmlspecialchars($data['ws_message']); ?></div>
</div>
<?php endif; ?>

<script>
(function(){
    var forms = document.querySelectorAll('form[method="post"]');
    for (var i=0;i<forms.length;i++) {
        var f = forms[i];
        if (f.querySelector('input[name="ws_subaction"][value="save_evals"]')) {
            f.addEventListener('submit', function(){
                var hidden = this.querySelector('input[name="eval_json"]');
                if (!hidden) return;
                var obj = {};
                var fields = this.querySelectorAll('.eval-field');
                for (var j=0;j<fields.length;j++) {
                    var el = fields[j];
                    var d = el.getAttribute('data-domain');
                    var k = el.getAttribute('data-field');
                    if (!obj[d]) obj[d] = {};
                    obj[d][k] = el.value;
                }
                hidden.value = JSON.stringify(obj);
            });
        }
    }
})();
</script>
