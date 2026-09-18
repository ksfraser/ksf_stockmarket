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

    <div style="margin-bottom:20px; padding:12px; background:var(--bg2); border:1px solid var(--border); border-radius:var(--radius);">
        <strong>Data Pipeline</strong>
        <span style="color:var(--text3); font-size:0.85em; margin-left:8px;">Trigger manual price sync from yfinance</span>
        <br>
        <a href="?action=refresh_all_prices" 
           onclick="return confirm('Refresh ALL symbol prices from yfinance? This can take a long time and will hit rate limits. Consider using the per-symbol refresh on detail pages instead.')"
           style="display:inline-block; margin-top:8px; background:var(--accent); color:#fff; padding:8px 16px; border-radius:4px; text-decoration:none; font-size:0.9em;">
            ↻ Refresh All Prices
        </a>
    </div>

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

<div class="card" style="margin-bottom:24px;border-color:var(--accent);">
    <div class="card-header">&#x1F9E0; LLM Fallback Chain Configuration (FR-13)</div>
    <p style="font-size:0.85em;color:var(--text3);margin-bottom:16px;">
        Configure up to three LLM endpoints in priority order. When the primary endpoint fails
        (timeout, error, rate limit), the system automatically routes to the secondary, then
        to the fallback. Each endpoint has its own URL, model, and API token.
    </p>

    <form method="POST" action="?action=admin_settings">
        <!-- Primary Endpoint -->
        <div style="margin-bottom:16px;padding:12px;background:rgba(104,211,145,0.08);border:1px solid var(--green);border-radius:var(--radius);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="background:var(--green);color:#fff;border-radius:50%;width:24px;height:24px;text-align:center;font-size:0.8em;font-weight:bold;">1</span>
                <strong>Primary Endpoint</strong>
                <span style="font-size:0.75em;color:var(--text3);margin-left:auto;">Highest priority — tried first</span>
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">API URL</label>
                <input type="url" name="llm_primary_url" value="<?= htmlspecialchars($settings['llm_primary_url'] ?? '') ?>"
                       placeholder="https://api.openai.com/v1" style="width:100%;font-family:monospace;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Model</label>
                <input type="text" name="llm_primary_model" value="<?= htmlspecialchars($settings['llm_primary_model'] ?? '') ?>"
                       placeholder="gpt-4o, claude-sonnet-4, llama3.1" style="width:100%;font-family:monospace;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">API Token</label>
                <input type="password" name="llm_primary_token" value="<?= htmlspecialchars($settings['llm_primary_token'] ?? '') ?>"
                       placeholder="sk-... or your-api-key" style="width:100%;font-family:monospace;">
            </div>
            <button type="button" onclick="testConnection('primary')" class="btn" style="padding:4px 12px;font-size:0.85em;">Test Connection</button>
            <span id="primary_health" style="margin-left:8px;font-size:0.85em;"></span>
        </div>

        <!-- Secondary Endpoint -->
        <div style="margin-bottom:16px;padding:12px;background:rgba(250,204,21,0.08);border:1px solid var(--yellow);border-radius:var(--radius);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="background:var(--yellow);color:#000;border-radius:50%;width:24px;height:24px;text-align:center;font-size:0.8em;font-weight:bold;">2</span>
                <strong>Secondary Endpoint</strong>
                <span style="font-size:0.75em;color:var(--text3);margin-left:auto;">Fallback — tried if primary fails</span>
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">API URL</label>
                <input type="url" name="llm_secondary_url" value="<?= htmlspecialchars($settings['llm_secondary_url'] ?? '') ?>"
                       placeholder="https://api.openai.com/v1" style="width:100%;font-family:monospace;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Model</label>
                <input type="text" name="llm_secondary_model" value="<?= htmlspecialchars($settings['llm_secondary_model'] ?? '') ?>"
                       placeholder="gpt-4o, claude-sonnet-4, llama3.1" style="width:100%;font-family:monospace;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">API Token</label>
                <input type="password" name="llm_secondary_token" value="<?= htmlspecialchars($settings['llm_secondary_token'] ?? '') ?>"
                       placeholder="sk-... or your-api-key" style="width:100%;font-family:monospace;">
            </div>
            <button type="button" onclick="testConnection('secondary')" class="btn" style="padding:4px 12px;font-size:0.85em;">Test Connection</button>
            <span id="secondary_health" style="margin-left:8px;font-size:0.85em;"></span>
        </div>

        <!-- Fallback Endpoint -->
        <div style="margin-bottom:20px;padding:12px;background:rgba(252,129,129,0.08);border:1px solid var(--red);border-radius:var(--radius);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="background:var(--red);color:#fff;border-radius:50%;width:24px;height:24px;text-align:center;font-size:0.8em;font-weight:bold;">3</span>
                <strong>Fallback Endpoint</strong>
                <span style="font-size:0.75em;color:var(--text3);margin-left:auto;">Last resort — tried if primary and secondary fail</span>
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">API URL</label>
                <input type="url" name="llm_fallback_url" value="<?= htmlspecialchars($settings['llm_fallback_url'] ?? '') ?>"
                       placeholder="https://api.openai.com/v1" style="width:100%;font-family:monospace;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Model</label>
                <input type="text" name="llm_fallback_model" value="<?= htmlspecialchars($settings['llm_fallback_model'] ?? '') ?>"
                       placeholder="gpt-4o, claude-sonnet-4, llama3.1" style="width:100%;font-family:monospace;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">API Token</label>
                <input type="password" name="llm_fallback_token" value="<?= htmlspecialchars($settings['llm_fallback_token'] ?? '') ?>"
                       placeholder="sk-... or your-api-key" style="width:100%;font-family:monospace;">
            </div>
            <button type="button" onclick="testConnection('fallback')" class="btn" style="padding:4px 12px;font-size:0.85em;">Test Connection</button>
            <span id="fallback_health" style="margin-left:8px;font-size:0.85em;"></span>
        </div>

        <button type="submit" class="btn">Save Fallback Chain</button>
    </form>
