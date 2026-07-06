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
        <div style="display:flex; align-items:center; gap:12px;">
            <form method="GET" action="?action=refresh_price" style="display:flex; align-items:center; gap:8px;"
                  onsubmit="return confirm('Refresh price data for <?= htmlspecialchars($sym) ?>? This will re-fetch from yfinance and may take a moment.');">
                <input type="hidden" name="symbol" value="<?= htmlspecialchars($sym) ?>">
                <button type="submit" 
                        style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:4px;font-size:0.85em;cursor:pointer;">
                    ↻ Refresh Price
                </button>
                <label style="font-size:0.82em; color:var(--text3); display:flex; align-items:center; gap:4px; cursor:pointer;">
                    <input type="checkbox" name="full_history" value="1">
                    Full history
                </label>
            </form>
            <div style="text-align:right;">
                <div style="font-size:1.8em; font-weight:700;">$<?= number_format($close, 2) ?></div>
                <div class="<?= $changeClass ?>" style="font-size:1.1em;">
                    <?= $changeSign ?>$<?= number_format($close - $prevClose, 2) ?> (<?= $changeSign ?><?= number_format($changePct, 2) ?>%)
                </div>
                <div style="font-size:0.8em; color:var(--text3);">Vol: <?= number_format($latest['volume'] ?? 0) ?> • As of <?= $latest['price_date'] ?? 'N/A' ?></div>
            </div>
        </div>
    </div>
</div>
