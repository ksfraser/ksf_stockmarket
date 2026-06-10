<?php
/**
 * Admin Settings - System configuration (Discord, LLM, TA parameters).
 * Data: $settings — array of system settings
 */
$settings = $data['settings'] ?? [];
$message = $data['message'] ?? '';
$error = $data['error'] ?? '';
?>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4B0; Discord Configuration</div>

    <?php if ($message): ?>
        <div style="background:rgba(104,211,145,0.15);border:1px solid var(--green);color:var(--green);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
            <?= htmlspecialchars($message) ?>
        </div>
    <?php endif; ?>
    <?php if ($error): ?>
        <div style="background:rgba(252,129,129,0.15);border:1px solid var(--red);color:var(--red);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
            <?= htmlspecialchars($error) ?>
        </div>
    <?php endif; ?>

    <form method="POST" action="?action=admin_settings">
        <div style="margin-bottom:16px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                Alert Webhook URL
            </label>
            <input type="url" name="discord_alert_webhook" value="<?= htmlspecialchars($settings['discord_alert_webhook'] ?? '') ?>" 
                   placeholder="https://discord.com/api/webhooks/.../stock-sell-alerts" style="width:100%;font-family:monospace;">
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                Incoming webhook for posting stock alerts (used by volume spike detector and price alerts).
            </p>
        </div>

        <div style="margin-bottom:16px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                Bot Token
            </label>
            <input type="password" name="discord_bot_token" value="<?= htmlspecialchars($settings['discord_bot_token'] ?? '') ?>" 
                   placeholder="MTQ5NzMyNTE2NTEw..." style="width:100%;font-family:monospace;">
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                Bot token for direct message sending (optional — webhook mode is preferred).
            </p>
        </div>

        <div style="margin-bottom:20px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                General Webhook URL
            </label>
            <input type="url" name="discord_webhook_url" value="<?= htmlspecialchars($settings['discord_webhook_url'] ?? '') ?>" 
                   placeholder="https://discord.com/api/webhooks/.../general" style="width:100%;font-family:monospace;">
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                General webhook for system notifications and cron job output.
            </p>
        </div>

        <button type="submit" class="btn">Save Discord Settings</button>
    </form>
</div>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F9E0; LLM Configuration</div>

    <form method="POST" action="?action=admin_settings">
        <div style="margin-bottom:14px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                LLM Provider
            </label>
            <select name="llm_provider" style="width:100%;">
                <option value="openrouter" <?= ($settings['llm_provider'] ?? '') === 'openrouter' ? 'selected' : '' ?>>OpenRouter (default)</option>
                <option value="ollama" <?= ($settings['llm_provider'] ?? '') === 'ollama' ? 'selected' : '' ?>>Ollama (local)</option>
                <option value="google" <?= ($settings['llm_provider'] ?? '') === 'google' ? 'selected' : '' ?>>Google Gemini</option>
                <option value="openai" <?= ($settings['llm_provider'] ?? '') === 'openai' ? 'selected' : '' ?>>OpenAI Direct</option>
            </select>
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                Select which LLM provider to use for analysis and recommendations.
            </p>
        </div>

        <div style="margin-bottom:14px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                Default Model
            </label>
            <input type="text" name="llm_model" value="<?= htmlspecialchars($settings['llm_model'] ?? 'anthropic/claude-sonnet-4') ?>" 
                   placeholder="model/provider" style="width:100%;font-family:monospace;">
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                Model identifier (e.g., anthropic/claude-sonnet-4, openai/gpt-4.1, google/gemini-2.5-flash).
            </p>
        </div>

        <div style="margin-bottom:14px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                API Key (if not using OpenRouter)
            </label>
            <input type="password" name="llm_api_key" value="<?= htmlspecialchars($settings['llm_api_key'] ?? '') ?>" 
                   placeholder="sk-... or AIza... or your-api-key" style="width:100%;font-family:monospace;">
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                API key for the selected provider. Not needed for OpenRouter (uses global key).
            </p>
        </div>

        <div style="margin-bottom:20px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                Custom Base URL
            </label>
            <input type="url" name="llm_base_url" value="<?= htmlspecialchars($settings['llm_base_url'] ?? '') ?>" 
                   placeholder="https://api.example.com/v1" style="width:100%;font-family:monospace;">
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                Override API endpoint (for self-hosted or proxy endpoints).
            </p>
        </div>

        <button type="submit" class="btn">Save LLM Settings</button>
    </form>
