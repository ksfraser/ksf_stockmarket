# Templates — Location & Deployment

## Where templates live

| Rendering mode | Path in repo | Files |
|---|---|---|
| **Main PHP** | `php/templates/` | `detail.php`, `portfolio.php`, `layout.php`, `layout_detail.php`, `css.php`, etc. |
| **Enhanced / Python-named** | `python/*.php` | `detail_enhanced.php`, `detail_old.php`, `shared_with_me.php`, and their controllers |
| **Dashboard** | `dashboard/templates/` | `DashboardController.php`, dashboard-specific views |

> **Note:** `python/` is a legacy directory name. It contains PHP templates and controllers, not Python code. The actual Python backend lives in `python/src/`.

## Server layout (current)

```
/var/www/html/stockmarket/    ← Apache DocumentRoot (public only)
    index.php                 ← Front controller
    js/                       ← Static assets
    uploads/                  ← User uploads (writable by apache)

/var/www/stockmarket-app/     ← Private app workspace (authoritative source)
    php/templates/            ← Main templates
    python/detail.php etc.    ← Enhanced templates  
    dashboard/templates/      ← Dashboard templates
    php/src/                  ← Controllers, models, services
    python/src/               ← Python backend
    vendor/                   ← Composer deps
    config.yaml
```

## Deployment targets

### VPS (bullet-proof — recommended)

`deploy.sh` mode `vps`.

```
public_html → /var/www/html/stockmarket/
app         → /var/www/stockmarket-app/
```

Only `index.php`, `js/`, and `uploads/` are in the webroot. Everything else is outside the document root and cannot be fetched directly via URL.

### Shared hosting (WHC, etc.)

`deploy.sh` mode `shared`.

```
public_html/stockmarket/      ← Webroot on shared host
    index.php
    assets/js/
    app/                      ← Protected by .htaccess
        php/templates/
        python/
        dashboard/
        src/
        vendor/
```

A `.htaccess` file in `app/` blocks direct HTTP access to private code.

## Why the split?

- **Security:** Controllers, models, and config cannot be downloaded if PHP fails or misconfigures.
- **OPcache friendly:** Templates in a non-webroot path don't get cached aggressively by Apache as static files.
- **WHC compatible:** On shared hosting, deploy the whole thing into `public_html/stockmarket/` and `.htaccess` does the rest.
