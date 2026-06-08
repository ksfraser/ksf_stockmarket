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
        <div class="stat-value"><?= $fundamentals['trailing_pe'] ? number_format($fundamentals['trailing_pe'], 1) : '—' ?></div>
        <div class="stat-label">P/E (TTM)</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $fundamentals['forward_pe'] ? number_format($fundamentals['forward_pe'], 1) : '—' ?></div>
        <div class="stat-label">Forward P/E</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $fundamentals['dividend_yield'] ? number_format($fundamentals['dividend_yield'] * 100, 2) . '%' : '—' ?></div>
        <div class="stat-label">Div Yield</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $fundamentals['beta'] ? number_format($fundamentals['beta'], 2) : '—' ?></div>
        <div class="stat-label">Beta</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $fundamentals['roe'] ? number_format($fundamentals['roe'] * 100, 1) . '%' : '—' ?></div>
        <div class="stat-label">ROE</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $fundamentals['debt_to_equity'] ? number_format($fundamentals['debt_to_equity'], 1) : '—' ?></div>
        <div class="stat-label">D/E Ratio</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= $fundamentals['profit_margin'] ? number_format($fundamentals['profit_margin'] * 100, 1) . '%' : '—' ?></div>
        <div class="stat-label">Profit Margin</div>
    </div>
</div>

<!-- ===== PRICE/VOLUME CHART ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
        <span>Price & Volume — 250 Days</span>
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
    <div class="card-header">Technical Oscillators</div>
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">
        <div>
            <div style="font-size:0.9em; font-weight:600; margin-bottom:4px;">RSI (14)</div>
            <div id="rsiChart" style="height:180px;"></div>
        </div>
        <div>
            <div style="font-size:0.9em; font-weight:600; margin-bottom:4px;">MACD (12,26,9)</div>
            <div id="macdChart" style="height:180px;"></div>
        </div>
        <div>
            <div style="font-size:0.9em; font-weight:600; margin-bottom:4px;">Stochastic (14,3,3)</div>
            <div id="stochChart" style="height:180px;"></div>
        </div>
    </div>
</div>

<!-- ===== VOLATILITY & BOLLINGER BANDS ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Volatility (ATR) & Bollinger Bands</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
        <div>
            <div id="atrChart" style="height:200px;"></div>
        </div>
        <div>
            <div id="bbChart" style="height:200px;"></div>
        </div>
    </div>
</div>

<!-- ===== MARKOV REGIME ANALYSIS ===== -->
<?php if (!empty($regime['current_regime'])): ?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Markov Regime Analysis (20-day rolling return)</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start;">
        <div>
            <h4>Current Regime: 
                <span style="padding:4px 12px;border-radius:4px;font-weight:600;
                    <?= $regime['current_regime'] === 'Bull' ? 'background:#84bba1;color:#1a1a1a;' : 
                        ($regime['current_regime'] === 'Bear' ? 'background:#c57f86;color:#1a1a1a;' : 
                        'background:#a4abb7;color:#1a1a1a;') ?>">
                    <?= htmlspecialchars($regime['current_regime']) ?>
                </span>
            </h4>
            <p style="font-size:0.85em;color:var(--text3);margin-top:8px;">
                Market state detection using 5% rolling return threshold.
            </p>
        </div>
        <div>
            <h4 style="margin-top:0;">Stationary Distribution</h4>
            <table style="width:100%;font-size:0.9em;">
                <tr><td>Bear</td><td class="r"><?= ($regime['stationary_distribution']['Bear'] ?? 0) * 100 ?>%</td></tr>
                <tr><td>Sideways</td><td class="r"><?= ($regime['stationary_distribution']['Sideways'] ?? 0) * 100 ?>%</td></tr>
                <tr><td>Bull</td><td class="r"><?= ($regime['stationary_distribution']['Bull'] ?? 0) * 100 ?>%</td></tr>
            </table>
        </div>
    </div>
    
    <?php if (!empty($regime['transition_matrix'])): ?>
    <div style="margin-top:12px;">
        <h4 style="margin-bottom:8px;">Transition Matrix (3×3)</h4>
        <table style="width:100%;font-size:0.85em;border-collapse:collapse;">
            <thead>
                <tr>
                    <th></th>
                    <th class="c">Bear</th>
                    <th class="c">Sideways</th>
                    <th class="c">Bull</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach (['Bear', 'Sideways', 'Bull'] as $from): ?>
                <tr>
                    <td style="font-weight:600;"><?= $from ?></td>
                    <?php foreach (['Bear', 'Sideways', 'Bull'] as $to): ?>
                    <td class="c" style="background:<?= ($from === $to) ? 'rgba(128,128,128,0.2)' : 'rgba(255,255,255,0.05)' ?>;">
                        <?= round(($regime['transition_matrix'][$from][$to] ?? 0) * 100, 1) ?>%
                    </td>
                    <?php endforeach; ?>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
    <?php endif; ?>
