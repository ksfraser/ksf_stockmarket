<?php
/** External Auth — status messages after OAuth flow. */
$message = $data['message'] ?? '';
$error   = $data['error'] ?? '';
?>
<div class="card">
    <div class="card-header">&#x1F510; External Provider Auth</div>

    <?php if ($message): ?>
        <div style="background:rgba(104,211,145,0.15);border:1px solid var(--green);color:var(--green);padding:12px;border-radius:var(--radius);margin-bottom:16px;">
            <?= htmlspecialchars($message) ?>
        </div>
    <?php endif; ?>
    <?php if ($error): ?>
        <div style="background:rgba(252,129,129,0.15);border:1px solid var(--red);color:var(--red);padding:12px;border-radius:var(--radius);margin-bottom:16px;">
            <?= htmlspecialchars($error) ?>
        </div>
    <?php endif; ?>

    <p style="margin-bottom:16px;">
        Connect external data providers to enhance the Research Agent.
        Tokens are stored as <strong>[REDACTED]</strong> in the database.
    </p>

    <div style="display:flex;gap:12px;flex-wrap:wrap;">
        <a href="?action=external_auth&view=authorize&provider=reddit" class="btn">Connect Reddit</a>
        <a href="?action=external_auth&view=revoke&provider=reddit" class="btn btn-secondary"
           onclick="return confirm('Disconnect Reddit?')">Disconnect Reddit</a>
    </div>

    <p style="margin-top:16px;color:var(--text3);font-size:0.85em;">
        Configure app credentials in Admin Settings → External Providers.
    </p>
</div>
