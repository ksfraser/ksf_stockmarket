<?php
/**
 * Settings page — per-user preferences.
 */
$settings = $data['settings'] ?? [];
$message = $data['message'] ?? '';
$error = $data['error'] ?? '';
$user = $data['user'] ?? [];
?>

<div class="grid-2">
    <!-- Display Settings -->
    <div class="card">
        <div class="card-header">&#x1F3A8; Display Settings</div>

        <?php if ($message): ?>
            <div style="background:rgba(104,211,145,0.15);border:1px solid var(--green);color:var(--green);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
                <?php echo htmlspecialchars($message); ?>
            </div>
        <?php endif; ?>
        <?php if ($error): ?>
            <div style="background:rgba(252,129,129,0.15);border:1px solid var(--red);color:var(--red);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
                <?php echo htmlspecialchars($error); ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="?action=settings">
            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Color Scheme</label>
                <select name="color_scheme" style="width:100%;">
                    <option value="dark" <?php echo ($settings['color_scheme'] ?? '') === 'dark' ? 'selected' : ''; ?>>Dark (default)</option>
                    <option value="darker" <?php echo ($settings['color_scheme'] ?? '') === 'darker' ? 'selected' : ''; ?>>Darker</option>
                    <option value="nord" <?php echo ($settings['color_scheme'] ?? '') === 'nord' ? 'selected' : ''; ?>>Nord</option>
                </select>
            </div>

            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Font Size</label>
                <select name="font_size" style="width:100%;">
                    <option value="small" <?php echo ($settings['font_size'] ?? '') === 'small' ? 'selected' : ''; ?>>Small</option>
                    <option value="medium" <?php echo ($settings['font_size'] ?? '') === 'medium' ? 'selected' : ''; ?>>Medium (default)</option>
                    <option value="large" <?php echo ($settings['font_size'] ?? '') === 'large' ? 'selected' : ''; ?>>Large</option>
                </select>
            </div>

            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Table Style</label>
                <select name="compact_tables" style="width:100%;">
                    <option value="0" <?php echo ($settings['compact_tables'] ?? '') === '0' ? 'selected' : ''; ?>>Normal</option>
                    <option value="1" <?php echo ($settings['compact_tables'] ?? '') === '1' ? 'selected' : ''; ?>>Compact</option>
                </select>
            </div>

            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Decimal Places</label>
                <select name="decimal_places" style="width:100%;">
                    <?php foreach (['0','1','2','3','4'] as $d): ?>
                        <option value="<?php echo $d; ?>" <?php echo ($settings['decimal_places'] ?? '2') === $d ? 'selected' : ''; ?>><?php echo $d; ?></option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Date Format</label>
                <select name="date_format" style="width:100%;">
                    <option value="Y-m-d" <?php echo ($settings['date_format'] ?? '') === 'Y-m-d' ? 'selected' : ''; ?>>2025-01-15</option>
                    <option value="m/d/Y" <?php echo ($settings['date_format'] ?? '') === 'm/d/Y' ? 'selected' : ''; ?>>01/15/2025</option>
                    <option value="d/m/Y" <?php echo ($settings['date_format'] ?? '') === 'd/m/Y' ? 'selected' : ''; ?>>15/01/2025</option>
                </select>
            </div>

            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Default Landing Page</label>
                <select name="default_page" style="width:100%;">
                    <option value="overview" <?php echo ($settings['default_page'] ?? '') === 'overview' ? 'selected' : ''; ?>>App Dashboard</option>
                    <option value="my_dashboard" <?php echo ($settings['default_page'] ?? '') === 'my_dashboard' ? 'selected' : ''; ?>>My Dashboard</option>
                    <option value="portfolio" <?php echo ($settings['default_page'] ?? '') === 'portfolio' ? 'selected' : ''; ?>>Portfolio</option>
                </select>
            </div>

            <div style="margin-bottom:20px;">
                <label style="display:flex;align-items:center;gap:8px;font-size:0.85em;color:var(--text3);cursor:pointer;">
                    <input type="checkbox" name="show_sparks" value="1" <?php echo ($settings['show_sparks'] ?? '1') === '1' ? 'checked' : ''; ?>>
                    Show mini sparklines in tables
                </label>
            </div>

            <button type="submit" class="btn" style="width:100%;">Save Settings</button>
        </form>
    </div>

    <!-- Sharing Settings -->
    <div class="card">
        <div class="card-header">&#128279; Sharing Settings</div>
        <p class="muted">Share your portfolios and transactions with others. Advisor accounts are globally visible to all users and cannot be changed here.</p>

        <form method="POST" action="?action=settings">
            <?php $isAdvisor = (($user['role'] ?? '') === 'advisor'); ?>
            <div style="margin-bottom:14px;">
                <label style="display:flex;align-items:center;gap:8px;font-size:0.85em;color:var(--text3);cursor:pointer;">
                    <input type="checkbox" name="share_global" value="1" <?php echo ($settings['share_global'] ?? '0') === '1' ? 'checked' : ''; ?> <?php echo $isAdvisor ? 'checked disabled' : ''; ?>>
                    <?php echo $isAdvisor ? 'Globally shared (advisor default — locked)' : 'Make my data visible to everyone'; ?>
                </label>
            </div>

            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Share scope</label>
                <select name="share_scope" style="width:100%;" <?php echo $isAdvisor ? 'disabled' : ''; ?>>
                    <option value="global" <?php echo ($settings['share_scope'] ?? 'global') === 'global' ? 'selected' : ''; ?>>Everyone</option>
                    <option value="selected" <?php echo ($settings['share_scope'] ?? '') === 'selected' ? 'selected' : ''; ?>>Only designated users</option>
                </select>
            </div>

            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Designated users</label>
                <select name="shared_user_ids[]" multiple style="width:100%;height:120px;" <?php echo $isAdvisor ? 'disabled' : ''; ?>>
                    <?php foreach ($all_users as $u): ?>
                        <option value="<?php echo (int)$u['id']; ?>">
                            <?php echo htmlspecialchars(($u['role'] === 'advisor' ? 'ADVISOR ' : '') . $u['username']); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
                <small class="muted">Hold Ctrl/Cmd to select multiple.</small>
            </div>

            <button type="submit" class="btn" style="width:100%;">Save Sharing Settings</button>
        </form>

        <?php if (!empty($shared_with_me)): ?>
            <div style="margin-top:20px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.1);">
                <strong>Users who share with you:</strong>
                <ul style="list-style:none; padding:0; margin:8px 0 0 0;">
                    <?php foreach ($shared_with_me as $u): ?>
                        <li><?php echo htmlspecialchars(($u['role'] === 'advisor' ? 'ADVISOR ' : '') . $u['username']); ?></li>
                    <?php endforeach; ?>
                </ul>
            </div>
        <?php endif; ?>
    </div>

    <!-- Password Change -->
    <div class="card">
        <div class="card-header">&#x1F511; Change Password</div>
        <form method="POST" action="?action=settings">
            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Current Password</label>
                <input type="password" name="current_password" style="width:100%;">
            </div>
            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">New Password</label>
                <input type="password" name="new_password" style="width:100%;">
            </div>
            <div style="margin-bottom:20px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Confirm New Password</label>
                <input type="password" name="new_password_confirm" style="width:100%;">
            </div>
            <button type="submit" class="btn" style="width:100%;">Update Password</button>
        </form>

        <div style="margin-top:24px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.1);">
            <div style="font-size:0.85em;color:var(--text3);">
                <strong>Account:</strong> <?php echo htmlspecialchars($user['username'] ?? ''); ?><br>
                <strong>Role:</strong> <?php echo htmlspecialchars($user['role'] ?? ''); ?><br>
                <strong>Display Name:</strong> <?php echo htmlspecialchars($user['display_name'] ?? ''); ?>
            </div>
        </div>
    </div>

    <!-- External Provider Auth -->
    <div class="card">
        <div class="card-header">&#x1F510; External Data Providers</div>
        <p style="font-size:0.85em;color:var(--text3);margin-bottom:16px;">
            Connect external providers to enhance the Research Agent with live strategy scanning.
            Tokens are stored as <strong>[REDACTED]</strong> and never exposed in logs.
        </p>

        <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
            <a href="?action=external_auth&view=authorize&provider=reddit" class="btn">Connect Reddit</a>
            <a href="?action=external_auth&view=revoke&provider=reddit" class="btn btn-secondary"
               onclick="return confirm('Disconnect Reddit?')">Disconnect Reddit</a>
            <span style="font-size:0.85em;color:var(--text3);">
                Scans r/algotrading, r/quant, r/options, r/investing for strategy ideas.
            </span>
        </div>
    </div>
</div>
