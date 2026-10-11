---
name: hermes-agent
description: "Configure, extend, or contribute to Hermes Agent."
version: 2.0.0
author: Hermes Agent + Teknium
license: MIT
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode]
---

# Hermes Agent

Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, messaging platforms, and IDEs. It belongs to the same category as Claude Code (Anthropic), Codex (OpenAI), and OpenClaw — autonomous coding and task-execution agents that use tool calling to interact with your system. Hermes works with any LLM provider (OpenRouter, Anthropic, OpenAI, DeepSeek, local models, and 15+ others) and runs on Linux, macOS, and WSL.

What makes Hermes different:

- **Self-improving through skills** — Hermes learns from experience by saving reusable procedures as skills. When it solves a complex problem, discovers a workflow, or gets corrected, it can persist that knowledge as a skill document that loads into future sessions. Skills accumulate over time, making the agent better at your specific tasks and environment.
- **Persistent memory across sessions** — remembers who you are, your preferences, environment details, and lessons learned. Pluggable memory backends (built-in, Honcho, Mem0, and more) let you choose how memory works.
- **Multi-platform gateway** — the same agent runs on Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, and 10+ other platforms with full tool access, not just chat.
- **Provider-agnostic** — swap models and providers mid-workflow without changing anything else. Credential pools rotate across multiple API keys automatically.
- **Profiles** — run multiple independent Hermes instances with isolated configs, sessions, skills, and memory.
- **Extensible** — plugins, MCP servers, custom tools, webhook triggers, cron scheduling, and the full Python ecosystem.

People use Hermes for software development, research, system administration, data analysis, content creation, home automation, and anything else that benefits from an AI agent with persistent context and full system access.

**This skill helps you work with Hermes Agent effectively** — setting it up, configuring features, spawning additional agent instances, troubleshooting issues, finding the right commands and settings, and understanding how the system works when you need to extend or contribute to it.

**Docs:** https://hermes-agent.nousresearch.com/docs/

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Interactive chat (default)
hermes

# Single query
hermes chat -q "What is the capital of France?"

# Setup wizard
hermes setup

# Change model/provider
hermes model

# Check health
hermes doctor
```

---

## CLI Reference

### Global Flags

```
hermes [flags] [command]

  --version, -V             Show version
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --pass-session-id         Include session ID in system prompt
```

No subcommand defaults to `chat`.

### Chat

```
hermes chat [flags]
  -q, --query TEXT          Single query, non-interactive
  -m, --model MODEL         Model (e.g. anthropic/claude-sonnet-4)
  -t, --toolsets LIST       Comma-separated toolsets
  --provider PROVIDER       Force provider (openrouter, anthropic, nous, etc.)
  -v, --verbose             Verbose output
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --source TAG              Session source tag (default: cli)
```

### Configuration

```
hermes setup [section]      Interactive wizard (model|terminal|gateway|tools|agent)
hermes model                Interactive model/provider picker
hermes config               View current config
hermes config edit          Open config.yaml in $EDITOR
hermes config set KEY VAL   Set a config value
hermes config path          Print config.yaml path
hermes config env-path      Print .env path
hermes config check         Check for missing/outdated config
hermes config migrate       Update config with new options
hermes login [--provider P] OAuth login (nous, openai-codex)
hermes logout               Clear stored auth
hermes doctor [--fix]       Check dependencies and config
hermes status [--all]       Show component status
```

### Tools & Skills

```
hermes tools                Interactive tool enable/disable (curses UI)
hermes tools list           Show all tools and status
hermes tools enable NAME    Enable a toolset
hermes tools disable NAME   Disable a toolset