</div>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4CA; Advisor-LLM Profile Assignment (FR-13.2)</div>
    <p style="font-size:0.85em;color:var(--text3);margin-bottom:16px;">
        Assign each AI advisor to use a specific LLM endpoint profile (primary, secondary, or fallback).
        This controls which endpoint each advisor's fundamental analysis uses.
    </p>

    <form method="POST" action="?action=admin_settings&section=llm_profiles">
        <table style="width:100%;border-collapse:collapse;font-size:0.9em;">
            <thead>
                <tr style="border-bottom:2px solid var(--border);">
                    <th style="text-align:left;padding:8px;">Advisor</th>
                    <th style="text-align:left;padding:8px;">Current LLM Profile</th>
                    <th style="text-align:left;padding:8px;">Change To</th>
                    <th style="text-align:left;padding:8px;">Action</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:8px;color:var(--text3);">llm-fundamental-value</td>
                    <td style="padding:8px;color:var(--accent);" id="prof_llm-fundamental-value">Loading...</td>
                    <td style="padding:8px;">
                        <select name="profile_change[llm-fundamental-value]" style="font-size:0.85em;">
                            <option value="primary">primary</option>
                            <option value="secondary">secondary</option>
                            <option value="fallback">fallback</option>
                        </select>
                    </td>
                    <td style="padding:8px;">
                        <button type="submit" name="set_profile" value="llm-fundamental-value" class="btn" style="padding:4px 8px;font-size:0.85em;">Set</button>
                    </td>
                </tr>
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:8px;color:var(--text3);">llm-fundamental-growth</td>
                    <td style="padding:8px;color:var(--accent);" id="prof_llm-fundamental-growth">Loading...</td>
                    <td style="padding:8px;">
                        <select name="profile_change[llm-fundamental-growth]" style="font-size:0.85em;">
                            <option value="primary">primary</option>
                            <option value="secondary">secondary</option>
                            <option value="fallback">fallback</option>
                        </select>
                    </td>
                    <td style="padding:8px;">
                        <button type="submit" name="set_profile" value="llm-fundamental-growth" class="btn" style="padding:4px 8px;font-size:0.85em;">Set</button>
                    </td>
                </tr>
            </tbody>
        </table>
        <p style="font-size:0.75em;color:var(--text3);margin-top:12px;">
            Click "Set" to assign the selected profile to the advisor. Changes are saved to the
            <code>advisor_llm_profiles</code> table.
        </p>
    </form>
</div>

<script>
function testConnection(profile) {
    var btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Testing...';
    var healthSpan = document.getElementById(profile + '_health');

    fetch('?action=admin_settings&llm_test=' + profile, {method: 'GET'})
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.available) {
                healthSpan.innerHTML = '<span style="color:var(--green);">Online (' + data.latency_ms + 'ms)</span>';
            } else {
                healthSpan.innerHTML = '<span style="color:var(--red);">Offline: ' + (data.error || 'unknown') + '</span>';
            }
        })
        .catch(function(err) {
            healthSpan.innerHTML = '<span style="color:var(--red);">Error: ' + err.message + '</span>';
        })
        .finally(function() {
            btn.disabled = false;
            btn.textContent = 'Test Connection';
        });
}

