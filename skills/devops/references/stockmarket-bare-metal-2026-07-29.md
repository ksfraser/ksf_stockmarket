# ksf_stockmarket Bare-Metal Layout — 2026-09-22 (updated)

## Architecture

ksf_stockmarket is **NOT** containerized. It runs as bare-metal Apache + PHP-FPM on the ksfii host.
The podman containers (ports 8090-8092) are **separate dev environments** (FrontAccounting, phpMyAdmin, WordPress) — NOT the stockmarket app.

**CRITICAL — stockmarket unreachable checklist:**
1. `systemctl is-enabled httpd` — must be `enabled`. If `disabled`, Apache isn't starting at boot.
2. `systemctl is-enabled php-fpm` — must be `enabled`. Without PHP-FPM, PHP files are not executed (Apache serves static HTML only, or returns 503).
3. `systemctl status httpd` — must be `active (running)`. Config syntax OK (`httpd -t`) does NOT mean it's running.
4. `ss -tlnp | grep ":80 "` — must show httpd listening. If nothing on port 80, httpd is down.
5. `/run/php-fpm/www.sock` — must exist as a socket (`srw-rw----`). Without it, PHP proxy handler fails.
6. All 5 checks must pass for stockmarket to be reachable. A config that passes `httpd -t` can still be offline.

## Paths

| Layer | Path | Served? |
|---|---|---|
| Webroot | `/var/www/html/stockmarket/` | Public — `Alias /stockmarket /var/www/html/stockmarket` |
| Private app code | `/var/www/stockmarket-app/` | NOT served by Apache |

## Apache Config

**Active config:** `/etc/httpd/conf.d/ksfraser.conf`
- **NO VirtualHost** — uses `Alias /stockmarket /var/www/html/stockmarket` at server scope.
- PHP via FPM unix socket: `SetHandler "proxy:unix:/run/php-fpm/www.sock|fcgi://localhost"`
- DB creds via `SetEnv` in the same file:
  ```
  SetEnv DB_HOST ksfraser.ca
  SetEnv DB_NAME ksfraser_stock_market
  SetEnv DB_USER ksfraser_stockmarket
  SetEnv DB_PASS Zaqwsx9sm1@
  SetEnv DB_CHARSET utf8mb4
  ```

**Stale backup:** `/etc/httpd/conf.d/stockmarket.conf.bak` — OLD VirtualHost layout (`<VirtualHost *:80>`, ServerName ksfraser.ca). **NOT active.** Do not restore this file — it uses a different config pattern than the current `ksfraser.conf`.

## Services

| Service | Status (2026-09-22) | Notes |
|---|---|---|
| `httpd.service` | enabled + running | Apache 2.4.57 (Fedora 36) |
| `php-fpm.service` | enabled + running | PHP-FPM, socket at `/run/php-fpm/www.sock` |
| `httpd.socket` | disabled | Socket activation not used |

## Database

Remote MariaDB at `ksfraser.ca:3306`, database `ksfraser_stock_market`, user `ksfraser_stockmarket`, password from `ansible/inventory/hosts.ini:wordpress_db_password` (also in `SetEnv DB_PASS`).

## Access

- `http://ksfraser.ca/stockmarket/` — main dashboard (public)
- `http://192.168.1.102/stockmarket/` — local LAN access
- `http://localhost/stockmarket/` — local host access (curl test: HTTP 200, 24KB, PHP executing)

## Cron Job Shell Script Bug (2026-09-22)

**Symptom:** Cron jobs fail with `ModuleNotFoundError: No module named 'db'` even though the Python files import fine from the CLI.

**Root cause:** Shell wrapper scripts (`run_tv_screener.sh`, `run_zacks_refresh.sh`, `run_ingest_screener.sh`) do not export `PYTHONPATH` before invoking `python3`. When `no_agent=true` cron jobs run the wrapper, Python can't find `db.stockprice_dao` etc.

**Fix:** Add `export PYTHONPATH="$REPO_DIR/python/src:$REPO_DIR/python"` (or `$REPO_DIR/python:$REPO_DIR` for non-DB scripts) BEFORE the `python3` invocation in every shell wrapper. Four copies of each script may exist (repo-root + `scripts/`, ksf_stockmarket + `/var/www/stockmarket-app`) — fix ALL copies.

**Affected files (2026-09-22):**
- `run_tv_screener.sh` (4 copies)
- `run_zacks_refresh.sh` (4 copies)
- `run_ingest_screener.sh` (2 copies: `/var/www/stockmarket-app/` root + `scripts/`)
- `populate_analyst_ratings.sh` — already has PYTHONPATH (check pattern)

**Pattern to look for:** any `*.sh` in `scripts/` or repo root that does `cd $REPO_DIR` + `python3 something.py` without a preceding `export PYTHONPATH=...`.