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
