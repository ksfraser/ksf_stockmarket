# Guard allowlist + rules (investment-agent)

Guard: `scripts/guard_standardized_access.py`. Modes:
  (default)            audit all .py     -> warnings only, exit 0
  --staged             pre-commit        -> block on violations in staged files
  --changed            CI (origin/main...HEAD, fallback HEAD~1..HEAD) -> block on diff
  --full               ⚠️ NOT A VALID FLAG (argparse exits 2 with no output;
                        looks like "0 violations" but is a crash)

BLOCK rules (outside allowlist):
  - raw sqlite3        : regex `sqlite3\.connect\(`
  - direct yfinance    : `import yfinance|yf\.Ticker|\.download\(|\.history\(`
  - hardcoded password : `password\s*=\s*['\"][^'\"]+['\"]`
  - direct http client : `requests\.(get|post)|httpx|urllib\.request`
  - direct llm         : `import openai|OpenAI\(|chat\.completions`

WARN rules (non-blocking):
  - direct discord send: `discord_webhook|DiscordWebhook\(|requests\.post\(\s*webhook`
    (a leftover `from discord_webhook import DiscordWebhook` comment also trips this)

Allowlist (legit data layer / sync tools) — regex on repo-relative path:
  ALLOW_SQLITE:
    src/db/
    src/delivery/webhook_dispatcher\.py
    scripts/sync-sqlite-alerts-to-mariadb\.py
    scripts/migrate_price_intraday_normalize\.py
    backfill_job\.py
  ALLOW_YF:
    src/db/            # price_fetcher AND data_cache legitimately use yfinance
    python/src/symbol_resolver\.py
  ALLOW_HTTP:          # the shared HTTP/LLM clients are allowed to use requests/urllib
    src/common/http_client\.py
    src/common/llm_client\.py
    src/delivery/webhook_dispatcher\.py
  ALLOW_LLM:
    src/common/llm_client\.py

PITFALL — self-exclusion:
  The guard scans every .py including itself. Its docstring documents the forbidden
  patterns, so the regex matches the guard's own file and it blocks its own commit.
  Fix: in the scan loop,
      if os.path.basename(full) == "guard_standardized_access.py": continue
  (Do NOT try to word-around the docstring; the exclusion is simpler and robust.)

PITFALL — regex paren balance in BLOCK rules:
  To match yfinance's `.history(` call, write `\.history\(` (one escaped open-paren).
  Writing `\.history\((` adds a RAW `(` that opens an unterminated group and crashes
  the guard at import: `re.error: missing ), unterminated subpattern`. Every BLOCK
  regex must have balanced parens.

Extending: when you add a legit data-layer module, add it to the right ALLOW_* list.
HTTP and LLM already have shared clients in `src/common/` (HttpClient, LLMClient) —
route through them; their former WARN rules are now BLOCK with the clients allowlisted.
