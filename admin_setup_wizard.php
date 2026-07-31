<?php
/**
 * Setup wizard for external API keys / OAuth credentials.
 * Admin-only page with step-by-step guides for each provider.
 */
$settings = $data['settings'] ?? [];
?>
<div class="card" style="max-width:900px;margin:0 auto 24px;">
    <div class="card-header">&#x1F6E0; External Provider Setup Wizard</div>
    <p style="color:var(--text3);font-size:0.9em;margin-bottom:16px;">
        This page walks you through obtaining and configuring the API keys and OAuth credentials
        used by the Research Agent, YouTube strategy scanner, and external data sources.
        After copying each key, paste it into <strong>Admin Settings</strong> and click Save.
    </p>

    <!-- LLM Provider -->
    <div style="margin-bottom:24px;padding:16px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">
        <h3 style="margin:0 0 8px;color:var(--accent);">Step 1 — LLM Provider (OpenRouter recommended)</h3>
        <p style="font-size:0.85em;color:var(--text3);margin:0 0 12px;">
            The Research Agent uses an LLM to score external strategy ideas and extract structured
            strategies from YouTube transcripts. <strong>OpenRouter</strong> is the default because
            it gives you access to many models through one API key.
        </p>
        <ol style="font-size:0.85em;color:var(--text3);padding-left:18px;margin:0 0 12px;">
            <li>Go to <a href="https://openrouter.ai/keys" target="_blank">openrouter.ai/keys</a></li>
            <li>Create a new API key.</li>
            <li>Copy the key (starts with <code>sk-or-...</code>).</li>
            <li>In <strong>Admin Settings</strong> paste it into <code>LLM API Key</code>.</li>
            <li>Set <code>LLM Provider</code> = <strong>openrouter</strong> and <code>LLM Model</code> = <strong>anthropic/claude-sonnet-4</strong> (or your preferred model).</li>
            <li>Leave <code>LLM Base URL</code> blank — the system fills it in automatically.</li>
        </ol>
        <p style="font-size:0.8em;color:var(--text3);margin:0;">
            <strong>Other providers:</strong>
            OpenAI → platform.openai.com/api-keys &nbsp;|&nbsp;
            Anthropic → console.anthropic.com &nbsp;|&nbsp;
            Ollama → run locally at <code>localhost:11434</code> (no API key needed) &nbsp;|&nbsp;
            Google → aistudio.google.com/app/apikey
        </p>
    </div>

    <!-- Reddit OAuth -->
    <div style="margin-bottom:24px;padding:16px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">
        <h3 style="margin:0 0 8px;color:var(--accent);">Step 2 — Reddit OAuth App</h3>
        <p style="font-size:0.85em;color:var(--text3);margin:0 0 12px;">
            Authenticated Reddit access removes the 403 rate-limit and lets the Research Agent
            pull posts from <code>r/algotrading</code>, <code>r/quant</code>, etc.
        </p>
        <ol style="font-size:0.85em;color:var(--text3);padding-left:18px;margin:0 0 12px;">
            <li>Log into <a href="https://www.reddit.com/prefs/apps" target="_blank">reddit.com/prefs/apps</a>.</li>
            <li>Click <strong>create app</strong> → choose <strong>web app</strong>.</li>
            <li>Name: anything (e.g. <em>StockResearchBot</em>).</li>
            <li>Redirect URI (exactly): <code>http://192.168.1.102/stockmarket/?action=external_auth&view=callback&provider=reddit</code></li>
            <li>Click <strong>create app</strong>.</li>
            <li>Copy the <strong>client ID</strong> (the string under the app name) and <strong>client secret</strong>.</li>
            <li>Paste them into <strong>Admin Settings → External Provider Auth</strong>.</li>
            <li>Visit <a href="?action=external_auth&view=authorize&provider=reddit">?action=external_auth&view=authorize&provider=reddit</a> to complete the OAuth handshake.</li>
        </ol>
        <p style="font-size:0.8em;color:var(--text3);margin:0;">
            After saving, you can revoke anytime from <strong>Settings → External Auth</strong>.
        </p>
    </div>

    <!-- YouTube Data API -->
    <div style="margin-bottom:24px;padding:16px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">
        <h3 style="margin:0 0 8px;color:var(--accent);">Step 3 — YouTube Data API v3 Key</h3>
        <p style="font-size:0.85em;color:var(--text3);margin:0 0 12px;">
            Required to look up trading channels and their latest videos.
            The transcript fetcher also needs an Apify token (see Step 4).
        </p>
        <ol style="font-size:0.85em;color:var(--text3);padding-left:18px;margin:0 0 12px;">
            <li>Go to the <a href="https://console.cloud.google.com/apis/credentials" target="_blank">Google Cloud Console → Credentials</a>.</li>
            <li>Create or select a project (e.g. <em>stock-research</em>).</li>
            <li>Enable the <strong>YouTube Data API v3</strong> under "APIs & Services → Library".</li>
            <li>In "Credentials" click <strong>Create Credentials → API key</strong>.</li>
            <li>Copy the key (starts with <code>AIzaSy...</code>).</li>
            <li>Paste it into <strong>Admin Settings → YouTube Strategy Channels → YouTube Data API Key</strong>.</li>
            <li>Optionally restrict the key to "YouTube Data API v3" in the Cloud Console.</li>
        </ol>
    </div>

    <!-- Apify Token -->
    <div style="margin-bottom:24px;padding:16px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">
        <h3 style="margin:0 0 8px;color:var(--accent);">Step 4 — Apify Token (Transcript Fetcher)</h3>
        <p style="font-size:0.85em;color:var(--text3);margin:0 0 12px;">
            Apify runs the <code>karamelo/youtube-transcripts</code> actor that extracts captions
            from YouTube videos. You need an Apify account + token.
        </p>
        <ol style="font-size:0.85em;color:var(--text3);padding-left:18px;margin:0 0 12px;">
            <li>Sign up at <a href="https://console.apify.com/sign-up" target="_blank">console.apify.com</a>.</li>
            <li>Open <a href="https://console.apify.com/account#/integrations" target="_blank">Account → Integrations</a>.</li>
            <li>Copy your <strong>API token</strong> (starts with <code>apify_api_...</code>).</li>
            <li>Paste it into <strong>Admin Settings → YouTube Strategy Channels → Apify Token</strong>.</li>
        </ol>
        <p style="font-size:0.8em;color:var(--text3);margin:0;">
            <strong>Free tier note:</strong> Apify includes a generous free monthly usage.
            The transcript actor is inexpensive; YouTube transcripts are typically &lt;$0.01 per video.
        </p>
    </div>

    <!-- Channels -->
    <div style="margin-bottom:24px;padding:16px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">
        <h3 style="margin:0 0 8px;color:var(--accent);">Step 5 — Add Channels to Watch</h3>
        <p style="font-size:0.85em;color:var(--text3);margin:0 0 12px;">
            Paste one or more trading YouTube channels into <strong>Admin Settings</strong>.
            Use either the full URL or just the <code>@handle</code>.
        </p>
        <ul style="font-size:0.85em;color:var(--text3);padding-left:18px;margin:0 0 12px;">
            <li>Format: comma-separated — e.g. <code>@markets,@patrickcasty,https://www.youtube.com/@unknownmoney</code></li>
            <li>Handle-only forms are fine; the system resolves the channel ID automatically.</li>
            <li>The Research Agent pulls the latest 5 videos per channel and appends structured extractions to the daily external brief.</li>
        </ul>
    </div>

    <!-- Quick links -->
    <div style="margin-bottom:8px;padding:16px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">
        <h3 style="margin:0 0 8px;color:var(--accent);">Other Providers (optional)</h3>
        <ul style="font-size:0.85em;color:var(--text3);padding-left:18px;margin:0;">
            <li><strong>TradingView:</strong> no public ideas API; the slot exists for future MCP/auth integration.</li>
            <li><strong>arXiv:</strong> optional API key for higher rate limits — <a href="https://info.arxiv.org/help/oa-tools.html" target="_blank">info.arxiv.org/help/oa-tools.html</a>. Paste into <strong>Admin Settings</strong>.</li>
        </ul>
    </div>
</div>
