# DB Sync Without Native Replication (outbox + cron container)

Reusable pattern for syncing a local MariaDB/MySQL to a **remote host that cannot
be a replica** (shared CPanel: no `my.cnf`, no `server-id`, no binlog, no `SUPER`
for `CHANGE MASTER`). Native GTID replication only works if you have root/WHM on
the remote — otherwise use this application-level approach.

## Architecture

Two co-located pairs + async sync container (the cron container travels with the
workload because it's baked into the image / a mounted volume, not a host
crontab):

- LAN pair: app + local MariaDB (fast local work).
- Webhost pair: app + CPanel MariaDB (fast prod).
- `db-sync` container: replays local → webhost. Never serve live WAN queries.

## Option A — nightly full clone (`nightly_dump.py`, e.g. `0 3 * * *`)

```python
# mysqldump piped straight into the remote; exclude outbox + triggers.
subprocess.Popen(["mysqldump","-h",LOCAL_HOST,"-u","root",
  "--single-transaction","--skip-triggers",
  "--ignore-table=%s.fa_sync_outbox"%LOCAL_NAME, "--databases", LOCAL_NAME],
  stdout=open(dump_path,"w"), env={"MYSQL_PWD":ROOT_PASS})
subprocess.Popen(["mysql","-h",WEB_HOST,"-u",WEB_USER,WEB_NAME],
  stdin=open(dump_path), env={"MYSQL_PWD":WEB_PASS})  # drop+recreate => clean refresh
```
- Passwords via `MYSQL_PWD` env (not `-p`) to avoid process-list exposure.
- Keep a rotating local copy under a **named volume** (`/backups`, 7-day
  retention) — NOT the git repo (git stores full snapshots, so committing dumps
  balloons the repo; untrack with `git rm --cached` if previously committed).

## Option B — intraday delta (`setup_outbox.py` + `sync_outbox.py`, e.g. `*/5 * * * *`)

`setup_outbox.py` (idempotent, runs at container start) creates:
```sql
CREATE TABLE IF NOT EXISTS fa_sync_outbox (
  id BIGINT PK AUTO_INCREMENT, tbl VARCHAR(128), op ENUM('I','U','D'),
  row_json JSON, pk_json JSON,
  status ENUM('pending','inflight','sent','error') DEFAULT 'pending',
  batch_id INT, attempts TINYINT, error TEXT, created_at TIMESTAMP,
  INDEX ix_status (status));
```
…and, for every user table (denylist `fa_sync_outbox`, `information_schema`,
`mysql`, `performance_schema`, `sys`; optional `SYNC_TABLES` allowlist), installs
`AFTER INSERT/UPDATE/DELETE` triggers that `INSERT INTO fa_sync_outbox
(tbl,op,row_json,pk_json) VALUES (... JSON_OBJECT(<cols>), JSON_OBJECT(<pk>))`.

`sync_outbox.py` replay (the corrected transaction design):
```python
# 1) CLAIM — short LOCAL transaction only
cur.execute("SELECT id,tbl,op,row_json,pk_json FROM fa_sync_outbox "
            "WHERE status='pending' ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED",(BATCH,))
ids=[r[0] for r in cur.fetchall()]
bid=time-based
cur.execute("UPDATE fa_sync_outbox SET status='inflight',batch_id=%s,attempts=attempts+1 "
            "WHERE id IN %s",(bid,tuple(ids)))
lc.commit()
# 2) TRANSMIT — REMOTE's own transaction (separate connection)
for tbl,trows in by_tbl.items():
    # one INSERT ... ON DUPLICATE KEY UPDATE per table (ins), DELETEs for op 'D'
    cur.executemany("INSERT INTO `%s` (...) VALUES (...) ON DUPLICATE KEY UPDATE ..."%tbl, data)
    cur.executemany("DELETE FROM `%s` WHERE ..."%tbl, del_pks)
wc.commit()
# 3) ACKNOWLEDGE — short LOCAL transaction
cur.execute("UPDATE fa_sync_outbox SET status='sent' WHERE batch_id=%s",(bid,))
```
On remote failure: return batch to `pending` (capped at `SYNC_MAX_ATTEMPTS`,
then `error`). Purge `sent` rows older than 7 days each run.

**Why this shape:** a transaction cannot span two servers; locking the outbox
during a WAN round-trip is a long-lived txn. Claim→Transmit→Ack with idempotent
upserts is resumable and never needs manual replica restart.

## Container build gotchas (Alpine `FROM alpine:*`)
- `pip install` is blocked by PEP 668 → use `apk add py3-pymysql` (not pip).
- `dcron` APK package has no `dcron` binary → use busybox `crond` (built-in):
  `exec crond -f` as PID 1. Crontab at `/var/spool/cron/crontabs/root` (no user col).
- Verify before committing: `podman build`, then
  `podman run --rm --entrypoint sh <img> -c "which crond; python3 -c 'import pymysql'; python3 -m py_compile /usr/local/bin/*.py"`.
  (The image `ENTRYPOINT` swallows appended args — use `--entrypoint` to test.)

## Compose wiring (pod definition)
Add a `db-sync` service that `build:`s the sync image, sets `LOCAL_DB_*` (source)
and `WEBHOST_DB_*` (clone target) from the env file, mounts a `…_backups` volume,
`depends_on: mariadb: condition: service_healthy`, `restart: unless-stopped`.
The external `ksf.pod` ansible role just consumes this compose file.

## Operational notes
- Webhost must whitelist the container's egress IP (CPanel Remote MySQL); a
  moved workload needs the allowlist updated.
- Least-privilege webhost user (INSERT/UPDATE/DELETE on the FA tables only).
- Bootstrap a fresh webhost by running Option A once; Option B needs no bootstrap.
- `SYNC_TABLES=tbl1,tbl2` to limit trigger creation to an allowlist.
