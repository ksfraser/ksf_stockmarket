# ksf_stockmarket Deployment Gotchas

## Dual-webroot layout
- Private workspace: `/var/www/stockmarket-app/`
- Apache webroot: `/var/www/html/stockmarket/`
- PHP controllers/templates must exist in BOTH or requests return 500/404
- When adding new files, copy/sync to webroot explicitly

## File permissions
- New files under `/var/www/stockmarket-app/` may be created `600 root:root`
- PHP-FPM cannot read `600` files → HTTP 500 with empty body
- Fix: `chmod 644 <new_file>` immediately after creation
- Verify: `ls -la` should show `-rw-r--r--`

## Debugging HTTP 500 with empty body
1. Check `/var/log/php-fpm/www-error.log` first — contains PHP fatal errors
2. Then `/var/log/httpd/error_log` or `/var/log/apache2/error.log`
3. CLI `php -l <file>` catches parse errors before deployment
4. `curl -s -w "\nHTTP:%{http_code}\n" <url>` confirms status code

## Admin Settings / system_settings
- Credentials saved as `password` type are stored plaintext in DB but masked in UI
- `AdminSettingsController::saveSettings()` uses INSERT ... ON DUPLICATE KEY UPDATE
- `.env` sync is partial (only Discord keys currently)

## MariaDB JSON quirks
- Use `JSON_OBJECT()` for objects, JSON-encode arrays as strings
- `JSON_EXTRACT(col, '$[0].field')` for reading arrays
- Python `DECIMAL` → use `_HermesJSONEncoder` or `default=str`