hermes skills list          List installed skills
hermes skills search QUERY  Search the skills hub
hermes skills install ID    Install a skill (ID can be a hub identifier OR a direct https://…/SKILL.md URL; pass --name to override when frontmatter has no name)
hermes skills inspect ID    Preview without installing
hermes skills config        Enable/disable skills per platform
hermes skills check         Check for updates
hermes skills update        Update outdated skills
hermes skills uninstall N   Remove a hub skill
hermes skills publish PATH  Publish to registry
hermes skills browse        Browse all available skills
hermes skills tap add REPO  Add a GitHub repo as skill source
```

### MCP Servers

```
hermes mcp serve            Run Hermes as an MCP server
hermes mcp add NAME         Add an MCP server (--url or --command)
hermes mcp remove NAME      Remove an MCP server
hermes mcp list             List configured servers
hermes mcp test NAME        Test connection
hermes mcp configure NAME   Toggle tool selection
```

### Gateway (Messaging Platforms)

```
hermes gateway run          Start gateway foreground
hermes gateway install      Install as background service
hermes gateway start/stop   Control the service
hermes gateway restart      Restart the service
hermes gateway status       Check status
hermes gateway setup        Configure platforms
```

Supported platforms: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix, Mattermost, Home Assistant, DingTalk, Feishu, WeCom, BlueBubbles (iMessage), Weixin (WeChat), API Server, Webhooks. Open WebUI connects via the API Server adapter.

Platform docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

### Sessions

```
hermes sessions list        List recent sessions
hermes sessions browse      Interactive picker
hermes sessions export OUT  Export to JSONL
hermes sessions rename ID T Rename a session
hermes sessions delete ID   Delete a session
hermes sessions prune       Clean up old sessions (--older-than N days)
hermes sessions stats       Session store statistics
```

### Cron Jobs

```
hermes cron list            List jobs (--all for disabled)
hermes cron create SCHED    Create: '30m', 'every 2h', '0 9 * * *'
hermes cron edit ID         Edit schedule, prompt, delivery
hermes cron pause/resume ID Control job state
hermes cron run ID          Trigger on next tick
hermes cron remove ID       Delete a job
hermes cron status          Scheduler status
```

### Webhooks

```
hermes webhook subscribe N  Create route at /webhooks/<name>
hermes webhook list         List subscriptions
hermes webhook remove NAME  Remove a subscription
hermes webhook test NAME    Send a test POST
```

### Profiles

```
hermes profile list         List all profiles
hermes profile create NAME  Create (--clone, --clone-all, --clone-from)
hermes profile use NAME     Set sticky default
hermes profile delete NAME  Delete a profile
hermes profile show NAME    Show details
hermes profile alias NAME   Manage wrapper scripts
hermes profile rename A B   Rename a profile
hermes profile export NAME  Export to tar.gz
hermes profile import FILE  Import from archive
```

### Credential Pools

```
hermes auth add             Interactive credential wizard
hermes auth list [PROVIDER] List pooled credentials
hermes auth remove P INDEX  Remove by provider + index
hermes auth reset PROVIDER  Clear exhaustion status
```

### Other

```
hermes insights [--days N]  Usage analytics
hermes update               Update to latest version
hermes pairing list/approve/revoke  DM authorization
hermes plugins list/install/remove  Plugin management
hermes honcho setup/status  Honcho memory integration (requires honcho plugin)
hermes memory setup/status/off  Memory provider config
hermes completion bash|zsh  Shell completions
hermes acp                  ACP server (IDE integration)
hermes claw migrate         Migrate from OpenClaw
hermes uninstall            Uninstall Hermes
```

---

## Slash Commands (In-Session)

Type these during an interactive chat session.

### Session Control
```
/new (/reset)        Fresh session
/clear               Clear screen + new session (CLI)
/retry               Resend last message
/undo                Remove last exchange
/title [name]        Name the session
/compress            Manually compress context
/stop                Kill background processes
/rollback [N]        Restore filesystem checkpoint
/background <prompt> Run prompt in background
/queue <prompt>      Queue for next turn
/resume [name]       Resume a named session
```

### Configuration
```
/config              Show config (CLI)
/model [name]        Show or change model
/personality [name]  Set personality
/reasoning [level]   Set reasoning (none|minimal|low|medium|high|xhigh|show|hide)
/verbose             Cycle: off → new → all → verbose
/voice [on|off|tts]  Voice mode
/yolo                Toggle approval bypass
/skin [name]         Change theme (CLI)
/statusbar           Toggle status bar (CLI)
```

### Tools & Skills
```
/tools               Manage tools (CLI)
/toolsets            List toolsets (CLI)
/skills              Search/install skills (CLI)
/skill <name>        Load a skill into session
/cron                Manage cron jobs (CLI)
/reload-mcp          Reload MCP servers
/plugins             List plugins (CLI)
```

### Gateway
```
/approve             Approve a pending command (gateway)
/deny                Deny a pending command (gateway)
/restart             Restart gateway (gateway)
/sethome             Set current chat as home channel (gateway)
/update              Update Hermes to latest (gateway)
/platforms (/gateway) Show platform connection status (gateway)
```

### Utility
```
/branch (/fork)      Branch the current session
/fast                Toggle priority/fast processing
/browser             Open CDP browser connection
/history             Show conversation history (CLI)
/save                Save conversation to file (CLI)
/paste               Attach clipboard image (CLI)
/image               Attach local image file (CLI)
```

### Info
```
/help                Show commands
/commands [page]     Browse all commands (gateway)
/usage               Token usage
/insights [days]     Usage analytics
/status              Session info (gateway)
/profile             Active profile info
```

### Exit
```
/quit (/exit, /q)    Exit CLI
```

---

## Key Paths & Config

```
~/.hermes/config.yaml       Main configuration
~/.hermes/.env              API keys and secrets
$HERMES_HOME/skills/        Installed skills
~/.hermes/sessions/         Session transcripts
~/.hermes/logs/             Gateway and error logs
~/.hermes/auth.json         OAuth tokens and credential pools
~/.hermes/hermes-agent/     Source code (if git-installed)
```

Profiles use `~/.hermes/profiles/<name>/` with the same layout.

### Config Sections

Edit with `hermes config edit` or `hermes config set section.key value`.

| Section | Key options |
|---------|-------------|
| `model` | `default`, `provider`, `base_url`, `api_key`, `context_length` |
| `agent` | `max_turns` (90), `tool_use_enforcement` |
| `terminal` | `backend` (local/docker/ssh/modal), `cwd`, `timeout` (180) |
| `compression` | `enabled`, `threshold` (0.50), `target_ratio` (0.20) |
| `display` | `skin`, `tool_progress`, `show_reasoning`, `show_cost` |
| `stt` | `enabled`, `provider` (local/groq/openai/mistral) |
| `tts` | `provider` (edge/elevenlabs/openai/minimax/mistral/neutts) |
| `memory` | `memory_enabled`, `user_profile_enabled`, `provider` |
| `security` | `tirith_enabled`, `website_blocklist` |
| `delegation` | `model`, `provider`, `base_url`, `api_key`, `max_iterations` (50), `reasoning_effort` |
| `checkpoints` | `enabled`, `max_snapshots` (50) |

Full config reference: https://hermes-agent.nousresearch.com/docs/user-guide/configuration

### Providers

20+ providers supported. Set via `hermes model` or `hermes setup`.

| Provider | Auth | Key env var |
|----------|------|-------------|
| OpenRouter | API key | `OPENROUTER_API_KEY` |
| Anthropic | API key | `ANTHROPIC_API_KEY` |
| Nous Portal | OAuth | `hermes auth` |
| OpenAI Codex | OAuth | `hermes auth` |
| GitHub Copilot | Token | `COPILOT_GITHUB_TOKEN` |
| Google Gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| DeepSeek | API key | `DEEPSEEK_API_KEY` |
| xAI / Grok | API key | `XAI_API_KEY` |
| Hugging Face | Token | `HF_TOKEN` |
| Z.AI / GLM | API key | `GLM_API_KEY` |
| MiniMax | API key | `MINIMAX_API_KEY` |
| MiniMax CN | API key | `MINIMAX_CN_API_KEY` |
| Kimi / Moonshot | API key | `KIMI_API_KEY` |
| Alibaba / DashScope | API key | `DASHSCOPE_API_KEY` |
| Xiaomi MiMo | API key | `XIAOMI_API_KEY` |
| Kilo Code | API key | `KILOCODE_API_KEY` |
| AI Gateway (Vercel) | API key | `AI_GATEWAY_API_KEY` |
| OpenCode Zen | API key | `OPENCODE_ZEN_API_KEY` |
| OpenCode Go | API key | `OPENCODE_GO_API_KEY` |
| Qwen OAuth | OAuth | `hermes login --provider qwen-oauth` |
| Custom endpoint | Config | `model.base_url` + `model.api_key` in config.yaml |
| GitHub Copilot ACP | External | `COPILOT_CLI_PATH` or Copilot CLI |

Full provider docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

### Toolsets

Enable/disable via `hermes tools` (interactive) or `hermes tools enable/disable NAME`.

| Toolset | What it provides |
|---------|-----------------|
| `web` | Web search and content extraction |
| `browser` | Browser automation (Browserbase, Camofox, or local Chromium) |
| `terminal` | Shell commands and process management |
| `file` | File read/write/search/patch |
| `code_execution` | Sandboxed Python execution |
| `vision` | Image analysis |
| `image_gen` | AI image generation |
| `tts` | Text-to-speech |
| `skills` | Skill browsing and management |
| `memory` | Persistent cross-session memory |
| `session_search` | Search past conversations |
| `delegation` | Subagent task delegation |
| `cronjob` | Scheduled task management |
| `clarify` | Ask user clarifying questions |
| `messaging` | Cross-platform message sending |
| `search` | Web search only (subset of `web`) |
| `todo` | In-session task planning and tracking |
| `rl` | Reinforcement learning tools (off by default) |
| `moa` | Mixture of Agents (off by default) |
| `homeassistant` | Smart home control (off by default) |

Tool changes take effect on `/reset` (new session). They do NOT apply mid-conversation to preserve prompt caching.

---

## Security & Privacy Toggles

Common "why is Hermes doing X to my output / tool calls / commands?" toggles — and the exact commands to change them. Most of these need a fresh session (`/reset` in chat, or start a new `hermes` invocation) because they're read once at startup.

### Secret redaction in tool output

Secret redaction is **off by default** — tool output (terminal stdout, `read_file`, web content, subagent summaries, etc.) passes through unmodified. If the user wants Hermes to auto-mask strings that look like API keys, tokens, and secrets before they enter the conversation context and logs:

```bash
hermes config set security.redact_secrets true       # enable globally
```

**Restart required.** `security.redact_secrets` is snapshotted at import time — toggling it mid-session (e.g. via `export HERMES_REDACT_SECRETS=true` from a tool call) will NOT take effect for the running process. Tell the user to run `hermes config set security.redact_secrets true` in a terminal, then start a new session. This is deliberate — it prevents an LLM from flipping the toggle on itself mid-task.

Disable again with:
```bash
hermes config set security.redact_secrets false
```

### PII redaction in gateway messages

Separate from secret redaction. When enabled, the gateway hashes user IDs and strips phone numbers from the session context before it reaches the model:

```bash
hermes config set privacy.redact_pii true    # enable
hermes config set privacy.redact_pii false   # disable (default)
```

### Command approval prompts

By default (`approvals.mode: manual`), Hermes prompts the user before running shell commands flagged as destructive (`rm -rf`, `git reset --hard`, etc.). The modes are:

- `manual` — always prompt (default)
- `smart` — use an auxiliary LLM to auto-approve low-risk commands, prompt on high-risk
- `off` — skip all approval prompts (equivalent to `--yolo`)

```bash
hermes config set approvals.mode smart       # recommended middle ground
hermes config set approvals.mode off         # bypass everything (not recommended)
```

Per-invocation bypass without changing config:
- `hermes --yolo …`
- `export HERMES_YOLO_MODE=1`

Note: YOLO / `approvals.mode: off` does NOT turn off secret redaction. They are independent.

### Shell hooks allowlist

Some shell-hook integrations require explicit allowlisting before they fire. Managed via `~/.hermes/shell-hooks-allowlist.json` — prompted interactively the first time a hook wants to run.

### Disabling the web/browser/image-gen tools

To keep the model away from network or media tools entirely, open `hermes tools` and toggle per-platform. Takes effect on next session (`/reset`). See the Tools & Skills section above.

---

## Voice & Transcription

### STT (Voice → Text)

Voice messages from messaging platforms are auto-transcribed.

Provider priority (auto-detected):
1. **Local faster-whisper** — free, no API key: `pip install faster-whisper`
2. **Groq Whisper** — free tier: set `GROQ_API_KEY`
3. **OpenAI Whisper** — paid: set `VOICE_TOOLS_OPENAI_KEY`
4. **Mistral Voxtral** — set `MISTRAL_API_KEY`

Config:
```yaml
stt:
  enabled: true
  provider: local        # local, groq, openai, mistral
  local:
    model: base          # tiny, base, small, medium, large-v3
```

### TTS (Text → Voice)

| Provider | Env var | Free? |
|----------|---------|-------|
| Edge TTS | None | Yes (default) |
| ElevenLabs | `ELEVENLABS_API_KEY` | Free tier |
| OpenAI | `VOICE_TOOLS_OPENAI_KEY` | Paid |
| MiniMax | `MINIMAX_API_KEY` | Paid |
| Mistral (Voxtral) | `MISTRAL_API_KEY` | Paid |
| NeuTTS (local) | None (`pip install neutts[all]` + `espeak-ng`) | Free |

Voice commands: `/voice on` (voice-to-voice), `/voice tts` (always voice), `/voice off`.

---

## Spawning Additional Hermes Instances

Run additional Hermes processes as fully independent subprocesses — separate sessions, tools, and environments.

### When to Use This vs delegate_task

| | `delegate_task` | Spawning `hermes` process |
|-|-----------------|--------------------------|
| Isolation | Separate conversation, shared process | Fully independent process |
| Duration | Minutes (bounded by parent loop) | Hours/days |
| Tool access | Subset of parent's tools | Full tool access |
| Interactive | No | Yes (PTY mode) |
| Use case | Quick parallel subtasks | Long autonomous missions |

### One-Shot Mode

```
terminal(command="hermes chat -q 'Research GRPO papers and write summary to ~/research/grpo.md'", timeout=300)

# Background for long tasks:
terminal(command="hermes chat -q 'Set up CI/CD for ~/myapp'", background=true)
```

### Interactive PTY Mode (via tmux)

Hermes uses prompt_toolkit, which requires a real terminal. Use tmux for interactive spawning:

```
# Start
terminal(command="tmux new-session -d -s agent1 -x 120 -y 40 'hermes'", timeout=10)

# Wait for startup, then send a message
terminal(command="sleep 8 && tmux send-keys -t agent1 'Build a FastAPI auth service' Enter", timeout=15)

# Read output
terminal(command="sleep 20 && tmux capture-pane -t agent1 -p", timeout=5)

# Send follow-up
terminal(command="tmux send-keys -t agent1 'Add rate limiting middleware' Enter", timeout=5)

# Exit
terminal(command="tmux send-keys -t agent1 '/exit' Enter && sleep 2 && tmux kill-session -t agent1", timeout=10)
```

### Multi-Agent Coordination

```
# Agent A: backend
terminal(command="tmux new-session -d -s backend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t backend 'Build REST API for user management' Enter", timeout=15)

# Agent B: frontend
terminal(command="tmux new-session -d -s frontend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t frontend 'Build React dashboard for user management' Enter", timeout=15)

# Check progress, relay context between them
terminal(command="tmux capture-pane -t backend -p | tail -30", timeout=5)
terminal(command="tmux send-keys -t frontend 'Here is the API schema from the backend agent: ...' Enter", timeout=5)
```

### Session Resume

```
# Resume most recent session
terminal(command="tmux new-session -d -s resumed 'hermes --continue'", timeout=10)

# Resume specific session
terminal(command="tmux new-session -d -s resumed 'hermes --resume 20260225_143052_a1b2c3'", timeout=10)
```

### Tips

- **Prefer `delegate_task` for quick subtasks** — less overhead than spawning a full process
- **Use `-w` (worktree mode)** when spawning agents that edit code — prevents git conflicts
- **Set timeouts** for one-shot mode — complex tasks can take 5-10 minutes
- **Use `hermes chat -q` for fire-and-forget** — no PTY needed
- **Use tmux for interactive sessions** — raw PTY mode has `\r` vs `\n` issues with prompt_toolkit
- **For scheduled tasks**, use the `cronjob` tool instead of spawning — handles delivery and retry

---

## Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml
2. Verify provider: `pip install faster-whisper` or set API key
3. In gateway: `/restart`. In CLI: exit and relaunch.

### Tool not available
1. `hermes tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### Model/provider issues
1. `hermes doctor` — check config and dependencies
2. `hermes login` — re-authenticate OAuth providers
3. Check `.env` has the right API key
4. **Copilot 403**: `gh auth login` tokens do NOT work for Copilot API. You must use the Copilot-specific OAuth device code flow via `hermes model` → GitHub Copilot.

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** In gateway: `/restart`. In CLI: exit and relaunch.
- **Code changes:** Restart the CLI or gateway process

### When patch fails to match
If `patch(action='replace')` can't find `old_string` and repeated attempts still fail, switch to the write-validate-swap pattern: write the complete corrected file to a temp path, validate it (compile/lint/test), then swap it into place. See `references/editing-patterns.md`.

### Skills not showing
1. `hermes skills list` — verify installed
2. `hermes skills config` — check platform enablement
3. Load explicitly: `/skill name` or `hermes -s name`

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

Common gateway problems:
- **Gateway dies on SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **Gateway dies on WSL2 close**: WSL2 requires `systemd=true` in `/etc/wsl.conf` for systemd services to work. Without it, gateway falls back to `nohup` (dies when session closes).
- **Ghost Connection (Connected but no targets):** If `gateway status` or logs show a platform as `connected` but `send_message(action='list')` is empty and messages fail to resolve, check `~/.hermes/logs/gateway.log` for `Channel directory built: 0 target(s)`. This indicates the adapter is connected to the server but failed to discover/index valid users. Try restarting the gateway or verifying `ALLOWED_USERS` in `.env`.\n\n### Node.js Requirements for WhatsApp\n\nWhatsApp pairing requires Node.js v20+. If you encounter version errors during `hermes whatsapp`:\n\n**On Fedora/RPM-based systems:**\n```bash\n# Remove conflicting npm first\nsudo dnf remove -y npm\n# Install Node.js 20 via NodeSource\ncurl -fsSL https://rpm.nodesource.com/setup_20.x | sudo -E bash -\nsudo dnf install -y --best --allowerasing nodejs\n```\n\n**On Debian/Ubuntu:**\n```bash\ncurl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -\nsudo apt-get install -y nodejs\n```

### Platform-specific issues
- **Discord bot silent**: Must enable **Message Content Intent** in Bot → Privileged Gateway Intents.
- **Slack bot only works in DMs**: Must subscribe to `message.channels` event. Without it, the bot ignores public channels.
- **Windows HTTP 400 "No models provided"**: Config file encoding issue (BOM). Ensure `config.yaml` is saved as UTF-8 without BOM.

### Auxiliary models not working
If `auxiliary` tasks (vision, compression, session_search) fail silently, the `auto` provider can't find a backend. Either set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`, or explicitly configure each auxiliary task's provider:
```bash
hermes config set auxiliary.vision.provider <your_provider>
hermes config set auxiliary.vision.model <model_name>
```

---

## Where to Find Things\n\n| Looking for... | Location |\n|----------------|----------|\n| Config options | `hermes config edit` or [Configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) |\n| Available tools | `hermes tools list` or [Tools reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference) |\n| Slash commands | `/help` in session or [Slash commands reference](https://hermes-agent.nousresearch.com/docs/reference/slash-commands) |\n| Skills catalog | `hermes skills browse` or [Skills catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) |\n| Provider setup | `hermes model` or [Providers guide](https://hermes-agent.nousresearch.com/docs/integrations/providers) |\n| Platform setup | `hermes gateway setup` or [Messaging docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/) |\n| MCP servers | `hermes mcp list` or [MCP guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) |\n| Profiles | `hermes profile list` or [Profiles docs](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) |\n| Cron jobs | `hermes cron list` or [Cron docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) |\n| Memory | `hermes memory status` or [Memory docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) |\n| Env variables | `hermes config env-path` or [Env vars reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) |\n| CLI commands | `hermes --help` or [CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) |\n| Gateway logs | `~/.hermes/logs/gateway.log` |\n| Session files | `~/.hermes/sessions/` or `hermes sessions browse` |\n| Source code | `~/.hermes/hermes-agent/` |\n| Troubleshooting | `~/.hermes/skills/hermes-agent/references/troubleshooting.md` |\n\n---\n\n## Cron Job Ops (absorbed from `cron-job-ops`)

Diagnose, fix, and verify Hermes scheduled cron jobs in non-OK status. Triggered when `cronjob(action='list')` shows `last_status: "error"`, a non-OK `last_delivery_error`, or a silently-failing job.

### Investigation workflow
1. **List & read** — `cronjob(action='list')` to find the failing job by `job_id`; never guess IDs.
2. **Locate the script** — `no_agent: true` jobs run the bare `script` filename from `/root/.hermes/scripts/`; read it with `read_file`. Agent jobs are driven by `prompt`/Skills.
3. **Reproduce** — run it from a terminal to see the real error (`bash /root/.hermes/scripts/<script>`); background + `process(action='poll')` for long runs (foreground ~60s cap).
4. **Classify** — path/command, import (`ModuleNotFoundError`), timeout (120s, see below), schema drift (`no such column`), or delivery error (separate from logic).
5. **Fix → re-run to verify clean exit (`EXIT: 0`) → commit & push** only the files touched.

### Pitfalls
- **120s hard timeout on `no_agent` jobs** — the runner kills at 120s; cannot be raised via the `cronjob` tool. Fix by lowering per-run work (`--limit`), adding an in-script wall-clock budget (`JOB_BUDGET`, default 90), or a stateful sweep across nights. Do NOT background-and-exit (hides failures).
- **`script` must be a bare filename** in `/root/.hermes/scripts/` — a command+path or absolute path fails to resolve.
- **PYTHONPATH / sys.path[0] quirk** — running `python3 /abs/repo/python/foo.py` sets `sys.path[0]` to the script dir, not repo root; `from python.db_connector import ...` needs `export PYTHONPATH="/repo/root:/repo/root/src"` in the wrapper.
- **SQLite schema drift in `_ensure_schema`** — `CREATE TABLE IF NOT EXISTS` is a no-op on an old schema; new columns fail with `no such column`. Use `ALTER TABLE ... ADD COLUMN` (verify with `PRAGMA table_info`), never drop/recreate.
- **`execute_code` blocked in autonomous cron runs** — fall back to `write_file` a `.py` to `/tmp` and run via `terminal` (`/usr/bin/python3.10`). Confirmed durable pattern (KSFP 2026-09-27 run, FHS 2026-09-22 run, KSFII 2026-09-25 run).
- **Always deliver a brief status** in cron output, even when no leads found. Never suppress the final response. Confirm delivery by stating the target channel and pipeline status (`COMPLETE — LEADS FOUND` / `COMPLETE — NO NEW LEADS`) in the final response body. If `execute_code` fails, fall back to `/tmp/` `.py` + `terminal()` rather than blocking.
- **`setsid`/`nohup`/`&` blocked in foreground** — split into a foreground guard (branch decision, `touch` lock, echo `LAUNCHED`/`SKIP_CONCURRENT`) + a tracked `terminal(background=true, notify_on_complete=true)` half; never start a second run while the lock is held.
- **Tracked PID is the shell, not the worker** — the real worker is a child python process; diagnose via `pgrep -P <pid>` and `tail` the script's own log file, not the Hermes capture.

### References
- `references/cron-error-cookbook.md` — four reproduction recipes (dto import + SQLite ALTER, indicator `--limit`, analyst-ratings path + time budget, backup script-path fix).
- `references/background-launch-and-diagnosis.md` — fire-and-forget cron guards when `setsid/&` is blocked, and diagnosing a suspected "hung" background run.

## Hermes operational patterns for cron, jobs, and multi-tenant deployment (absorbed from `hermes-ops` and `hermes-multi-tenant-deployment`)

### Cron script resolution (summary)

The `script` field in `cron/jobs.json` must be a bare **filename** resolved from `~/.hermes/scripts/`; for project scripts, **copy them there** (not symlink — the validator rejects symlinks that point outside the scripts dir with "Script path escapes the scripts directory via traversal"). The full diagnostic runbook — the 120s no_agent hard timeout, PYTHONPATH/sys.path quirks, SQLite schema-drift migration, verify+commit workflow, and background-launch/`setsid` diagnosis — now lives in **Cron Job Ops** (section above). See `references/cron-error-cookbook.md` and `references/background-launch-and-diagnosis.md`.

---

## Multi-tenant Hermes deployment

Run multiple independent Hermes instances on one Linux server — one per business entity — with full isolation via system users, shared venv, and systemd user services.

### Layer isolation

| Layer | Shared | Per-User (Isolated) |
|-------|--------|---------------------|
| Hermes source/venv | `/usr/local/lib/hermes-agent/` (root-owned) | — |
| Python interpreter | System Python 3.11 via uv | `~/venv/` (symlinks to shared Python) |
| Config & state | — | `~/.hermes/` |
| Gateway service | — | systemd **user** service `hermes-gateway.service` |
| Linger | — | `loginctl enable-linger <user>` |

### Setup procedure

1. Create system users for each entity; run `loginctl enable-linger` on each.
2. Run `./setup-hermes.sh` per user — creates venv, symlinks binary, seeds skills.
3. Run `hermes setup` per user for config, or set config keys via `hermes config set`.
4. Install gateway as user service per user; verify with `hermes gateway status`.
5. Deploy cron jobs per user via `cronjob action=create ... --workdir ...`.

### Migration from root

Copy `/root/.hermes` to the new user's home, `chown -R`, sed `HERMES_HOME` paths in `config.yaml`, install per-user, install gateway, disable root gateway if present.

### Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Gateway dies on SSH logout | Linger not enabled | `loginctl enable-linger <user>` |
| `hermes: command not found` | PATH missing `~/.local/bin` | Add to `~/.bashrc` |
| Skills not loading | Skills not synced | `hermes skills config` or `cp -r` from shared source |
| Cron jobs not firing | Scheduler not running | Cron runs inside gateway; check gateway status |
| Permission denied on `~/.hermes` | Wrong ownership | `chown -R <user>:<user>` |

## Contributor Quick Reference

For occasional contributors and PR authors. Full developer docs: https://hermes-agent.nousresearch.com/docs/developer-guide/

### Project Layout

```
hermes-agent/
├── run_agent.py          # AIAgent — core conversation loop
├── model_tools.py        # Tool discovery and dispatch
├── toolsets.py           # Toolset definitions
├── cli.py                # Interactive CLI (HermesCLI)
├── hermes_state.py       # SQLite session store
├── agent/                # Prompt builder, context compression, memory, model routing, credential pooling, skill dispatch
├── hermes_cli/           # CLI subcommands, config, setup, commands
│   ├── commands.py       # Slash command registry (CommandDef)
│   ├── config.py         # DEFAULT_CONFIG, env var definitions
│   └── main.py           # CLI entry point and argparse
├── tools/                # One file per tool
│   └── registry.py       # Central tool registry
├── gateway/              # Messaging gateway
│   └── platforms/        # Platform adapters (telegram, discord, etc.)
├── cron/                 # Job scheduler
├── tests/                # ~3000 pytest tests
└── website/              # Docusaurus docs site
```

Config: `~/.hermes/config.yaml` (settings), `~/.hermes/.env` (API keys).

### Adding a Tool (3 files)

**1. Create `tools/your_tool.py`:**
```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("EXAMPLE_API_KEY"))

def example_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="example_tool",
    toolset="example",
    schema={"name": "example_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: example_tool(
        param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

**2. Add to `toolsets.py`** → `_HERMES_CORE_TOOLS` list.

Auto-discovery: any `tools/*.py` file with a top-level `registry.register()` call is imported automatically — no manual list needed.

All handlers must return JSON strings. Use `get_hermes_home()` for paths, never hardcode `~/.hermes`.

### Adding a Slash Command

1. Add `CommandDef` to `COMMAND_REGISTRY` in `hermes_cli/commands.py`
2. Add handler in `cli.py` → `process_command()`
3. (Optional) Add gateway handler in `gateway/run.py`

All consumers (help text, autocomplete, Telegram menu, Slack mapping) derive from the central registry automatically.

### Agent Loop (High Level)

```
run_conversation():
  1. Build system prompt
  2. Loop while iterations < max:
     a. Call LLM (OpenAI-format messages + tool schemas)
     b. If tool_calls → dispatch each via handle_function_call() → append results → continue
     c. If text response → return
  3. Context compression triggers automatically near token limit
```

### Testing

```bash
python -m pytest tests/ -o 'addopts=' -q   # Full suite
python -m pytest tests/tools/ -q            # Specific area
```

- Tests auto-redirect `HERMES_HOME` to temp dirs — never touch real `~/.hermes/`
- Run full suite before pushing any change
- Use `-o 'addopts='` to clear any baked-in pytest flags

### Commit Conventions

```
type: concise subject line

Optional body.
```

Types: `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`

### Key Rules

- **Never break prompt caching** — don't change context, tools, or system prompt mid-conversation
- **Message role alternation** — never two assistant or two user messages in a row
- Use `get_hermes_home()` from `hermes_constants` for all paths (profile-safe)
- Config values go in `config.yaml`, secrets go in `.env`
- New tools need a `check_fn` so they only appear when requirements are met

## KSFII financial advisory agent suite

Absorbed from `ksfii-agents`. Covers domain agents for business insurance, estate planning, life insurance, retirement planning, daily process automation, and marketing (Fraser Highland Shoppe).

See `references/ksfii-agents-overview.md` (if present) for agent specializations.
See `references/customer-service-agent.md`, `references/kyc-onboarding.md`, `references/suitecrm-integration.md` for integration notes.


## Simplify-code (parallel 3-agent review pattern)

Absorbed from `simplify-code`. Three focused subagents running concurrently beat one broad reviewer on code-cleanup tasks.

**Core principle:** Three narrow reviewers beat one broad reviewer. Each one deeply searches the codebase for a single class of problem without diluting attention across all three. They run concurrently, so you pay the latency of one review, not three.

**Invoke only when the user explicitly asks** for "simplify," "clean up," "review my changes," or similar — not automatically after every edit. It costs three subagents' worth of tokens.

**The three reviewers (drop any the user's focus excludes):**

1. **Code Reuse** — duplicate functionality already in the codebase. Search utility modules, shared helpers, adjacent files for existing functions the new code could call instead of reimplementing. Flag: new functions duplicating existing ones; hand-rolled logic a utility already does. Name the existing thing and where it lives.

2. **Code Quality** — redundant state, parameter sprawl, copy-paste-with-variation, leaky abstractions, stringly-typed code. Give the concrete refactor.

3. **Efficiency** — unnecessary work, missed concurrency, hot-path bloat, TOCTOU anti-patterns, memory issues, overly broad reads. Give the concrete fix and why it runs faster/lighter.

**Rules:**
- Give **every reviewer the complete diff** — cross-file issues hide in gaps.
- Require `file:line` evidence for each finding. Drop findings that lack it.
- Default resolution order for conflicts: **correctness > stated focus > readability/reuse > micro-perf**. Don't apply a perf "fix" that hurts clarity unless the path is genuinely hot.
- Keep edits scoped to what the diff touched plus the minimal surrounding change a fix requires. This is cleanup, not a license to refactor the whole module.
- More than ~3 reviewers means more cost and conflicting suggestions, not better coverage. Three categories cover the space.

## Subagent output discipline

Absorbed from `delegation`. Subagent runs can include outdated or stale-looking surface output. Trust only Postgres/Disk invariant checks you rerun yourself in a second step, not tool-result summaries alone.

When a background job reports success but later database state shows no new rows, treat that as incomplete until independently verified. Re-run the exact failing script and capture exit code + new state snapshot.

## Hermes skill authoring (hermes-agent-skill-authoring)

Write, validate, and audit SKILL.md files for in-repo Hermes skills.

**Frontmatter rules**
- `name`: lowercase, hyphens, 64 chars max
- `description`: one paragraph, no markdown lists
- `version`, `author`, `license`: always present

## Hermes gateway troubleshooting (hermes-gateway-troubleshooting)

Diagnose connectivity and target discovery issues for Hermes messaging gateways (WhatsApp, Email, Discord, etc.).

## Hermes TUI slash commands (debugging-hermes-tui-commands)

Debug Hermes TUI slash commands: Python, gateway, Ink UI.

## Claude Code delegation — `claude-code`

Delegate coding tasks to any leading CLI coding agent: Claude Code, Codex, OpenCode, etc. Wrap the CLI so it matches Hermes tool interfaces (file tools, terminal).

## Long-running commands — `long-running-commands`

Execute long-running single-shot commands in cron or non-interactive shells. Use `terminal(background=True, notify_on_complete=True)` instead of foreground; prefer `watch_patterns` only for truly rare mid-process signals, not end-of-run markers.

Reference: `references/atr_sweep_2026-07-29.md` — session-specific ATR sweep reproduction recipe.

## KSFII Financial Lead-Response Pipeline

Absorbed from `ksfii-lead-response`. Automated lead-discovery and response pipeline for KSFII Financial (insurance/financial advisory). Scans Reddit, Canadian forums, Facebook Groups, LinkedIn, and Quora, then scores, deduplicates, and delivers leads via email and Discord. Runs as a scheduled cron job.

### Pipeline Stages

SCAN → DEDUP → SCORE → CRM → CONTENT → APPROVAL → POST → KB

### Scanner Timeout Fallback (critical)

Both `reddit_scanner.py` (60s timeout) and `workflow.py` (120s timeout) reliably time out under cron (exit code 124). The `web_search` fallback is now the effective primary path for cron executions.

**Detection heuristic**: if `cronjob action=list` shows a job with `no_agent: true`, `script: reddit_scan_*.sh`, and the last 3+ runs all show `"source unavailable (HTTP 429)"` or `"no leads fetched"`, the job is stuck on a dead API endpoint. Convert to an agent job immediately.

**Fix — convert to agent job**: Change from `no_agent: true` + `script:` to an agent job with `skills: ["ksfii-lead-response"]` and a business-specific prompt using `web_search` across multiple sources.

**Converted examples** (2026-09-16): FHS (Fraser Highland Shoppe), KSFP (K.S. Fraser Piping), ASPD (Airdrie Pipe Band) — all converted from `no_agent` shell → agent with multi-source web_search.

### Scoring Models

**Model A (1-6 decision tree):** For clean, fresh leads from direct scanner output. Minimum threshold: 3.

**Model B (1-10 factored):** For web_search fallback mode and older-but-valuable leads. Scores 7 dimensions independently: Freshness, Intent Clarity, Budget/Pain Signal, Location Specificity, Multi-Product/Lifetime Value, Sophistication Signal, Active Shopping/Switching. Minimum threshold: 5.

**Model selection:** If unsure, use Model B. It handles both fresh and older leads well.

### Business Variant Note

This pipeline was designed for KSFII Financial but the stages are business-agnostic. Confirmed working 2026-09-19 for Fraser Highland Shoppe (Scottish gift/kilt business) producing 2 qualified event/reference leads.

### Reference Files

- `references/scoring-criteria.md`, `references/scoring-factored.md`, `references/intent-signals.md` — scoring rubrics
- `references/cron-job-conversion.md` — FHS/KSFP/ASPD conversion case study
- `references/2026-09-17-ksfii-financial-cron-run.md`, `references/2026-09-18-ksfii-financial-cron-run.md`, `references/2026-09-19-fhs-lead-run.md`, `references/2026-09-19-ksfp-cron-run.md` — execution references
- `references/fhs-event-pipeline.md` — event pipeline patterns for Scottish/gift businesses
- `references/care-first-alberta.md` — Care-First auto insurance market context (Alberta, Jan 2027)
- `references/delivery-troubleshooting.md`, `references/market-signals.md` — delivery and market context

### Cron Job Re-enablement After Migration

After infrastructure tasks that pause cron jobs (e.g. schema migrations), always do a re-enable sweep: list all jobs, filter to paused, resume in priority order (daily monitors first, then night batch jobs, then event-driven), skip intentionally-paused and not-yet-due jobs, verify `next_run_at` moved forward.

### Self-Removing Completion Monitors

For long-running batch jobs that need a safety net: build a self-removing cron monitor that checks process liveness, restarts if dead, and removes its own cron entry when the job is done. **Critical pitfall for Hermes-managed jobs**: self-removal via `crontab -l | grep -v | crontab -` is DEAD CODE — Hermes jobs live in `~/.hermes/cron/jobs.json`, not the system crontab. Use Hermes API removal, `cronjob action=update`, or parent-session cleanup instead.

(See `references/cron-job-conversion.md` and `references/cron-file-editing-resilience.md` for full details.)

---

## State Backup & Restore (absorbed from `hermes-config-backup`)

Persist the agent "brain" (memory + skills + safe config) to a **PRIVATE** GitHub repo so a disk loss/corruption doesn't wipe accumulated context. Load when the user asks to back up memory/skills to GitHub, or after making valuable skill/memory changes that should survive off-box.

- **Never `git add -A` in `~/.hermes`** — it also holds secrets (`.env`, `auth.json`, `config.yaml`) and `state.db` (~3GB). Stage only explicit safe paths: `.gitignore memories/ skills/ SOUL.md scripts/`.
- `.gitignore` template (copy to `~/.hermes/.gitignore`): `templates/.gitignore` — excludes secrets/state/caches/sessions, keeps only memory/skills/SOUL/scripts, and also excludes `skills/.archive/`, `skills/.curator_backups/`, `__pycache__`, `*.pyc`, `skills/.hub/`.
- Repeatable commit+push script: `templates/backup_memory_skills.sh` (copy to `~/.hermes/backup_memory_skills.sh`, `chmod +x`). Schedule via Hermes cron for daily auto-backup.
- **Sanity gate before pushing:** `git diff --cached --name-only | grep -E '\.env|auth\.json|config\.yaml|state\.db'` must return NOTHING.
- Create the private repo with `gh repo create <you>/hermes-backup --private --source . --remote origin --push` (authenticated with `repo` scope). Confirm the name is free first (`gh repo view <name>`).
- The safety gate may block a compound `git rm --cached` + `git push` as destructive — run that step only after the user approves it.
