<div class="stats-grid" style="margin-top:12px;">
    <div class="stat-card">
        <div class="stat-value">$<?= fmt_large_num($fundamentals['market_cap'] ?? null) ?></div>
        <div class="stat-label">Market Cap</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= isset($fundamentals['trailing_pe']) ? number_format($fundamentals['trailing_pe'], 1) : '—' ?></div>
        <div class="stat-label">P/E (TTM)</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= isset($fundamentals['forward_pe']) ? number_format($fundamentals['forward_pe'], 1) : '—' ?></div>
        <div class="stat-label">Forward P/E</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= isset($fundamentals['dividend_yield']) ? number_format($fundamentals['dividend_yield'], 2) . '%' : '—' ?></div>
        <div class="stat-label">Div Yield</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= isset($fundamentals['beta']) ? number_format($fundamentals['beta'], 2) : '—' ?></div>
        <div class="stat-label">Beta</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= isset($fundamentals['roe']) ? number_format($fundamentals['roe'], 1) . '%' : '—' ?></div>
        <div class="stat-label">ROE</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= isset($fundamentals['debt_to_equity']) ? number_format($fundamentals['debt_to_equity'], 1) : '—' ?></div>
        <div class="stat-label">D/E Ratio</div>
    </div>
    <div class="stat-card">
        <div class="stat-value"><?= isset($fundamentals['profit_margin']) ? number_format($fundamentals['profit_margin'], 1) . '%' : '—' ?></div>
        <div class="stat-label">Profit Margin</div>
    </div>
    <?php $atrVal = ($data['indicators']['atr_14'] ?? null); ?>
    <div class="stat-card">
        <div class="stat-value"><?= $atrVal !== null && $atrVal !== '' ? '$' . number_format((float)$atrVal, 2) : '—' ?></div>
        <div class="stat-label">ATR (14)</div>
    </div>
    <?php $idealAtr = ($data['indicators']['ideal_atr_factor'] ?? ($h['atr_multiplier'] ?? null)); ?>
    <div class="stat-card">
        <div class="stat-value"><?= $idealAtr !== null && $idealAtr !== '' ? number_format((float)$idealAtr, 2) . '×' : '—' ?></div>
        <div class="stat-label">Ideal ATR Factor</div>
    </div>
</div>
