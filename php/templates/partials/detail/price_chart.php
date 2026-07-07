<div class="card" style="margin-top:12px;">
    <div class="card-header">Price & Volume — 250 Days</div>
    <div style="height:400px; width:100%;"><canvas id="priceChart" style="display:block; width:100%; height:100%;"></canvas></div>
    <div style="display:flex; gap:16px; padding:8px 12px; font-size:0.8em; color:var(--text3); flex-wrap:wrap;">
        <span><span style="color:#4CAF50">━━</span> Price</span>
        <span><span style="color:#4CAF50">▍</span> Volume (green=up, red=down)</span>
        <span><span style="color:#FFC107">━━</span> Vol Avg 22d</span>
        <span><span style="color:#9C27B0">━━</span> Vol Avg 63d</span>
        <?php if ($entryPrice): ?><span><span style="color:#FF9800">━━</span> Entry $<?= number_format($entryPrice, 2) ?></span><?php endif; ?>
        <?php if ($stopPrice): ?><span><span style="color:#f44336">━━</span> Trailing Stop $<?= number_format($stopPrice, 2) ?></span><?php endif; ?>
        <?php if ($consensusPrice): ?><span><span style="color:#9C27B0">━━</span> Analyst Consensus $<?= number_format($consensusPrice, 2) ?></span><?php endif; ?>
        <span><span style="color:#FFC107">▲</span> Individual Analyst</span>
        <span><span style="color:red">●</span> News Event</span>
    </div>
</div>
