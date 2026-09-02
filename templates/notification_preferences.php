<?php
require_once __DIR__ . '/partials/helpers.php';
$prefs = $data['prefs'] ?? [];
$user = $data['user'] ?? [];
?>
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">📬 Advisor Notification Preferences</div>
    <p class="muted">Choose how your hired advisors reach you with recommendations.</p>

    <form method="post">
        <div style="margin-top:12px;">
            <label style="display:block;margin-bottom:6px;"><strong>Email</strong></label>
            <input type="email" name="email" value="<?= htmlspecialchars($prefs['email'] ?? $user['email'] ?? '') ?>"
                   placeholder="you@example.com" style="width:100%;padding:8px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <label style="display:block;margin-top:10px;">
                <input type="checkbox" name="advisor_notify_email" value="1" <?= (!empty($prefs['advisor_notify_email']) && $prefs['advisor_notify_email'] === '1') ? 'checked' : '' ?>>
                Send advisor recommendations to email
            </label>
        </div>

        <div style="margin-top:18px;">
            <label style="display:block;margin-bottom:6px;"><strong>Discord</strong></label>
            <label style="display:block;margin-bottom:10px;">
                <input type="checkbox" name="advisor_notify_discord_dm" value="1" <?= (!empty($prefs['advisor_notify_discord_dm']) && $prefs['advisor_notify_discord_dm'] === '1') ? 'checked' : '' ?>>
                Send advisor recommendations as Discord DM
            </label>
            <input type="text" name="advisor_discord_user_id" value="<?= htmlspecialchars($prefs['advisor_discord_user_id'] ?? '') ?>"
                   placeholder="Discord user ID (numeric snowflake)" style="width:100%;padding:8px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <label style="display:block;margin-top:10px;">
                <input type="checkbox" name="advisor_notify_discord_channel" value="1" <?= (!empty($prefs['advisor_notify_discord_channel']) && $prefs['advisor_notify_discord_channel'] === '1') ? 'checked' : '' ?>>
                Send advisor recommendations to a Discord channel
            </label>
            <input type="text" name="advisor_discord_channel_id" value="<?= htmlspecialchars($prefs['advisor_discord_channel_id'] ?? '') ?>"
                   placeholder="Discord channel ID" style="width:100%;padding:8px 10px;margin-top:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>

        <div style="margin-top:18px;">
            <label style="display:block;margin-bottom:6px;"><strong>WhatsApp</strong></label>
            <label style="display:block;margin-bottom:10px;">
                <input type="checkbox" name="advisor_notify_whatsapp" value="1" <?= (!empty($prefs['advisor_notify_whatsapp']) && $prefs['advisor_notify_whatsapp'] === '1') ? 'checked' : '' ?>>
                Send advisor recommendations to WhatsApp
            </label>
            <input type="text" name="advisor_whatsapp_number" value="<?= htmlspecialchars($prefs['advisor_whatsapp_number'] ?? '') ?>"
                   placeholder="+15551234567" style="width:100%;padding:8px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
        </div>

        <div style="margin-top:18px;">
            <button class="btn" type="submit">Save Preferences</button>
        </div>
    </form>
</div>

<div style="margin-top:16px;text-align:center;">
    <a class="btn" href="?action=my_recommendations">My Recommendations</a>
    <a class="btn" href="?action=hire_advisors" style="background:var(--bg2);color:var(--text);margin-left:8px;">Hire Advisors</a>
</div>
