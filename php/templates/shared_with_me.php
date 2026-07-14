<?php
/** @var array $data */
$sharers = $data['sharers'] ?? [];
$selectedUserId = $data['selected_user_id'] ?? 0;
$tab = $data['tab'] ?? 'portfolio';
$ownerSummary = $data['owner_summary'] ?? [];
$portfolioData = $data['portfolio_data'] ?? [];
$transactions = $data['transactions'] ?? [];
$GLOBALS['selected_user_id'] = $selectedUserId;
$GLOBALS['tab'] = $tab;
?>

<div class="card">
    <h2>&#128202; Shared with Me</h2>
    <p class="muted">Read-only views of portfolios and transactions shared by other users. Advisor accounts are globally visible to all logged-in users.</p>
</div>

<div style="display:flex; gap:16px; align-items:flex-start;">

    <!-- Sidebar: sharers list -->
    <div class="card" style="width:260px; min-width:220px;">
        <h3>People</h3>
        <?php if (empty($sharers)): ?>
            <p class="muted">No one has shared with you yet.</p>
        <?php else: ?>
            <ul style="list-style:none; padding:0; margin:0;">
                <?php foreach ($sharers as $s): ?>
                    <li style="margin-bottom:6px;">
                        <a href="?action=shared_with_me&user_id=<?php echo (int)$s['id']; ?>&tab=portfolio"
                           style="color:<?php echo ($selectedUserId == $s['id']) ? 'var(--accent)' : 'inherit'; ?>; text-decoration:none; font-weight:600;">
                            <?php echo htmlspecialchars($s['label']); ?>
                        </a>
                        <?php if (!empty($s['is_public'])): ?>
                            <span class="badge" style="background:#2ecc71; color:#fff; font-size:0.7em; padding:1px 6px; border-radius:10px;">public</span>
                        <?php endif; ?>
                    </li>
                <?php endforeach; ?>
            </ul>
        <?php endif; ?>
    </div>

    <!-- Main content -->
    <div class="card" style="flex:1;">
        <?php if (!$selectedUserId): ?>
            <p class="muted">Select a user from the list to view their portfolio or transactions.</p>
        <?php else: ?>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h3>
                    <?php echo htmlspecialchars($ownerSummary['display_name'] ?? $ownerSummary['username'] ?? 'User'); ?>
                    <small style="color:var(--text3); font-weight:400;">
                        (<?php echo htmlspecialchars($ownerSummary['role'] ?? ''); ?>)
                    </small>
                </h3>
                <span class="muted">Read-only</span>
            </div>

            <?php if ($tab === 'transactions'): ?>
                <?php include __DIR__ . '/shared_with_me_transactions.php'; ?>
            <?php else: ?>
                <?php include __DIR__ . '/shared_with_me_portfolio.php'; ?>
            <?php endif; ?>
        <?php endif; ?>
    </div>
</div>