</div>
<?php endif; ?>

<!-- ===== DIVIDEND DETAILS ===== -->
<?php if (!empty($dividends) || !empty($dividendSafety)): ?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Dividend Details</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
            <h4>Dividend Safety Score: <span style="color:<?= ($dividendSafety['score'] ?? 0) >= 80 ? 'var(--green)' : (($dividendSafety['score'] ?? 0) >= 60 ? 'var(--yellow)' : 'var(--red)') ?>"><?= $dividendSafety['score'] ?? 'N/A' ?></span> <span style="font-size:0.8em; color:var(--text3)">(<?= $dividendSafety['rating'] ?? 'N/A' ?>)</span></h4>
            <table style="width:100%; font-size:0.9em;">
                <tr><td class="text-muted">Payout Ratio</td><td class="r"><?= $fundamentals['payout_ratio'] ? number_format($fundamentals['payout_ratio'] * 100, 1) . '%' : '—' ?></td></tr>
                <tr><td class="text-muted">FCF Coverage</td><td class="r"><?= $dividendSafety['fcf_coverage'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">D/E Ratio</td><td class="r"><?= $dividendSafety['debt_equity'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">Revenue Growth</td><td class="r"><?= $dividendSafety['revenue_growth'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">Annual Dividend</td><td class="r">$<?= number_format($fundamentals['dividend_rate'] ?? 0, 2) ?></td></tr>
                <tr><td class="text-muted">5Y Avg Yield</td><td class="r"><?= $fundamentals['five_year_div_yield'] ? number_format($fundamentals['five_year_div_yield'], 2) . '%' : '—' ?></td></tr>
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
            <div class="stat-value"><?= isset($optionsData['implied_volatility']) ? number_format($optionsData['implied_volatility'] * 100, 1) . '%' : '—' ?></div>
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

<!-- ===== FUNDAMENTALS DEEP DIVE ===== -->
<div class="card" style="margin-top:12px;">
    <div class="card-header">Fundamentals Deep Dive</div>
    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; font-size:0.9em;">
        <div><span class="text-muted">Forward EPS</span><br><strong><?= $fundamentals['forward_eps'] ? '$' . number_format($fundamentals['forward_eps'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">PEG Ratio</span><br><strong><?= $fundamentals['peg_ratio'] ? number_format($fundamentals['peg_ratio'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Price/Book</span><br><strong><?= $fundamentals['price_to_book'] ? number_format($fundamentals['price_to_book'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Price/Sales</span><br><strong><?= $fundamentals['price_to_sales'] ? number_format($fundamentals['price_to_sales'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Book Value</span><br><strong><?= $fundamentals['book_value'] ? '$' . number_format($fundamentals['book_value'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Free Cash Flow</span><br><strong><?= fmt_large_num($fundamentals['free_cash_flow'] ?? null) ?></strong></div>
        <div><span class="text-muted">Operating CF</span><br><strong><?= fmt_large_num($fundamentals['operating_cash_flow'] ?? null) ?></strong></div>
        <div><span class="text-muted">Revenue</span><br><strong><?= fmt_large_num($fundamentals['total_revenue'] ?? null) ?></strong></div>
        <div><span class="text-muted">Revenue Growth</span><br><strong style="color:<?= ($fundamentals['revenue_growth'] ?? 0) > 0 ? 'var(--green)' : 'var(--red)' ?>"><?= $fundamentals['revenue_growth'] ? number_format($fundamentals['revenue_growth'] * 100, 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">Gross Margin</span><br><strong><?= $fundamentals['gross_margin'] ? number_format($fundamentals['gross_margin'] * 100, 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">Operating Margin</span><br><strong><?= $fundamentals['operating_margin'] ? number_format($fundamentals['operating_margin'] * 100, 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">ROA</span><br><strong><?= $fundamentals['roa'] ? number_format($fundamentals['roa'] * 100, 1) . '%' : '—' ?></strong></div>
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
?>