// Load current advisor-LLM profile assignments
fetch('?action=admin_settings&llm_profiles=1', {method: 'GET'})
    .then(function(r) { return r.json(); })
    .then(function(profiles) {
        for (var advisor in profiles) {
            var el = document.getElementById('prof_' + advisor);
            if (el) el.textContent = profiles[advisor] || 'primary (default)';
        }
    })
    .catch(function() {});
</script>
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

<div class="card" style="margin-bottom:24px;border-color:var(--accent);">
    <div class="card-header">&#x1F510; External Provider Auth (OAuth / API Keys)</div>
    <p style="font-size:0.85em;color:var(--text3);margin-bottom:16px;">
        Configure app credentials for external data providers. Secrets are stored as <strong>[REDACTED]</strong>
        in the database and used by the Research Agent for authenticated API access.
    </p>

    <form method="post" action="?action=admin_settings" style="margin-bottom:16px;">
        <div style="margin-bottom:12px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Reddit Client ID</label>
            <input type="text" name="external_auth_reddit_client_id"
                   value="<?= htmlspecialchars($settings['external_auth_reddit_client_id'] ?? '') ?>"
                   placeholder="Reddit app client_id" style="width:100%;max-width:400px;">
        </div>
        <div style="margin-bottom:12px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Reddit Client Secret</label>
            <input type="password" name="external_auth_reddit_client_secret"
                   value="<?= htmlspecialchars($settings['external_auth_reddit_client_secret'] ?? '') ?>"
                   placeholder="••••••••••••" style="width:100%;max-width:400px;">
        </div>
        <div style="margin-bottom:12px;">
            <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">TradingView API Key (optional)</label>
            <input type="password" name="external_auth_tradingview_api_key"
                   value="<?= htmlspecialchars($settings['external_auth_tradingview_api_key'] ?? '') ?>"
                   placeholder="••••••••••••" style="width:100%;max-width:400px;">
        </div>
        <div style="margin-bottom:12px;">
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">arXiv API Key (optional)</label>
                <input type="password" name="external_auth_arxiv_api_key"
                       value="<?= htmlspecialchars($settings['external_auth_arxiv_api_key'] ?? '') ?>"
                       placeholder="••••••••••••" style="width:100%;max-width:400px;">
            </div>
            </form>

            <p style="font-size:0.85em;color:var(--text3);">
            After saving, users can connect providers via <strong>Settings → External Auth</strong>.
            Reddit requires a <a href="https://www.reddit.com/prefs/apps" target="_blank">Reddit app</a>
            of type <em>web app</em> with redirect URI
            <code>http://192.168.1.102/stockmarket/?action=external_auth&view=callback&provider=reddit</code>.
            </p>
            </div>

            <div class="card">
            <div class="card-header">&#x1F3A5; YouTube Strategy Channels</div>
            <p style="font-size:0.85em;color:var(--text3);margin-bottom:12px;">
            The Research Agent can watch trading YouTube channels, pull transcripts via Apify,
            extract structured strategies (buy/sell rules, risk, timing), and produce living
            strategy documents. Requires a YouTube Data API key and an Apify token.
            </p>
            <form method="post" action="?action=admin_settings" style="margin-bottom:16px;">
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">YouTube Data API Key</label>
                <input type="password" name="youtube_api_key"
                       value="<?= htmlspecialchars($settings['youtube_api_key'] ?? '') ?>"
                       placeholder="AIzaSy..." style="width:100%;max-width:400px;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Apify Token (transcript fetcher)</label>
                <input type="password" name="apify_token"
                       value="<?= htmlspecialchars($settings['apify_token'] ?? '') ?>"
                       placeholder="apify_api_..." style="width:100%;max-width:400px;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Channels to watch (comma-separated @handles or URLs)</label>
                <textarea name="youtube_watch_channels" rows="4" placeholder="@markets,@patrickcasty,https://www.youtube.com/@channel"
                          style="width:100%;max-width:400px;font-family:monospace;"><?= htmlspecialchars($settings['youtube_watch_channels'] ?? '') ?></textarea>
            </div>
            <button type="submit" class="btn">Save YouTube / Apify Settings</button>
            </form>
            </div>

<div style="display:flex;gap:12px;margin-top:24px;justify-content:center;">
    <a href="?action=alerts_status" class="btn">&larr; Alerts Status</a>
    <a href="?action=admin_symbols" class="btn">&#x1F4B0; Symbol Admin</a>
    <a href="?action=overview" class="btn">Dashboard</a>
</div>