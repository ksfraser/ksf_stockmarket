<?php require_once __DIR__ . '/partials/helpers.php'; ?>
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">
        <strong>📚 Knowledge Base</strong>
    </div>
    <div class="card-body">
        <p style="margin-bottom:12px;">Core principles on wealth, investing, and financial behavior.</p>
        <div style="display:grid;gap:8px;">
            <?php foreach ($data['articles'] as $a): ?>
                <div style="padding:10px;background:rgba(0,0,0,0.15);border-radius:var(--radius);">
                    <div style="font-size:0.75em;opacity:0.7;text-transform:uppercase;letter-spacing:0.08em;"><?= htmlspecialchars($a['category']) ?></div>
                    <a href="?action=kb_article&slug=<?= urlencode($a['slug']) ?>" style="color:var(--accent);font-weight:600;"><?= htmlspecialchars($a['title']) ?></a>
                </div>
            <?php endforeach; ?>
        </div>
    </div>
</div>
