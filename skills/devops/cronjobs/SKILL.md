---
name: cronjobs
description: Debug and fix cron jobs whose shell wrappers fail because the script path doesn't resolve relative to the workdir, or whose Python entry point gets empty DB creds because the wrapper didn't source .env. Covers no_agent=true mode, script-path resolution, env sourcing, verifying a cron job actually runs before trusting its status, self-removing completion monitors, and the python/src/ import-path pitfall.
---

# Cron Job Debugging

When a Hermes-scheduled cron job reports `error` status, the first thing to check is whether the scheduler can actually find and execute the wrapper script. Two distinct failure modes account for most cron-job errors:

1. **Script path doesn't resolve** — the `script` field references a basename relative to `workdir`, but the file only lives in a subdirectory.
2. **Python entry point gets empty DB creds** — the wrapper didn't source `.env`, and the Python script reads `DB_HOST`/`DB_USER`/`DB_PASS`/`DB_NAME` env vars directly (not via a shared `db_connector` module).

## Root cause: script path resolution

The cron scheduler resolves `script` relative to `workdir`. If `workdir=/home/ksf_stockmarket/ksf_stockmarket` and `script=run_ingest_screener.sh`, the scheduler looks for `/home/ksf_stockmarket/ksf_stockmarket/run_ingest_screener.sh`. If the file only exists at `scripts/run_ingest_screener.sh`, the job fails.

