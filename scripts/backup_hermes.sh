#!/usr/bin/env bash
# backup_hermes.sh — Targeted backup of Hermes config/skills/cron/memories
# Excludes runtime state, caches, logs, sessions, secrets bloat
set -euo pipefail

BACKUP_DIR="${1:-/root/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/hermes_backup_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$BACKUP_FILE" \
  --exclude='state.db' \
  --exclude='state-snapshots' \
  --exclude='checkpoints' \
  --exclude='cache' \
  --exclude='logs' \
  --exclude='sessions' \
  --exclude='bin' \
  --exclude='image_cache' \
  --exclude='audio_cache' \
  --exclude='whatsapp' \
  --exclude='tradingview-mcp' \
  --exclude='lsp' \
  --exclude='workspace' \
  --exclude='*.db' \
  --exclude='*.db-*' \
  --exclude='*.log' \
  --exclude='*.pid' \
  --exclude='*.lock' \
  -C /root .hermes/config.yaml \
       .hermes/skills \
       .hermes/cron \
       .hermes/profiles \
       .hermes/memories \
       .hermes/scripts \
       .hermes/mcp.json \
       .hermes/.env 2>/dev/null || true

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup complete: $BACKUP_FILE ($SIZE)"

# Optional: keep last 7 backups
ls -1t "$BACKUP_DIR"/hermes_backup_*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
echo "Retention: keeping latest 7 backups"
