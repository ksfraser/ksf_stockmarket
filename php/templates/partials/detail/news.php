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
