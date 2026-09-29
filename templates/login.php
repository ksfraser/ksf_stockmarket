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

        <?php if (!empty($success)): ?>
            <div style="background:rgba(129,252,129,0.15);border:1px solid var(--green);color:var(--green);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
                <?php echo htmlspecialchars($success); ?>
            </div>
        <?php endif; ?>

        <!-- OAuth provider buttons -->
        <?php if (!empty($providers) && is_array($providers)): ?>
            <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:20px;">
                <?php foreach ($providers as $name => $meta): ?>
                    <?php
                        $callbackUrl = '?action=oauth-callback&provider=' . urlencode($name);
                        $brandClass  = htmlspecialchars($meta['icon'] ?? 'fa-sign-in-alt');
                        $label       = htmlspecialchars($meta['label'] ?? $name);
                        $help        = htmlspecialchars($meta['help'] ?? '');
                    ?>
                    <a href="<?php echo htmlspecialchars($callbackUrl); ?>"
                       style="display:flex;align-items:center;justify-content:center;gap:10px;
                              padding:12px;border:1px solid var(--border);border-radius:var(--radius);
                              background:var(--card);text-decoration:none;color:var(--text);
                              font-size:0.95em;transition:background 0.15s;"
                       onmouseover="this.style.background='var(--hover)'"
                       onmouseout="this.style.background='var(--card)'">
                        <i class="fab <?php echo $brandClass; ?>" style="font-size:1.3em;"></i>
                        <?php echo $label; ?>
                    </a>
                    <?php if ($help !== ''): ?>
                        <div style="font-size:0.75em;color:var(--text3);margin-left:32px;margin-top:-4px;">
                            <?php echo $help; ?>
                        </div>
                    <?php endif; ?>
                <?php endforeach; ?>
            </div>

            <div style="text-align:center;margin-bottom:16px;font-size:0.85em;color:var(--text3);">
                &mdash; or sign in with email &mdash;
            </div>
        <?php endif; ?>

        <!-- Local username/password form -->
        <form method="POST" action="?action=login">
            <input type="hidden" name="csrf_token" value="<?php echo htmlspecialchars($csrf_token ?? ''); ?>">

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

        <div style="text-align:center;margin-top:16px;">
            <a href="?action=forgot-password" style="font-size:0.85em;color:var(--accent);text-decoration:none;">
                Forgot password?
            </a>
            &nbsp;&middot;&nbsp;
            <a href="?action=register" style="font-size:0.85em;color:var(--accent);text-decoration:none;">
                Create account
            </a>
        </div>

        <div style="text-align:center;margin-top:12px;font-size:0.8em;color:var(--text3);">
            Default: admin / admin123
        </div>
    </div>
</div>
