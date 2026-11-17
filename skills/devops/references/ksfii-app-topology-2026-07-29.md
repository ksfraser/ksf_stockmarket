# ksfii App Topology — 2026-07-29

## Apps and Ownership

| App | Runtime | URL / Port | DB | Owner |
|---|---|---|---|---|
| ksf_stockmarket | bare-metal Apache + PHP-FPM | `192.168.1.102/stockmarket/` | remote `ksfraser.ca:3306` (`ksfraser_stock_market`) | rootful services |
| ksf-fa (FA) | rootless Podman container | `192.168.1.102:8080` | its own `ksf-mariadb` pod container, db `ksf_fa`, user `ksf_user` | user `kevin` rootless podman |
| ksf-tesseract | rootless Podman | `192.168.1.102:8100` | — | user `kevin` |
| ksfii-pod (rootful) | root Podman pod | WP: `127.0.0.1:8083` only | `ksfii-mariadb` in same pod, db `wordpress` fresh core install | root podman |

## Critical Rules

- **Port 8080 is reserved for ksf-fa.** The rootful pod must NOT publish `8080:80`. Future ksfii apps needing port 80 must use 8081–8086.
- **`ksfraser.ca` is NOT this host** — it resolves to `67.215.3.243`. The bare-metal stockmarket vhost uses it as ServerName, but local access is always via `192.168.1.102/stockmarket/`.
- **Estate Planning sub-app**: exists only as code/tests/docs in `/home/kevin/Documents/ksfii_app/`. Not deployed. No URL, no DB tables, no credentials.
- **SuiteCRM**: files exist in `/var/www/html/` under bare-metal docroot but no VirtualHost exposes it by default.
- **FrontAccounting**: runs inside Kevin's rootless `ksf-fa` container, not in rootful podman.
- **ksfii_mariadb data**: bound from `/opt/ksfii/mariadb/data/` on host. **Never remove or recreate the ksfii-pod without verifying this bind mount is re-attached.**

## DB Ownership Map

| DB host | DB name | App | How to connect |
|---|---|---|---|
| `ksfraser.ca:3306` | `ksfraser_stock_market` | bare-metal stockmarket | `mariadb -h ksfraser.ca -u ksfraser_stockmarket -p<pass_from_vhost>` |
| `ksf-mariadb` (pod DNS) | `ksf_fa` | ksf-fa | pod DNS name `ksf-mariadb`, NOT localhost |
| `127.0.0.1:3306` in ksfii-pod | `wordpress` | WordPress | `wordpress`/`<pass>` via env in container |

## ksf-fa DB Connectivity Detail

Inside `ksf-fa`, `config_db.php` uses `host=ksf-mariadb`, `dbuser=ksf_user`, `dbpassword=ksfuser2024!`, `dbname=ksf_fa`, `tbpref=0_`. This is pod-internal DNS resolution. Do not change to `localhost` unless recreating the MariaDB container explicitly with `--network=host`.

## Filesystem Layout

| Path | Owner | Notes |
|---|---|---|
| `/home/kevin/Documents/ksfii_app/` | `kevin` | working copy of ksfii_app |
| `/home/kevin/Documents/PersonalRecordsOrganizer/` | `kevin` | executor-facing app (not deployed) |
| `/home/kevin/Documents/ksf_<module>/` | `kevin` | individual FA modules (CRM, Calendar, etc.) |
| `/var/www/html/stockmarket/` | root | stockmarket webroot |
| `/var/www/stockmarket-app/` | root | stockmarket private code, NOT web-accessible |
| `/opt/ksfii/mariadb/data/` | root | ksfii MariaDB datadir — **bind-mounted, never clobber** |

## Pod and Services to Avoid

| Port | Why |
|---|---|
| `53/tcp` | conflicts with `dnsmasq` / `systemd-resolved` |
| `8080/tcp` | reserved for Kevin's rootless ksf-fa |
