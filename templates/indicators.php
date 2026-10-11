<?php
/**
 * Indicators detail template — focuses on trend visualization.
 * Reuses data from detail template.
 */
$s = $data['symbol'] ?? 'Unknown';
$indicators = $data['indicators'] ?? [];
$indHistory = $data['ind_history'] ?? [];
$latest = $data['latest'] ?? [];
?>

<h1 style="margin-bottom:8px">
    <a href="?action=detail&symbol=<?= urlencode($s) ?>"><?= htmlspecialchars($s) ?></a> — Indicators
</h1>
<div style="color:var(--text3); margin-bottom:20px">As of <?= htmlspecialchars($latest['price_date'] ?? 'unknown') ?></div>

<!-- Category: Trend -->
<div class="card">
    <div class="card-header">Trend Indicators</div>
    <div class="ind-grid">
        <?php
        $trend = ['sma_5','sma_10','sma_20','sma_50','sma_100','sma_200','ema_14','ema_20','ema_50'];
        foreach ($trend as $k) {
            if (isset($indicators[$k])): ?>
                <div class="ind-item">
                    <div class="ind-name"><?= htmlspecialchars(strtoupper($k)) ?></div>
                    <div class="ind-value">$<?= number_format($indicators[$k], 2) ?></div>
                </div>
            <?php endif;
        }

        // Price vs MAs
        if (isset($latest['close'])) {
            $price = $latest['close'];
            foreach (['sma_50','sma_200'] as $ma) {
                if (isset($indicators[$ma]) && $indicators[$ma] > 0) {
                    $diff = (($price / $indicators[$ma]) - 1) * 100;
                    $color = $diff >= 0 ? 'var(--green)' : 'var(--red)';
                    ?>
                    <div class="ind-item">
                        <div class="ind-name">vs <?= strtoupper($ma) ?></div>
                        <div class="ind-value" style="color:<?= $color ?>"><?= $diff >= 0 ? '+' : '' ?><?= number_format($diff, 2) ?>%</div>
                    </div>
                <?php }
            }
        }
        ?>
    </div>
</div>

<!-- Category: Momentum -->
<div class="card">
    <div class="card-header">Momentum Indicators</div>
    <div class="ind-grid">
        <?php
        $momentum = ['rsi_14','rsi_7','stoch_k_14','stoch_d_14','macd','macd_signal','macd_hist','roc_14','cmo_14','willr_14','cci_14'];
        foreach ($momentum as $k) {
            if (isset($indicators[$k])): ?>
                <div class="ind-item">
                    <div class="ind-name"><?= htmlspecialchars(strtoupper($k)) ?></div>
                    <div class="ind-value"><?= number_format($indicators[$k], 4) ?></div>
                </div>
            <?php endif;
        }
        ?>
    </div>
</div>

<!-- Category: Volatility -->
<div class="card">
    <div class="card-header">Volatility Indicators</div>
    <div class="ind-grid">
        <?php
        $vol = ['atr_14','atr_7','atr_20','natr_14','natr_7','natr_20'];
        foreach ($vol as $k) {
            if (isset($indicators[$k])): ?>
                <div class="ind-item">
                    <div class="ind-name"><?= htmlspecialchars(strtoupper($k)) ?></div>
                    <div class="ind-value"><?= number_format($indicators[$k], 4) ?></div>
                </div>
            <?php endif;
        }

        // Bollinger Band position
        if (isset($indicators['bb_20_2.0_upper'], $indicators['bb_20_2.0_lower'], $latest['close'])) {
            $range = $indicators['bb_20_2.0_upper'] - $indicators['bb_20_2.0_lower'];
            $pos = $range > 0 ? (($latest['close'] - $indicators['bb_20_2.0_lower']) / $range) * 100 : 50;
            ?>
            <div class="ind-item">
                <div class="ind-name">BB Position</div>
                <div class="ind-value"><?= number_format($pos, 1) ?>%</div>
                <div class="bar"><div class="bar-fill" style="width:<?= $pos ?>%; background:<?= $pos > 80 ? 'var(--red)' : ($pos < 20 ? 'var(--green)' : 'var(--accent)') ?>"></div></div>
            </div>
        <?php } ?>
    </div>
</div>

<!-- Category: Volume -->
<div class="card">
    <div class="card-header">Volume Indicators</div>
    <div class="ind-grid">
        <?php if (isset($latest['volume'])): ?>
            <div class="ind-item">
                <div class="ind-name">Current Volume</div>
                <div class="ind-value"><?= fmt_num($latest['volume']) ?></div>
            </div>
        <?php endif;
        $volInd = ['obv','ad','adosc'];
        foreach ($volInd as $k) {
            if (isset($indicators[$k])): ?>
                <div class="ind-item">
                    <div class="ind-name"><?= htmlspecialchars(strtoupper($k)) ?></div>
                    <div class="ind-value"><?= fmt_num($indicators[$k]) ?></div>
                </div>
            <?php endif;
        } ?>
    </div>
</div>

<!-- All raw indicators -->
<details>
    <summary style="cursor:pointer; color:var(--text3)">Show all <?= count($indicators) ?> raw indicator values</summary>
    <div style="margin-top:12px; font-family:monospace; font-size:0.8em; background:var(--bg3); padding:16px; border-radius:var(--radius); max-height:400px; overflow:auto">
    <?php foreach ($indicators as $k => $v): ?>
        <div><span style="color:var(--accent)"><?= htmlspecialchars($k) ?>:</span> <?= htmlspecialchars((string)$v) ?></div>
    <?php endforeach; ?>
    </div>
</details>
