<?php
/**
 * WealthSystem Technical Analysis Detail Narrative
 *
 * Expects: $latest, $indicators, $history
 */
if (empty($latest) && empty($indicators)):
?>
<p class="text-muted">Technical analysis data not yet available for this symbol.</p>
<?php return; endif;

$close = (float)($latest['close'] ?? 0);
$vol = (float)($latest['volume'] ?? 0);
$sma50 = (float)($indicators['sma_50'] ?? 0);
$sma200 = (float)($indicators['sma_200'] ?? 0);
$rsi = (float)($indicators['rsi_14'] ?? 50);
$macd = (float)($indicators['macd_12_26_9_macd'] ?? 0);
$macd_sig = (float)($indicators['macd_12_26_9_signal'] ?? 0);
$stoch_k = (float)($indicators['stoch_14_3_3_k'] ?? 50);
$stoch_d = (float)($indicators['stoch_14_3_3_d'] ?? 50);
$atr = (float)($indicators['atr_14'] ?? 0);
$volatility = ($indicators['volatility_20'] ?? null);
$bb_width = null;
if (!empty($indicators['bb_20_2_0_upper']) && !empty($indicators['bb_20_2_0_lower']) && $close > 0) {
    $bb_width = ((float)$indicators['bb_20_2_0_upper'] - (float)$indicators['bb_20_2_0_lower']) / $close;
}

function taBadge(string $label, string $status): string {
    $map = [
        'bullish'=>'var(--green)',
        'bearish'=>'var(--red)',
        'neutral'=>'var(--yellow)',
        'overbought'=>'#e91e63',
        'oversold'=>'#9c27b0',
    ];
    $bg = match($status){'bullish'=>'var(--green-bg)','bearish'=>'var(--red-bg)','overbought'=>'#fce4ec','oversold'=>'#f3e5f5', default=>'#f5f5f5'};
    $color = $map[$status] ?? 'var(--text1)';
    return '<span style="display:inline-block;padding:3px 8px;border-radius:4px;background:'.$bg.';color:'.$color.';font-size:0.8em;">'.htmlspecialchars($label).'</span>';
}

function taStatus(float $val, float $upper=70, float $lower=30): string {
    if ($val >= $upper) return 'overbought';
    if ($val <= $lower) return 'oversold';
    return 'neutral';
}

$trend = $sma200 > 0 ? ($close > $sma200 ? 'bullish' : 'bearish') : 'neutral';
$macdStatus = ($macd > $macd_sig) ? 'bullish' : 'bearish';
$rsiStatus = taStatus($rsi);
$stochStatus = ($stoch_k > $stoch_d) ? 'bullish' : 'bearish';
if ($stoch_k >= 80 || $stoch_d >= 80) $stochStatus = 'overbought';
if ($stoch_k <= 20 || $stoch_d <= 20) $stochStatus = 'oversold';

$support = $close - ($atr ?: $close*0.02);
$resistance = $close + ($atr ?: $close*0.02);
?>
<div class="stats-grid">
    <div class="stat-card"><div class="stat-value"><?= $trend==='bullish' ? taBadge('Uptrend','bullish') : ($trend==='bearish' ? taBadge('Downtrend','bearish') : taBadge('Range','neutral')) ?></div><div class="stat-label">Trend (price vs SMA200)</div></div>
    <div class="stat-card"><div class="stat-value"><?= taBadge('RSI '.round($rsi,0), $rsiStatus) ?></div><div class="stat-label">RSI 14</div></div>
    <div class="stat-card"><div class="stat-value"><?= taBadge('MACD '.($macd>0?'+':'').round($macd,2), $macdStatus) ?></div><div class="stat-label">MACD vs Signal <?= round($macd_sig,2) ?></div></div>
    <div class="stat-card"><div class="stat-value"><?= taBadge('Stoch '.round($stoch_k,0).'/'.round($stoch_d,0), $stochStatus) ?></div><div class="stat-label">Stochastic %K/%D</div></div>
    <?php if ($atr > 0): ?>
    <div class="stat-card"><div class="stat-value"><?= taBadge('ATR '.round($atr,2), 'neutral') ?></div><div class="stat-label">Volatility / risk buffer</div></div>
    <?php endif; ?>
    <?php if ($bb_width !== null): ?>
    <div class="stat-card"><div class="stat-value"><?= taBadge('BB Width '.round($bb_width*100,1).'%', 'neutral') ?></div><div class="stat-label">Bollinger bandwidth</div></div>
    <?php endif; ?>
</div>
<div style="margin-top:10px; font-size:0.85em; color:var(--text3);">
    Suggested support ≈ $<?= number_format($support,2) ?>; resistance ≈ $<?= number_format($resistance,2) ?>.
    Use stop placement relative to ATR multiples per portfolio rules.
</div>
