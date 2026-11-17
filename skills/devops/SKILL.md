---
name: devops
description: "Deploy and troubleshoot containerized application stacks, webhook subscriptions, and event-driven automation."
tags: [podman, containers, deployment, webhooks, events, automation, ci-cd, rootless, multi-user]
---

# DevOps

Class-level umbrella for container deployment and webhook automation.

## 1) Podman Deployment — `podman-deployment`

Deploy and troubleshoot Podman-based containerized application stacks with pods, volumes, and host port bindings. Covers port-conflict resolution, stale rootlessport cleanup, network-namespace verification, container recreation inside pods, and WordPress-specific bring-up steps (DB seeding, installer automation).

References: app topology, WordPress bring-up, WiFi recovery, bare-metal stockmarket layout, portfolio fork capabilities, cron job debugging.

## 2) Webhook Subscriptions — `webhook-subscriptions`

Create dynamic webhook subscriptions so external services (GitHub, GitLab, Stripe, CI/CD, IoT sensors, monitoring tools) can trigger Hermes agent runs by POSTing events to a URL. Supports prompt templates, HMAC validation, and direct delivery (no LLM cost).

## 3) Database Sync Without Native Replication — `db-sync-outbox`

When the target DB is on **shared CPanel / managed hosting** (no `my.cnf` access, no `server-id`, no binlog, no `SUPER` for `CHANGE MASTER`), native MariaDB/MySQL replication is impossible in either direction. The durable fix is an **application-level change feed** driven by a **cron container that travels with the workload** (baked into the image / a mounted volume — NOT a host crontab, so it moves when the container moves).

Two complementary jobs (both push local → remote clone / offsite backup):
- **Option A — nightly full clone:** `mysqldump --single-transaction --skip-triggers --ignore-table=<db>.outbox <db> | mysql -h <remote>` (excludes the outbox table + triggers so the clone stays pure data). Keep a rotating local copy in a **named volume, never the git repo**.
- **Option B — intraday delta:** an `outbox` table + per-table `AFTER INSERT/UPDATE/DELETE` triggers that write each changed row as JSON. A worker claims a batch (`SELECT … WHERE status='pending' … FOR UPDATE SKIP LOCKED` → `UPDATE … status='inflight'`), replays to the remote as idempotent `INSERT … ON DUPLICATE KEY UPDATE` (one per table) + `DELETE`s, then marks `sent`. On failure returns the batch to `pending` (capped → `error`).

**Transaction correction (key insight):** a single transaction cannot span two DB servers, and holding locks during a WAN round-trip is a long-lived txn. Split into three: (1) short local txn claims the batch, (2) transmit on the **remote's own** transaction, (3) acknowledge with a local txn. Idempotent upserts make replay safe — this is exactly why it avoids the "replication stopped, nightmare to resume" problem.

Full recipe + transaction detail in `references/db_sync_outbox_pattern.md`.

## 5) Cron Job Debugging — `cronjobs`

Debug and fix cron jobs whose shell wrappers fail because the script path doesn't resolve relative to the job's workdir, or whose Python entry point gets empty DB creds because the wrapper didn't source `.env`. Covers no_agent=true mode, script-path resolution, env sourcing, and verifying a cron job actually runs before trusting its status.

### PYTHONPATH pitfall

Shell wrapper scripts (`run_tv_screener.sh`, `run_zacks_refresh.sh`, `run_ingest_screener.sh`) that do `cd $REPO_DIR` + `python3 something.py` without exporting `PYTHONPATH` first will fail in cron with `ModuleNotFoundError` even though the imports work from CLI. Fix: add `export PYTHONPATH="$REPO_DIR/python/src:$REPO_DIR/python"` before the `python3` call. Four copies of each script may exist (repo-root + scripts/, ksf_stockmarket + /var/www/stockmarket-app/) — fix all copies. Any `*.sh` doing `cd $REPO_DIR` then `python3 something.py` without `export PYTHONPATH=...` is vulnerable.

When authoring a `Containerfile`/`Dockerfile` from `alpine:*`:
- **PEP 668 externally-managed Python:** `pip install` fails ("externally-managed-environment"). Install Python libs via APK instead — `apk add py3-<pkg>` (e.g. `py3-pymysql`, `py3-requests`). Do NOT rely on `pip`.
- **Cron daemon:** the `dcron` APK package does **not** provide a `dcron` binary. Alpine ships **busybox `crond`** built-in (`/usr/sbin/crond`). Run it as PID 1 in foreground: `exec crond -f`. Per-user crontabs live at `/var/spool/cron/crontabs/<user>` (no username column in the file).
- **Verify before committing:** always `podman build` the image and smoke-test it. `podman run --rm --entrypoint sh <img> -c "which crond; python3 -c 'import pymysql'; python3 -m py_compile /usr/local/bin/*.py"` — note the image `ENTRYPOINT` ignores appended args, so use `--entrypoint` to run your own check command.
- **Co-location principle:** keep each app co-located with its own DB; the cron container only syncs clones in the background. Never serve live queries across the WAN (that is the actual latency root cause, not "slow DB").

Detail + ready-to-adapt scripts in `references/db_sync_outbox_pattern.md`.

## Rules

1. Check both rootful and rootless Podman for port conflicts before destroying any pod.
2. Never kill another user's container to free a port; remove the port from your own pod instead.
3. Verify webhook HMAC secrets match the service configuration; stale secrets cause 401s.
4. Always `podman build` + smoke-test a Containerfile before committing it — do not ship an unbuilt image definition.
