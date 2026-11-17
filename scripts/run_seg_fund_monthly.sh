#!/usr/bin/env bash
# Monthly seg-fund pipeline (runs on the 15th).
# Refreshes the LIVE-API carriers' data, snapshots performance_history, and
# recomputes the analytics (calc_pipeline.py -> seg_fund_metrics).
#
# NOTE: BMO / Canada Life / Empire Life / Equitable are seeded from prod
# metadata and are intentionally EXCLUDED here -- re-running their seeders
# could re-introduce the decimal-unit corruption that was normalised in place.
# Their refresh is manual until a verified headless seeder exists.
set -u
REPO=/home/ksf_stockmarket/ksf_stockmarket
LOG=/tmp/segfund_monthly.log
cd "$REPO" || exit 1
echo "[$(date -u +%FT%TZ)] monthly seg-fund run start" | tee -a "$LOG"

# --- helper: download/create JSON input files ---
# Sun Life: parse embedded JSON from SPA (only working source verified)
if [ ! -f /tmp/sunlife_profiles.json ]; then
  echo "downloading Sun Life data..." | tee -a "$LOG"
  curl -s -A "Mozilla/5.0" "https://funds.sunlifeglobalinvestments.com/seg-funds-list" -o /tmp/sunlife.html 2>>"$LOG" || echo "Sun Life download failed" | tee -a "$LOG"
  python3 - <<'PY' 2>>"$LOG"
import json, sys
html = open('/tmp/sunlife.html', encoding='utf-8', errors='ignore').read()
i = html.find("__PRELOADED_STATES__['root'] = ")
if i == -1:
    print("Sun Life embedded JSON not found")
    sys.exit(1)
s = html.index('{', i)
try:
    obj, _ = json.JSONDecoder().raw_decode(html, s)
    json.dump(obj.get('data', {}).get('webProfiles', []), open('/tmp/sunlife_profiles.json', 'w'))
    print("Sun Life JSON written to /tmp/sunlife_profiles.json")
except Exception as e:
    print(f"Sun Life parse error: {e}")
PY
fi

# RBC Calendar Year: POST List/GetResult (known to fail due to auth/session)
# Keep existing /tmp/rbc_calyear.json if present (currently invalid HTML)
# We'll pass the file (it may be empty/invalid) but the script will skip if missing.

# RBC Long Term, Manulife, iA: data sources blocked or unclear; create empty placeholder to prevent file-not-found.
for f in /tmp/rbc_longterm.json /tmp/manu_all.json /tmp/ia_yield_savings.json; do
  if [ ! -f "$f" ]; then
    touch "$f"
    echo "created empty placeholder $f" | tee -a "$LOG"
  fi
done

# --- run seeders with explicit file paths ---
for s in seed_rbc_local seed_rbc_trailing seed_sunlife_local seed_manulife_local seed_ia_local; do
  echo "-- $s" | tee -a "$LOG"
  # pass the expected JSON file path as argument
  case $s in
    seed_rbc_local)   src="/tmp/rbc_calyear.json" ;;
    seed_rbc_trailing) src="/tmp/rbc_longterm.json" ;;
    seed_sunlife_local) src="/tmp/sunlife_profiles.json" ;;
    seed_manulife_local) src="/tmp/manu_all.json" ;;
    seed_ia_local) src="/tmp/ia_yield_savings.json" ;;
    *) echo "unknown seeder $s" | tee -a "$LOG"; continue ;;
  esac
  python3 "scripts/$s.py" "$src" >> "$LOG" 2>&1 || echo "  WARN: $s failed" | tee -a "$LOG"
done
python3 scripts/snapshot_perf_history.py >> "$LOG" 2>&1 || true
python3 scripts/calc_pipeline.py >> "$LOG" 2>&1 || true
echo "[$(date -u +%FT%TZ)] monthly seg-fund run done" | tee -a "$LOG"
