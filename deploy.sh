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
    HOST="${1:-192.168.1.102}"
    shift || true
    WEBROOT="${1:-/var/www/html/stockmarket}"
    APPROOT="${1:-/var/www/stockmarket-app}"
    shift || true

    # Detect localhost — if HOST points at this box, skip SSH prefixes
    # so rsync runs locally without going through localhost loopback.
    # Added 192.168.1.102 because this dev box has that address on the LAN.
    if [[ "$HOST" =~ ^(localhost|127\.0\.0\.1|::1|192\.168\.1\.102)$ ]]; then
        RSYNC_DEST=""
        REMOTE_CMD="sh -c"
    else
        RSYNC_DEST="$HOST:"
        REMOTE_CMD="ssh $HOST"
    fi

    echo "Deploying to VPS: $HOST"
    echo "  Webroot:    $WEBROOT"
    echo "  App root:   $APPROOT"

    # 1) Public files → webroot
    rsync -av --delete \
        public_html/ "${RSYNC_DEST}${WEBROOT}/"

    # 2) Templates from all sources → app root
    rsync -av php/templates/                "${RSYNC_DEST}${APPROOT}/templates/"
    rsync -av php/templates/partials/detail/ "${RSYNC_DEST}${APPROOT}/templates/partials/detail/"
    rsync -av python/*.php                  "${RSYNC_DEST}${APPROOT}/"
    rsync -av dashboard/templates/          "${RSYNC_DEST}${APPROOT}/dashboard/templates/"
    rsync -av dashboard/src/Controller/     "${RSYNC_DEST}${APPROOT}/controllers/"
    rsync -av dashboard/config/             "${RSYNC_DEST}${APPROOT}/config/"
    for f in dashboard/*.php; do
      [ -f "$f" ] && rsync -av "$f" "${RSYNC_DEST}${APPROOT}/"
    done

    # 3) PHP app code
    rsync -av php/src/                      "${RSYNC_DEST}${APPROOT}/src/"
    rsync -av php/config/                   "${RSYNC_DEST}${APPROOT}/config/"
    rsync -av config.yaml                   "${RSYNC_DEST}${APPROOT}/config.yaml"

    # Ensure Apache can read all template/app utility files post-rsync
    $REMOTE_CMD "chown -R apache:apache $APPROOT/templates/partials/detail && chmod 644 $APPROOT/templates/partials/detail/*.php && chown -R apache:apache $APPROOT/src/Util && chmod -R u+rwX $APPROOT/src/Util && chown -R apache:apache $APPROOT/python && chmod 755 $APPROOT/python/*.py && mkdir -p $APPROOT/results && chown apache:apache $APPROOT/results && chmod 755 $APPROOT/results"

    # 4) Python backend
    rsync -av python/src/                   "${RSYNC_DEST}${APPROOT}/python/src/"
    rsync -av python/*.py                   "${RSYNC_DEST}${APPROOT}/python/"

    # 5) Scripts, tests, external
    rsync -av scripts/                      "${RSYNC_DEST}${APPROOT}/scripts/"
    rsync -av tests/                        "${RSYNC_DEST}${APPROOT}/tests/"
    rsync -av external/                     "${RSYNC_DEST}${APPROOT}/external/"

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
