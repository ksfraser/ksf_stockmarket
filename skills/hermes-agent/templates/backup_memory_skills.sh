#!/bin/bash
# backup_memory_skills.sh — commit & push Hermes memory + skills to GitHub.
# Safe config (scripts/, SOUL.md) is included too. Secrets/state are excluded
# by ~/.hermes/.gitignore. Run manually, or schedule via Hermes cron.
#
# Repo: https://github.com/ksfraser/hermes-backup  (private)
set -euo pipefail
cd /root/.hermes

# Stage ONLY the tracked-safe paths. NEVER `git add -A` here — real secrets
# (.env, auth.json, config.yaml, state.db) live in this directory.
git add .gitignore memories/ skills/ SOUL.md scripts/ 2>/dev/null

if git diff --cached --quiet; then
  echo "backup: no changes to memory/skills since last push"
  exit 0
fi

TS=$(date '+%Y-%m-%d %H:%M:%S')
git commit -q -m "Auto-backup memory+skills: $TS

Co-Authored-By: Hermes Agent <noreply@nousresearch.com>"
git push origin HEAD
echo "backup: pushed at $TS -> $(git remote get-url origin)"
