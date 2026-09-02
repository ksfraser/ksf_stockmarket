<?php require_once __DIR__ . '/partials/helpers.php'; ?>
<a class="btn" href="?action=knowledge_base" style="background:var(--bg2);color:var(--text);margin-bottom:12px;">← All Knowledge Base</a>
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">
        <strong><?= htmlspecialchars($data['article']['title']) ?></strong>
        <span style="margin-left:8px;font-size:0.8em;opacity:0.7;"><?= htmlspecialchars($data['article']['category']) ?></span>
    </div>
    <div class="card-body">
        <?= $data['article']['body'] ?>
    </div>
</div>