**Symptom:** job status = `error`, manual run of the same script from the workdir succeeds (because you're running it from the right path or via the subdirectory path).

**Fix:** put a copy of the wrapper at the repo root (the workdir level) in addition to any organized subdirectory location. Both copies should be identical and source `.env` before `exec`.

## Root cause: missing .env sourcing for env-reading scripts

Some Python scripts read DB credentials directly from environment variables:

```python
# zacks_scraper.py style — reads env vars directly
host = os.environ.get("DB_HOST", "ksfraser.ca")
user = os.environ.get("DB_USER", "ksfraser_stockmarket")
password = os.environ.get("DB_PASS", "")
database = os.environ.get("DB_NAME", "ksfraser_stock_market")
```

When the cron wrapper does NOT source `.env` before `exec`, these variables are empty in the cron environment. The script then connects with empty credentials and fails — often with a misleading error or silently.

**Contrast with db_connector style:** scripts that go through a shared `db_connector` module may have fallback paths (config.yaml, hardcoded defaults, SQLite fallback) that partially mask the missing env vars. Scripts that read env vars directly have no fallback — empty creds = failed connection.

**Fix:** the wrapper MUST source `.env` before exec:

```bash
#!/usr/bin/env bash
set -uo pipefail
REPO_DIR="/path/to/repo"
cd "$REPO_DIR"
if [[ -f ".env" ]]; then
    set -a && . ./.env && set +a
fi
exec python3 -u python/entry_point.py 2>&1
```

### no_agent=true mode

When a cron job is created with `no_agent=true`, the Hermes scheduler runs the script directly — there is no LLM agent layer. The script must be fully self-contained:

- Correct working directory (the `workdir` setting handles this, but the script should `cd` to be safe)
- `.env` sourced (cron environments don't inherit shell env)
- `python3` resolvable (use `exec python3` or full path; `which python3` in the wrapper confirms)
- Entry point found at the expected relative path
- Output goes to stdout (the scheduler captures it); logging to a file is fine as a secondary channel but don't rely on it as the only output

### Single-source API rate limiting in no_agent cron jobs

**Symptom**: A `no_agent: true` cron job with a shell script (`script:` field) hits a single API endpoint (e.g. PullPush.io Reddit) and receives HTTP 429 / rate-limited / empty responses for weeks. The job produces zero results forever.

**Root cause**: `no_agent: true` jobs run the shell script directly with no LLM reasoning, no tool access (no `web_search`), and no fallback logic. If the single API endpoint is rate-limited or down, the job silently produces nothing. The business-domain skill (e.g. `ksfii-lead-response`) has multi-source web_search fallback, but `no_agent` shell-script jobs cannot use it.

**Fix — convert to an agent job**:

1. Change the cron job from `no_agent: true` + `script:` to an **agent job** with `skills: ["<business-skill>"]` and a business-specific prompt
2. Remove the `script:` field and set `no_agent: false` (or omit it)
3. Write a business-specific prompt that uses `web_search` across multiple sources (Reddit + forums + Facebook + LinkedIn + Quora), with explicit query templates per source type
4. Keep the same schedule and deliver target
5. Delete the obsolete shell script (e.g. `reddit_scan_fhs.sh`, `reddit_scan_common.sh`)

**Why this works**: Agent jobs load the business skill which has `web_search` as a tool. The skill's SCAN stage already documents multi-source query templates. The agent adapts queries to any business type.

**Converted examples** (2026-09-16):
- **FHS** (Fraser Highland Shoppe): `no_agent` shell → agent with `ksfii-lead-response` skill, 18 web_search queries across 4 source types (Reddit, General Web, Forums, Facebook). Re-enabled.
- **KSFP** (K.S. Fraser Piping): same conversion, 16 queries. 2026-09-17 run produced 4 new leads (Facebook group beginner seeker score 5, CDPB recruitment signal score 4, Alberta events calendar score 4, older event-hire signal score 3) — multi-source web_search confirmed working.
- **ASPD** (Airdrie Pipe Band): same conversion, 18 queries. Re-enabled.

**Detection heuristic**: if `cronjob action=list` shows a job with `no_agent: true`, `script: reddit_scan_*.sh`, and the last 3+ runs all show `"source unavailable (HTTP 429)"` or `"no leads fetched"`, the job is stuck on a dead API endpoint. Convert immediately — do not wait for "more data" to confirm.

**Reference**: `references/cron-job-conversion.md` in this skill directory for the full FHS/KSFP/ASPD conversion case study with query templates and 2026-09-17 run results.

### Re-enabling paused cron jobs after infrastructure work

**Symptom**: After a migration, schema change, or infrastructure task, all cron jobs were paused (`enabled: false`, `state: "paused"`) but never resumed. The user sees no alerts/results and asks "are our cron tasks running?"

**Root cause**: During migration work (e.g. the `indicators_json → indicators` columnar migration), cron jobs are paused to prevent them from writing to a changing schema. After the migration completes, the pause sweep is one step in the workflow — but re-enabling is a separate step that is easy to forget, especially when the session gets interrupted or context-compressed.

**Fix**: After any infrastructure task that pauses cron jobs, the final step is ALWAYS a re-enable sweep:

1. List all jobs: `cronjob action=list`
2. Filter to paused: check `enabled: false` / `state: "paused"` on each
3. Resume in priority order — start with jobs the user expects results from (daily monitors, alert detectors, price syncs, volume snapshots, screener ingesters, analyst ratings, indicator calculators)
4. Skip jobs that are intentionally paused (monthly/quarterly/annual that aren't due yet, compliance reviews far in the future)
5. Verify: `cronjob action=list` again — confirm `enabled: true` on resumed jobs, check `next_run_at` moved forward

**What to resume vs skip**:
- **Resume immediately**: Daily monitors, intraday alert detectors, price syncs, volume snapshots, screener ingesters, analyst ratings, indicator calculators, backtest queues, daily research briefs, Zacks refreshes, Lipper scores, symbol reconciliations, nightly pipelines
- **Skip (not due)**: Monthly/quarterly/annual jobs whose `next_run_at` is weeks/months away (e.g. `Seg-fund monthly pipeline` due 2026-10-15, `Seg-fund annual rollover` due 2027-02-01, `RBC monthly seg-fund refresh` due 2026-10-15, `KSFII annual compliance review` due 2027-01-10) — these will self-resume when their schedule triggers
- **Skip (intentionally off)**: Jobs the user has explicitly asked to keep paused

**Batch pattern**: Resume 5-8 jobs per turn to stay under output limits. Group by category (daily monitors first, then night-time batch jobs, then event-driven). Verify each `cronjob action=resume` succeeds before moving to the next batch.

**Verification**: After resuming, check `next_run_at` on each resumed job — it should be a future timestamp (not null, not in the past). If `next_run_at` is still null, the job's schedule may need inspection.

**Reference**: `references/cron-job-conversion.md` in this skill directory for the full resume + conversion workflow from 2026-09-16.

## Debugging workflow

1. **Read the job definition** — `cronjob action=list`, find the job, note `script`, `workdir`, `no_agent`.
2. **Check both locations** — does the script exist at `$workdir/$script` AND at any subdirectory variant?
3. **Run the wrapper manually from the workdir** — `cd $workdir && bash $script` (or the subdirectory path). If it works manually but the cron job fails, the path resolution is the issue.
4. **Verify .env sourcing** — add a temporary `echo "DB_HOST=$DB_HOST"` after the sourcing block in the wrapper and run it. If DB_HOST is empty, the sourcing isn't working.
5. **Verify python3 resolves** — `which python3` inside the wrapper context.
6. **Check the log file** — if the wrapper appends to `/tmp/*.log`, read it. But don't trust the log as the only signal; a missing script produces no log at all.
7. **Reproduce the cron environment** — the key insight: the cron scheduler's view of the filesystem (workdir + relative script path) is what matters, not whether the script works when you run it from somewhere else.

## Verification before trusting status

Before declaring a cron job fixed, verify end-to-end from the scheduler's perspective:

```bash
cd "$WORKDIR"
bash "$SCRIPT"   # exactly what the scheduler does
```

If that succeeds, the next scheduled tick should pass. If it fails or hangs, the fix isn't complete.

## Related: precomputed data tables

When a filter engine or screener depends on computed columns that don't exist in the base tables, the recommended pattern is a nightly refresh script that upserts into a dedicated table — not runtime CTEs or triggers. Verify such a script works against the live DB before relying on it:

```bash
cd "$APP_ROOT"
set -a && source .env && set +a
php scripts/refresh_perf_windows.php
```

A successful run prints counts (rows updated/skipped) and exits 0. A hang or timeout means the computation is too expensive for the schedule window — increase the timeout or reduce the scope.

## Cherry-picking narrow fixes onto main

When a fix lives on a feature branch but main needs just that fix (not the whole branch), cherry-pick the specific commit onto main:

```bash
git checkout main
git cherry-pick <commit-sha>
```

**Typical conflict:** the feature branch deleted or modified a file that main still has (or vice versa). Git reports `CONFLICT (modify/delete)`. Resolve by picking the version that makes sense for main — usually the incoming (theirs) version if the fix is an addition, or keeping main's version if the file shouldn't change on main.

After resolving, `git add <resolved-files>` then `git cherry-pick --continue`.

**Push:** `git push origin main`. If remote is ahead (another push happened), pull/rebase first: `git pull --rebase origin main && git push origin main`.

## "Ready to merge to main" checkpoints

Before declaring a branch merge-ready, verify all four:

1. **Commits pushed** — `git log main..HEAD --not --remotes=origin` returns empty. Every commit on the branch is on the remote.
2. **Working tree clean** — `git status --short` shows no `M` (modified) files. Only `??` untracked files are acceptable.
3. **Tested in the live environment** — not just from a dev sandbox. For cron jobs: the wrapper resolves from the scheduler's `workdir` perspective, `.env` sources, `python3` resolves, and the entry point connects to the actual DB. For PHP: the dev tree IS the live path (`/var/www/stockmarket-app/`), so committed PHP runs immediately for web requests — but cron jobs are a separate axis (they read scripts from disk, resolved by `workdir` + `script` path).
4. **End-to-end smoke test** — run the actual entry point the way the scheduler/cron would: `cd $WORKDIR && bash $SCRIPT`. If it succeeds, the fix is real. If it fails or hangs, it's not complete.

**Merge-readiness is per-fix, not per-branch.** A branch can carry a safe-to-merge narrow fix (e.g. a cron wrapper path correction) alongside large uncommitted feature work that is NOT ready. Cherry-pick the narrow fix onto main; leave the rest on the feature branch.

## Self-removing completion monitors

When a long-running batch job (DB migration, data copy, purge) needs a safety net
that restarts it if it dies and removes itself when the job is done, build a
**self-removing cron monitor** rather than a permanent watchdog:

- The monitor script checks whether the job process is alive (`pgrep -f`), and
  if not, checks the completion condition (e.g. remaining row count in the source
  table). If the table is empty it removes its own cron entry (tagged with a
  known marker comment) and exits. If the table still has rows it restarts the
  job and logs the restart.
- Tag the cron line with a distinctive comment (e.g. `# hers-migrate-indicator-monitor`)
  so the self-removal step can target it precisely with `crontab -l | grep -v <marker>`.
- Run the monitor on a reasonable interval (15 min in this case) — frequent enough
  to catch a dead job before much time is lost, infrequent enough to not spam.
- The monitor must NOT write to the tables the job is working on — it only reads
  row counts and process state. A monitor that writes to the same tables can deadlock
  with the job (this session hit a MySQL deadlock because the migration's DELETE
  raced with another writer; the monitor itself must stay read-only on those tables).
- Document the monitor's exit conditions clearly so a future session knows the cron
  will disappear on its own when the job finishes (don't leave a "mystery cron" that
  silently stops firing).

This pattern is reusable for any "run until table X is empty, restart if it dies"
batch job. Capture the script path and marker comment in the relevant skill so the
next session can find and re-use or adapt it.

**Reference implementation:** the indicators migration monitor created this session
lives at `~/.hermes/scripts/migrate-indicators-monitor.sh` (or the cron job's `script`
field if a different path was used). It checks `pgrep -f migrate_indicators_json_to_columnar.py`,
queries `indicators_json` row count, restarts if dead and rows remain, and removes
itself when the count hits zero. Reuse as a template for any similar "process until
table empty" watchdog.

**Critical pitfall — self-removal in the Hermes cron system:** Hermès-managed cron jobs
live in `~/.hermes/cron/jobs.json` (managed via `cronjob` tool actions), NOT in the host's
`crontab`. A self-removal step in a job prompt that calls `crontab -l | grep -v <marker> |
crontab -` is DEAD CODE for Hermès jobs — the system crontab never had the entry. The
monitor will fire every interval forever, delivering status messages, even though the
monitored job completed long ago. This session's migration monitor (`59fc71e44a68`) ran 362
times over ~3 days because of exactly this: its prompt instructed `crontab -l | grep -v ...
| crontab -` but the job was Hermès-managed, so the removal never took effect. The
migration was actually complete (0 rows in `indicators_json`) but the monitor kept sending
"ok" status every 15 minutes until manually removed.

**Fix for Hermès-managed self-removing monitors:** use one of these approaches:
1. **Hermès API removal** — have the monitor run a Python snippet that edits
   `/root/.hermes/cron/jobs.json` directly (read, filter out the job ID, write back), then
   verify with `cronjob action=list`.
2. **`cronjob action=update`** — call `cronjob action=update` with `enabled=false` on the
   job's ID (requires the job ID to be known at prompt-writing time).
3. **Parent-session cleanup** — simpler and more reliable: don't self-remove. Have the parent
   session check `indicators_json` row count and remove the monitor when the job is done.

**Verification before trusting a self-removing monitor:** test the removal path manually.
Run the removal command and confirm the job disappears from `cronjob action=list`. If it
doesn't disappear, the self-removal is a no-op and the monitor will run forever.

### Pitfall: multi-copy scripts — the wrong copy gets executed

When a shell script exists at **both** the repo root (`$REPO_DIR/run_<name>.sh`) and the scripts subdirectory (`$REPO_DIR/scripts/run_<name>.sh`), the cron scheduler's `workdir` + `script=basename` resolution picks **one specific copy** — and it may not be the one you patched.

**Resolution rule**: `workdir=$REPO_DIR`, `script=run_<name>.sh` → cron executes `$REPO_DIR/run_<name>.sh` (the repo-root copy). The `scripts/` subdirectory copy is **not** what runs.

**Symptom**: you patch `scripts/run_<name>.sh` (which works when run manually from `scripts/`), but the cron job still fails with the same error. Root cause: the cron job is executing the repo-root copy, which you didn't patch.

**This session's case** (2026-09-22):
- TV Screener job: `workdir=/home/ksf_stockmarket/ksf_stockmarket`, `script=run_tv_screener.sh` → runs repo-root copy
- The `scripts/run_tv_screener.sh` copy already had `PYTHONPATH` — but the repo-root copy did **not**
- Same pattern for Zacks: `workdir=/var/www/stockmarket-app`, `script=run_zacks_refresh.sh` → runs `/var/www/stockmarket-app/run_zargs_refresh.sh` (repo-root copy), not the `scripts/` copy
- Both had repo-root copies lacking PYTHONPATH, causing `ModuleNotFoundError`
- Fix: patch **all** copies — repo-root + scripts/ + any other workdir copies (e.g. `/var/www/stockmarket-app/` copies for the `/var/www` workdir jobs)

**How to check**: when a job has `no_agent: true` and `script=<basename>`, run `find $workdir -name "$script" -type f` to see **all** copies. Patch every copy that the job could execute. Don't assume the copy you can see is the one the cron scheduler runs.

**Prevention**: when creating a new cron job shell script, put it at the repo-root level under `workdir` (not just in `scripts/`), or add a copy there. And always add `export PYTHONPATH="$REPO_DIR/python/src:$REPO_DIR/python"` (or the appropriate path for your script's imports) **before** the `.env` sourcing block.

### Quick verification after fixing a Python-import cron job

Python modules that live under `python/src/` (e.g. `python/src/db/exchange_routing.py`)
often need credentials from the shared connector `python/db_connector.py`, which lives at
the **repo root**, not under `python/src/`. The two are on different import paths — a module
at `python/src/db/` cannot do `import db_connector` and a module at the repo root cannot
import from `python/src/` unless the path is set up.

**Symptom:** `ModuleNotFoundError: No module named 'db_connector'` when running a script
under `python/src/`, even though `db_connector.py` exists at the repo root right next to
`python/`.

**Why this happens:** `db_connector.py` lives at the repo root (e.g.
`/home/ksf_stockmarket/ksf_stockmarket/python/db_connector.py`), while the new module lives
at `python/src/db/exchange_routing.py`. The repo root is on the import path for the entry
points (they add it via `sys.path.insert(0, parent_dir)`), but modules under `python/src/`
don't automatically get the repo root on their import path from the perspective of a direct
import.

**Fix — read the same env vars, don't import:**

When a `python/src/` module needs the same credentials as `db_connector`, read the same
environment variables directly via `os.environ.get()` rather than trying to import
`db_connector`. The credential source of truth is the **environment**, not the module — so
reading the same env vars (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_PORT`, `DB_NAME`) gives the
same result as going through `db_connector`, without the import-path coupling.

```python
# In a python/src/ module that needs DB credentials:
import os

def _default_host() -> str:
    return os.environ.get("DB_HOST", "ksfraser.ca")

def _default_user() -> str:
    return os.environ.get("DB_USER", "ksfraser_stockmarket")

def _default_password() -> str:
    return os.environ.get("DB_PASS", "")

def _default_port() -> int:
    try:
        return int(os.environ.get("DB_PORT", "3306"))
    except ValueError:
        return 3306
```

The values are identical to what `db_connector` uses because they come from the same env
vars. If `db_connector` ever changes how it sources credentials, update these helpers to
match — one place, still no import coupling.

**How to check:** if a `python/src/` module needs DB access, first try `import db_connector`
— if that fails with `ModuleNotFoundError`, fall back to env-var reads. If the module is
being called from a `python/` entry point that already has the repo root on `sys.path` and
`python/` has an `__init__.py`, the import path may work — but don't rely on it for modules
under `python/src/`. Env-var reads are the portable path.

**Note:** this is a *credential-sharing* pattern, not a replacement for the common connector
rule. The common connector rule still applies — all DB access goes through one path. When the
module's import path can reach the connector, use it. When it can't (because of the directory
layout), share the credential source (env vars) so there is still exactly one source of truth
for passwords — just not via import.

## Workflow preference: DB-infrastructure changes ship with tests + docs

When the user asks for a DB-layer change (new DAO, new repository, new routing, schema
change, new connector pattern), **code alone is not done.** The deliverable is code + unit
tests + requirements/architecture doc updates. A patch that only touches the implementation
file and skips tests and docs is incomplete, not quick.

Concrete expectations that came from this session's exchange-routing + stockprices-DAO work:

- **Unit tests:** a `tests/unit/test_<module>.py` that exercises the new module's public API
  with SQLite fixtures (matching `tests/unit/test_db_adapter.py` style) and mocks the
  connection path. Pure functions get direct tests; connection-dependent paths get stubbed
  tests. No MariaDB in default CI.
- **Requirements doc:** a `docs/requirements/FR-<feature>.md` that states the functional
  requirement, acceptance criteria, and constraints (storage-tier rule, common-connector
  rule, exchange-routing rule). Mirrors the style of `FR-stockprices-exchange-routing.md`.
- **Architecture doc:** `docs/ARCHITECTURE_PYTHON.md` updated to reflect the new layer's place
  in the stack (which layer, which contract, which directories it owns).
- **AGENTS.md:** if the change introduces a rule that other agents will encounter (e.g. "all
  MySQL writes go through a DAO, never raw SQL in business scripts"), add it to
  `AGENTS.md` as a canonical rule so future agent sessions don't bypass it.
- **The code commit should include the tests and doc updates in the same commit** — not as
  a follow-up "oh I forgot the tests" later. If the tests can't be written yet (e.g. need a
  schema that doesn't exist), that's a reason to split the task, not to ship code without them.

This preference was stated explicitly by the user in the context of the exchange-routing + DAO
build ("Make sure to ALSO update requirements documents, architecture, test cases, unit tests,
etc.") and applies to any DB-infrastructure task in this repo — not just that one.

## Related skills

- **stockmarket-nightly-pipeline** — the stockmarket-app-specific nightly workflow (Zacks scrape + signal dispatch + verify + report). Use this skill when the cron job targets `/var/www/stockmarket-app` and involves `python/zacks_scraper.py` or signal dispatch. The cronjobs skill covers generic cron debugging; this skill covers the stockmarket application layer on top of it.

- [2026-09-07 TV Screener + Zacks cron job failures](references/2026-09-07-cron-job-failures.md) — full root-cause analysis, fixes, verification, and the "ready to merge to main" assessment for this session's three failing jobs.

- [2026-09-13 indicators migration: log trim + monitor restart + cron pause sweep](references/2026-09-13-indicators-migration-recovery.md) — session-specific detail: how the migration was restarted after the cron pause sweep killed it, how `/tmp` was recovered by trimming the log to last 5000 lines, and the resulting "all paused except the watchdog" state.

- [Exchange routing module — reference implementation](references/exchange-routing-module.md) — the `python/src/db/exchange_routing.py` module built this session, captured as a reference for the `python/src/` import-path pitfall and the exchange-routing contract.
- [Ephemeral SQLite price sync — `sync_stock_prices.py --sqlite`](references/sync-stock-price-ephemeral.md) — verified invocation, PYTHONPATH rules, SQLite-only write behavior, decoy-DB trap, and verification recipe (session 2026-09-25).

## Intraday detection cron (investment-agent)

Weekday market-hours alert detection that writes to a throwaway SQLite store instead of MariaDB.
The canonical command is `cd /root/.hermes/workspace/investment-agent && /usr/bin/python3.10
detection_triggers.py --sqlite`. There are NO MariaDB writes during intraday (only a read-only
`watchlist_symbols` SELECT); all alert writes go to `ANALYTICS_DB` = `~/.hermes/cache/analysis_results.db`
`alert_queue`. For the full invocation detail, the stdout-vs-store anomaly class
(`volume_spike`/`gap_up` reported-written-but-absent), the decoy-DB trap, and the verification recipe,
see the dedicated reference `references/intraday-detection-cron.md` (this skill), which cross-references
`investment-agent-data-access/references/detection-triggers.md` for the deep write-path anomaly writeup.