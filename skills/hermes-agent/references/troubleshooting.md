# Hermes Agent Troubleshooting Reference

## File Editing — When Patch Fails

If `patch(action='replace')` can't find `old_string` after a careful read of the file:

1. Read the full file: `read_file(path, offset=1, limit=2000)`
2. Write a complete corrected version to a temp file: `write_file(path="/tmp/fix.py", content=NEW)`
3. Validate: `terminal("python3 -m py_compile /tmp/fix.py")`
4. Swap: `terminal("cp original.py original.py.bak && cp /tmp/fix.py original.py")`
5. Verify: `terminal("python3 -m py_compile original.py")`

See `references/editing-patterns.md` for the full pattern.

## Email Gateway Issues

### "No home channel set for email" Error
When attempting to send email and receiving:
```
No home channel set for email to determine where to send the message. Either specify a channel directly with 'email:CHANNEL_NAME', or set a home channel via: hermes config set EMAIL_HOME_CHANNEL <channel_id>
```

**Solution:**
1. First, list available email channels:
   ```bash
   send_message(action='list', target='email')
   ```
2. Set the home channel (use quotes for names with spaces):
   ```bash
   hermes config set EMAIL_HOME_CHANNEL "channel-name"
   ```
3. Restart the email gateway:
   ```bash
   hermes gateway restart email
   ```
   or toggle email platform off/on via `hermes gateway setup`

### Email Not Sending After Configuration
If email still fails after setting home channel:
- Check gateway logs: `grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20`
- Verify email credentials in `.env` file
- Ensure email platform is enabled in gateway setup
- Try restarting the entire gateway: `hermes gateway restart`

## WhatsApp Gateway Issues

### Node.js Version Requirements
WhatsApp pairing requires Node.js v20+. If encountering version errors:

**On Fedora/RPM-based systems:**
```bash
# Remove conflicting npm first
sudo dnf remove -y npm
# Install Node.js 20 via NodeSource
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo -E bash -
sudo dnf install -y --best --allowerasing nodejs
```

**On Debian/Ubuntu:**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### QR Code Pairing Failed
If WhatsApp QR code pairing fails:
1. Ensure Node.js v20+ is installed
2. Check WhatsApp gateway logs for specific errors
3. Try removing existing pairing and retrying:
   ```bash
   hermes pairing revoke whatsapp
   hermes whatsapp
   ```
4. Verify phone has active WhatsApp and internet connection

## General Gateway Troubleshooting

### Ghost Connection (Connected but No Targets)
If `gateway status` shows connected but `send_message(action='list')` returns empty:
1. Check logs for: `Channel directory built: 0 target(s)`
2. Verify `ALLOWED_USERS` in `.env` file
3. Restart gateway: `hermes gateway restart`
4. For specific platforms, toggle off/on via `hermes gateway setup`

### Gateway Dies on Session Close
- **SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **WSL2 close**: Requires `systemd=true` in `/etc/wsl.conf` for systemd services

## Model/Provider Issues

### Copilot 403 Errors
GitHub Copilot requires specific OAuth flow:
```bash
hermes model  # Select GitHub Copilot and follow device code flow
```
Regular GitHub tokens (`gh auth login`) do NOT work for Copilot API.

### Auxiliary Tasks Not Working
If vision, compression, or session_search fail silently:
1. Either set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`
2. Or explicitly configure each auxiliary task:
   ```bash
   hermes config set auxiliary.vision.provider <provider>
   hermes config set auxiliary.vision.model <model>
   ```

## Configuration Issues

### Changes Not Taking Effect
- **Tools/skills**: Use `/reset` for new session with updated toolset
- **Config changes**: In gateway: `/restart`; In CLI: exit and relaunch
- **Code changes**: Restart CLI or gateway process

### Config File Encoding (Windows)
Ensure `config.yaml` is saved as UTF-8 without BOM to avoid "No models provided" errors.

### Config Corruption After Updates
Config values can become corrupted from terminal paste operations, editor issues, or interrupted writes. Symptoms include:
- `AttributeError: 'str' object has no attribute 'get'` - A section expected a dict but found a string
- `AttributeError: 'NoneType' object has no attribute 'get'` - A section is null instead of dict
- Unknown toolset warnings (e.g., `Warning: Unknown toolsets: rl`) - Invalid toolset names in platform_toolsets

**Common corruption patterns:**
```yaml
# BAD: API key used as top-level key instead of nested under 'openrouter' section
openrouter: sk-or-v1-xxx...  # This breaks config parsing
custom_providers:
- api_key: "\e[O\e[I..."  # Shell escape sequences from copy/paste

# BAD: Null/empty values where empty dicts are required  
known_plugin_toolsets: null  # Should be: {}
# BAD: Removed/renamed toolsets still listed
platform_toolsets:
  cli:
  - rl  # RL toolset doesn't exist by this name
  - moa # MOA toolset requires explicit enablement
```

**Recovery steps:**
1. Identify the corrupted section: `hermes doctor` shows parsing errors
2. Use `hermes config check` to verify API key configuration
3. Read the raw file to spot malformed lines: look for stray key=values at wrong indentation levels
4. For `.env` corruption: remove duplicate/mangled lines, ensure clean key=value format
5. For `config.yaml` corruption: fix section structure, replace `null` with `{}`, remove invalid toolsets
6. Run `hermes config migrate` to resync to current config version
