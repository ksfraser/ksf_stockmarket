# ksf_stockmarket — Agent/Developer Guide

## Scope
This repo contains the ksf_stockmarket application at ksfraser.ca. It splits into a public web front (`public_html/`) and a private app root deployed to `/var/www/stockmarket-app/`. All code paths must be deployable via `./deploy.sh vps`.

## Coding standards
- **PSR-4** class autoloading under `src/`. Controllers, Models, and Utilities all resolve from `src/<Type>/<Class>.php`.
- **SOLID / DRY / DI / SRP**: shared business rules live in controllers/util classes, not copy-pasted across templates or routes.
- **Docblocks**: every public method/property must have a one-line summary plus `@param`/`@return` where non-trivial.
- **Defensive programming**: never read array keys without null coalescing or `??`. Default to `''`, `0`, or typed defaults where sensible.
- **Production errors**: `error_reporting(E_ALL)` is required, but `ini_set('display_errors', '0')` everywhere shipped to webroots. Errors must go to `$APP_ROOT/logs/php_errors.log`. Never leave `display_errors=1` in production entry points.
- **Naming**: yfinance requires `.TO` (or exchange-suffixed) tickers for non-US equities. Do not inline `.TO`/.UN fallbacks in controllers or templates. Use the centralized resolver.

## Canonical symbol resolution
- **Python**: `python/src/symbol_resolver.py` exposes `resolve_for_yfinance(symbol)`. Every script that calls `yf.Ticker()` or `yf.download()` must route through `resolve_for_yfinance()`.
- **PHP**: `php/src/Util/SymbolResolver.php` exposes `resolve(symbol)`. Controllers must instantiate `SymbolResolver` in the constructor and call `$this->resolver->resolve()` for all user/symbol lookups.
- **DB shape**: `symbol_master.symbol` is canonical. `.TO` / `.UN` / `.V` / `.B.TO` → `-TO` / `-UN.TO` / `-B.TO` canon forms only live in yfinance calls, never in DB writes.

## Python guardrails
- All Python scripts must `import symbol_resolver` and call `resolve_for_yfinance()` before any `yf.Ticker()` / `yf.download()`.
- Do not add new local resolver stubs (`KNOWN_TSX`, `KNOWN_US`, `normalize_symbol()`). Use the canonical resolver.

## Deploy and CI
- `deploy.sh vps` rsyncs `public_html/`, templates, `php/src/`, `python/src/`, and `scripts/` to both VPS roots. After deploy, Apache ownership applies to templates and `src/Util`.
- **Smoke test before push/merge**:
  - `php tests/test_symbol_resolver.php` → must pass 16/16 with exit 0.
  - `python3 -m py_compile python/src/symbol_resolver.py` and `python3 -m py_compile python/data_importer.py` → must pass.
  - `grep -R "yf\\.Ticker\\|yf\\.download" python/ | grep -v "resolve_for_yfinance"` → must return empty.
  - `grep -R "new SymbolResolver" php/src/Controller/` → must show all new-style controllers wiring resolver; `grep -R "strtoupper.*symbol" php/src/Controller/` should not contain bare `.TO`/yfinance fallback logic.
- Test data: never modify live export HTML, currentdata, or seed SQL unless explicitly requested.

## Database safety
- Read-only MySQL user: `ksfraser_stockmarket`. Writes require explicit deploy scripts or protected admin routes only.
- `symbol_master` must have zero NULL `name` and `exchange` values. Backfill via `python/refresh_symbol_info.py` rather than manual SQL.
- Portfolio symbol identity: update `portfolio.price_symbol` to `.TO` variants, then re-import prices.

## Templates
- Every numeric/boolean field presented to the user needs a tooltip that explains what it means and how it is calculated — not a restatement of the label.
- Do not invoke controllers or business logic from templates. Templates format data only.
