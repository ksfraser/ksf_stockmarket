<?php
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
$zacksScore = $data['zacks_score'] ?? [];
$vectorvest = $data['vectorvest'] ?? [];
$sectorRank = $data['sector_rank'] ?? [];
$regime = $data['regime'] ?? [];

$close = $latest['close'] ?? 0;
$prevClose = $latest['prev_close'] ?? 0;
$changePct = $prevClose > 0 ? (($close - $prevClose) / $prevClose) * 100 : 0;
$changeClass = $changePct >= 0 ? 'pnl-positive' : 'pnl-negative';
$changeSign = $changePct >= 0 ? '+' : '';

$entryPrice = $portfolio['cost_basis'] ?? null;
$shares = $portfolio['shares'] ?? null;
$trailingStop = $portfolio['trailing_stop_pct'] ?? 0.10;
$stopPrice = $entryPrice ? $entryPrice * (1 - $trailingStop) : null;

$consensusPrice = 0;
$numTargets = count($analystTargets);
if ($numTargets > 0) {
    $consensusPrice = array_sum(array_column($analystTargets, 'price_target')) / $numTargets;
}

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

$rsiData = [];
$macdData = [];
$stochData = [];
foreach ($indHistory as $ih) {
    $date = $ih['price_date'];
    $rsi = $ih['rsi_14'] ?? $ih['rsi_14_1'] ?? null;
    if ($rsi !== null) $rsiData[] = ['date' => $date, 'value' => round((float)$rsi, 2)];

    $macd = $ih['macd_12_26_9_macd'] ?? $ih['macd'] ?? null;
    $macdSignal = $ih['macd_12_26_9_signal'] ?? $ih['macd_signal'] ?? null;
    if ($macd !== null && $macdSignal !== null) {
        $macdData[] = ['date' => $date, 'macd' => round((float)$macd, 4), 'signal' => round((float)$macdSignal, 4)];
    }

    $stochK = $ih['stoch_14_3_3_k'] ?? $ih['stoch_k_14'] ?? null;
    $stochD = $ih['stoch_14_3_3_d'] ?? $ih['stoch_d_14'] ?? null;
    if ($stochK !== null && $stochD !== null) {
        $stochData[] = ['date' => $date, 'k' => round((float)$stochK, 2), 'd' => round((float)$stochD, 2)];
    }
}

$newsMarkers = [];
foreach ($news as $n) {
    $newsMarkers[] = ['date' => $n['date'], 'title' => $n['title'], 'url' => $n['url'] ?? '#'];
}

$targetMarkers = [];
foreach ($analystTargets as $t) {
    $targetMarkers[] = ['date' => $t['date'], 'price' => (float)$t['price_target'], 'firm' => $t['firm'] ?? '', 'analyst' => $t['analyst_name'] ?? ''];
}

$atrData = [];
foreach ($indHistory as $ih) {
    if (!empty($ih['atr_14'])) $atrData[] = ['date' => $ih['price_date'], 'atr' => round((float)$ih['atr_14'], 4)];
}

$bbData = [];
foreach ($indHistory as $ih) {
    $bbMid = $ih['bb_20_2.0_mid'] ?? $ih['bb_20_2_0_mid'] ?? null;
    if ($bbMid !== null) {
        $bbData[] = [
            'date' => $ih['price_date'],
            'upper' => round((float)($ih['bb_20_2.0_upper'] ?? $ih['bb_20_2_0_upper'] ?? 0), 4),
            'mid' => round((float)$bbMid, 4),
            'lower' => round((float)($ih['bb_20_2.0_lower'] ?? $ih['bb_20_2_0_lower'] ?? 0), 4)
        ];
    }
}
?>

<script>
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
