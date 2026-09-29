<?php $pageTitle = 'Forgot Password'; ?>
<div style="max-width:420px;margin:60px auto;">
    <div class="card">
        <div class="card-header" style="text-align:center;font-size:1.2em;">
            &#x1F989; OWL Investment Dashboard
        </div>

        <div style="font-size:0.9em;color:var(--text3);margin-bottom:16px;text-align:center;">
            Enter your email address and we'll send you a link to reset your password.
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

        <form method="POST" action="?action=forgot-password">
            <input type="hidden" name="csrf_token" value="<?php echo htmlspecialchars($csrf_token ?? ''); ?>">

            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Email Address</label>
                <input type="email" name="email" required
                       value="<?php echo htmlspecialchars($_POST['email'] ?? ''); ?>"
                       style="width:100%;">
            </div>

            <button type="submit" class="btn" style="width:100%;padding:12px;font-size:1em;">
                Send Reset Link
            </button>
        </form>

        <div style="text-align:center;margin-top:16px;">
            <a href="?action=login" style="font-size:0.85em;color:var(--accent);text-decoration:none;">
                Back to login
            </a>
        </div>
    </div>
</div>
