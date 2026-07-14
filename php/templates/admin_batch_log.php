<?php /** @var array $data */ ?>
<div class="card">
    <div class="card-header">Batch Cleanup Log</div>
    <p><a href="?action=admin_symbols">← Back to Symbol Admin</a></p>
    <pre style="background:rgba(0,0,0,0.2);padding:12px;border-radius:8px;overflow-x:auto;font-size:0.85em;"><?php echo htmlspecialchars($data['batch_log'] ?? ''); ?></pre>
</div>
