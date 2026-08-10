<?php $pageTitle = 'Login'; ?>
<div style="max-width:420px;margin:60px auto;">
    <div class="card">
        <div class="card-header" style="text-align:center;font-size:1.2em;">
            &#x1F989; OWL Investment Dashboard
        </div>

        <?php if (!empty($error)): ?>
            <div style="background:rgba(252,129,129,0.15);border:1px solid var(--red);color:var(--red);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
                <?php echo htmlspecialchars($error); ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="?action=login">
            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Username</label>
                <input type="text" name="username" required autofocus
                       value="<?php echo htmlspecialchars($_POST['username'] ?? ''); ?>"
                       style="width:100%;">
            </div>
            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Password</label>
                <input type="password" name="password" required style="width:100%;">
            </div>
            <div style="margin-bottom:20px;">
                <label style="display:flex;align-items:center;gap:8px;font-size:0.85em;color:var(--text3);cursor:pointer;">
                    <input type="checkbox" name="remember" value="1">
                    Remember me for 30 days
                </label>
            </div>
            <button type="submit" class="btn" style="width:100%;padding:12px;font-size:1em;">
                Sign In
            </button>
        </form>

        <div style="text-align:center;margin-top:16px;font-size:0.85em;color:var(--text3);">
            Default: admin / admin123
        </div>
    </div>
</div>