</div>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4CA; Analysis Parameters</div>

    <form method="POST" action="?action=admin_settings">
        <div style="margin-bottom:14px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                TA Run Frequency
            </label>
            <select name="ta_run_frequency" style="width:100%;">
                <option value="daily" <?= ($settings['ta_run_frequency'] ?? '') === 'daily' ? 'selected' : '' ?>>Daily (4:00 AM)</option>
                <option value="twice_daily" <?= ($settings['ta_run_frequency'] ?? '') === 'twice_daily' ? 'selected' : '' ?>>Twice Daily (4:00 AM, 2:00 PM)</option>
                <option value="intraday" <?= ($settings['ta_run_frequency'] ?? '') === 'intraday' ? 'selected' : '' ?>>Intraday (during market hours)</option>
            </select>
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                How often to calculate technical indicators (TA-Lib 340 indicators).
            </p>
        </div>

        <div style="margin-bottom:14px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                Alert Check Frequency
            </label>
            <select name="alert_check_frequency" style="width:100%;">
                <option value="5min" <?= ($settings['alert_check_frequency'] ?? '') === '5min' ? 'selected' : '' ?>>Every 5 minutes</option>
                <option value="15min" <?= ($settings['alert_check_frequency'] ?? '') === '15min' ? 'selected' : '' ?>>Every 15 minutes</option>
                <option value="30min" <?= ($settings['alert_check_frequency'] ?? '') === '30min' ? 'selected' : '' ?>>Every 30 minutes</option>
                <option value="hourly" <?= ($settings['alert_check_frequency'] ?? '') === 'hourly' ? 'selected' : '' ?>>Hourly</option>
            </select>
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                How often to check for price/volume alerts.
            </p>
        </div>

        <div style="margin-bottom:20px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">
                Max Symbols Per Run
            </label>
            <input type="number" name="max_symbols_per_run" value="<?= htmlspecialchars($settings['max_symbols_per_run'] ?? '100') ?>" 
                   min="10" max="1000" step="10" style="width:200px;">
            <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">
                Limit symbols processed per cron run (prevents timeout on large watchlists).
            </p>
        </div>

        <button type="submit" class="btn">Save Analysis Settings</button>
    </form>
</div>

<div class="card" style="margin-bottom:24px;border-color:var(--yellow);">
    <div class="card-header">&#x26A0;&#xFE0F; Current .env Configuration (Read-only)</div>
    <p style="font-size:0.85em;color:var(--text3);margin-bottom:12px;">
        These values are loaded from the system environment. They take effect immediately after saving above.
    </p>
    <table style="width:100%;font-size:0.85em;">
        <tr>
            <td style="padding:8px 0;color:var(--text3);width:40%;"><strong>DISCORD_ALERT_WEBHOOK</strong></td>
            <td style="padding:8px 0;font-family:monospace;color:var(--text2);">
                <?= htmlspecialchars($settings['discord_alert_webhook'] ? str_repeat('*', 20) . '...' . substr($settings['discord_alert_webhook'], -20) : 'Not set') ?>
            </td>
        </tr>
        <tr>
            <td style="padding:8px 0;color:var(--text3);"><strong>OPENROUTER_API_KEY</strong></td>
            <td style="padding:8px 0;font-family:monospace;color:var(--green);">
                <?= isset($_ENV['OPENROUTER_API_KEY']) ? 'Configured (via OpenRouter)' : 'Not set' ?>
            </td>
        </tr>
        <tr>
            <td style="padding:8px 0;color:var(--text3);"><strong>LLM Provider in Use</strong></td>
            <td style="padding:8px 0;color:var(--accent);">
                <?= htmlspecialchars($settings['llm_provider'] ?? 'openrouter (default)') ?>
            </td>
        </tr>
        <tr>
            <td style="padding:8px 0;color:var(--text3);"><strong>Model</strong></td>
            <td style="padding:8px 0;color:var(--accent);">
                <?= htmlspecialchars($settings['llm_model'] ?? 'anthropic/claude-sonnet-4') ?>
            </td>
        </tr>
    </table>
</div>

<div style="display:flex;gap:12px;margin-top:24px;justify-content:center;">
    <a href="?action=alerts_status" class="btn">&larr; Alerts Status</a>
    <a href="?action=admin_symbols" class="btn">&#x1F4B0; Symbol Admin</a>
    <a href="?action=overview" class="btn">Dashboard</a>
</div>