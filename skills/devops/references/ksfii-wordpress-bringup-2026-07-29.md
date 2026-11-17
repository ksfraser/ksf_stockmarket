# ksfii_app WordPress Bringup — 2026-07-29

## Final State

| Component | Name | Port | Status |
|---|---|---|---|
| Pod | `ksfii-pod` (root) | — | Running |
| MariaDB | `ksfii-mariadb` | 3306 (pod) | Up, bind-mounted `/opt/ksfii/mariadb/data`. Root auth from ansible inventory/hosts.ini |
| WordPress | `ksfii-wordpress` | 8083 → 80 | Up, mount `podman_wp_data/_data:/var/www/html` |

## Credentials (from ansible inventory/hosts.ini)

- MariaDB root: `m1l1ce`
- MariaDB `wordpress` user: `Zaqwsx9wordpress`

## Facts

- Kevin's `ksf-fa` lives in his **own rootless podman** instance under user `kevin`, bound to host 8080 — unaffected by the root podman pod.
- Pod `8080:80` mapping was removed to avoid colliding with ksf-fa.
- Original pod could not start because it published port 53, which collides with `systemd-resolved` / `dnsmasq`.
- MariaDB bind mount `/opt/ksfii/mariadb/data` preserved; InnoDB recovered cleanly.
- WordPress `siteurl` + `home` patched via `wp-load.php` + `update_option()` to break the `localhost`-rooted redirect loop.

## Pitfalls encountered

1. **removing/rebuilding pod without checking other users' containers** — killed ksf-fa access to 8080. Always `su - kevin -c "podman ps ..."` before any destructive pod action.
2. **`mysqld` vs `mariadbd` in official image** — `mariadb:latest` entrypoint fails when `--skip-grant-tables` is passed because command `mysqld` doesn't exist. Avoid `--skip-grant-tables` with this image.
3. **WordPress URL rooting** — installer/`siteurl` defaults to `http://localhost`. After install, update both `siteurl` and `home` to the real host:port, otherwise `curl http://127.0.0.1:8083` triggers a 301 to `http://127.0.0.1/` which 403s.
4. **`wp_install()` CLI requires `HTTP_HOST`** — fallback PHP CLI installer with wp_install sets off a warning unless `HTTP_HOST=localhost:8083` is in env.
5. **curl POST from inside pod** — WordPress `install.php?step=2` must be POSTed to `localhost:80` (container-internal). `localhost:8083` from inside the container returns Connection refused.
