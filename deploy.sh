#!/usr/bin/env bash
# deploy.sh — Deploy stockmarket app to VPS or shared hosting
#
# Repo layout (source):
#   public_html/               ← public entry points + assets
#   php/index.php              ← CANONICAL front controller
#   php/templates/             ← main PHP templates (36 files)
#   php/src/                   ← PHP controllers, models, services
#   python/*.php               ← enhanced/detail templates + controllers (legacy name)
#   python/src/                ← Python backend
#   dashboard/                 ← dashboard templates + controllers
#   scripts/                   ← CLI scripts
#   tests/                     ← test suites
#   external/                  ← docs, reference files
#   vendor/                    ← (gitignored) Composer deps, run composer install
#
# VPS deploy result:
#   /var/www/html/stockmarket/    ← webroot (index.php, js/, uploads/, .htaccess)
#   /var/www/stockmarket-app/     ← private app (templates, src, python, config, etc.)
#
# Shared hosting deploy result:
#   public_html/stockmarket/      ← flattened; .htaccess protects private dirs
#       index.php
#       templates/
#       src/
#       python/
#       controllers/
#       docs/
#       vendor/
#       scripts/
#       tests/
#       external/

set -euo pipefail

MODE="${1:-vps}"
shift || true

case "$MODE" in
  vps)
    HOST="${1:-root@192.168.1.102}"
    shift || true
    WEBROOT="${1:-/var/www/html/stockmarket}"
    APPROOT="${1:-/var/www/stockmarket-app}"
    shift || true

    echo "Deploying to VPS: $HOST"
    echo "  Webroot:    $WEBROOT"
    echo "  App root:   $APPROOT"

    # 1) Public files → webroot
    rsync -av --delete \
        public_html/ "$HOST:$WEBROOT/"

    # 2) Templates from all sources → app root
    rsync -av php/templates/                "$HOST:$APPROOT/templates/"
    rsync -av php/templates/partials/detail/ "$HOST:$APPROOT/templates/partials/detail/"
    rsync -av python/*.php                  "$HOST:$APPROOT/"
    rsync -av dashboard/templates/          "$HOST:$APPROOT/dashboard/templates/"
    rsync -av dashboard/src/Controller/     "$HOST:$APPROOT/controllers/"
    rsync -av dashboard/config/             "$HOST:$APPROOT/config/"
    for f in dashboard/*.php; do
      [ -f "$f" ] && rsync -av "$f" "$HOST:$APPROOT/"
    done

    # 3) PHP app code
    rsync -av php/src/                      "$HOST:$APPROOT/src/"
    rsync -av php/config/                   "$HOST:$APPROOT/config/"
    rsync -av config.yaml                   "$HOST:$APPROOT/config.yaml"

    # 4) Python backend
    rsync -av python/src/                   "$HOST:$APPROOT/python/src/"
    rsync -av python/*.py                   "$HOST:$APPROOT/python/"

    # 5) Scripts, tests, external
    rsync -av scripts/                      "$HOST:$APPROOT/scripts/"
    rsync -av tests/                        "$HOST:$APPROOT/tests/"
    rsync -av external/                     "$HOST:$APPROOT/external/"

    # 6) Remind user
    echo ""
    echo "=== Post-deploy ==="
    echo "  Hard refresh browser (Ctrl+Shift+R)"
    echo "  If tooltips missing: clear browser cache or try incognito"
    ;;

  shared)
    TARGET="${1:-/home/username/public_html/stockmarket}"
    shift || true

    if [[ -z "$TARGET" ]]; then
      echo "Usage: $0 shared /path/to/public_html/stockmarket"
      exit 1
    fi

    echo "Deploying to shared hosting: $TARGET"
    mkdir -p "$TARGET"

    # Public files
    rsync -av --delete \
        --exclude='.git' \
        --exclude='deploy.sh' \
        --exclude='TEMPLATES.md' \
        --exclude='node_modules' \
        public_html/ "$TARGET/"

    # Templates (all sources)
    rsync -av --delete \
        --exclude='.git' \
        php/templates/            "$TARGET/templates/"
    rsync -av --delete \
        --exclude='.git' \
        php/templates/partials/detail/ "$TARGET/templates/partials/detail/"
    rsync -av --delete \
        --exclude='.git' \
        python/*.php              "$TARGET/"
    rsync -av --delete \
        --exclude='.git' \
        dashboard/templates/      "$TARGET/templates/"
    rsync -av --delete \
        --exclude='.git' \
        dashboard/src/Controller/ "$TARGET/controllers/"
    for f in dashboard/*.php; do
      [ -f "$f" ] && rsync -av --delete --exclude='.git' "$f" "$TARGET/"
    done
    rsync -av --delete \
        --exclude='.git' \
        dashboard/config/         "$TARGET/config/"
    for f in dashboard/docs/*; do
      [ -e "$f" ] && rsync -av --delete --exclude='.git' dashboard/docs/ "$TARGET/docs/"
      break
    done

    # App code
    rsync -av --delete \
        --exclude='.git' \
        php/src/                  "$TARGET/src/"
    rsync -av --delete \
        --exclude='.git' \
        php/config/               "$TARGET/config/"
    rsync -av --delete \
        --exclude='.git' \
        python/src/               "$TARGET/python/src/"
    rsync -av --delete \
        --exclude='.git' \
        scripts/                  "$TARGET/scripts/"
    rsync -av --delete \
        --exclude='.git' \
        tests/                    "$TARGET/tests/"
    rsync -av --delete \
        --exclude='.git' \
        external/                 "$TARGET/external/"
    rsync -av --delete \
        --exclude='.git' \
        config.yaml               "$TARGET/config.yaml"

    # Protect private/code directories on shared hosting
    cat > "$TARGET/.htaccess" <<'HTACESS'
# Deny direct HTTP access to application source code
<Directory "src">
    Require all denied
</Directory>
<Directory "vendor">
    Require all denied
</Directory>
<Directory "tests">
    Require all denied
</Directory>
<Directory "external">
    Require all denied
</Directory>
<Directory "scripts">
    Require all denied
</Directory>
<Directory "python">
    Require all denied
</Directory>
<Directory "controllers">
    Require all denied
</Directory>
<Directory "docs">
    Require all denied
</Directory>

# Block sensitive file types (credentials, configs, schema dumps)
<FilesMatch "\.(yaml|yml|sql|env|log)$">
    Require all denied
</FilesMatch>
HTACESS

    echo ""
    echo "=== Post-deploy ==="
    echo "  Private directories protected with $TARGET/.htaccess"
    echo "  On WHC: run 'composer install --no-dev' if vendor/ is missing"
    ;;

  *)
    echo "Usage: $0 [vps|shared] [args...]"
    echo ""
    echo "  VPS (default):"
    echo "    $0 vps                                  # Deploy to root@192.168.1.102"
    echo "    $0 vps user@host /path/to/webroot"
    echo ""
    echo "  Shared hosting (WHC, cPanel, etc.):"
    echo "    $0 shared /home/you/public_html/stockmarket"
    exit 1
    ;;
esac
