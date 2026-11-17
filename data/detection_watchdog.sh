#!/bin/bash
# Watchdog: wait for the detection_triggers.py --sqlite background process,
# then dump a final SQLite alert-type aggregate + error tally to a file.
DET_PID=270256
LOG=/root/Documents/stockmarket/php/stockmarket-app/data/detection_run_sqlite_cron_20261021.log
OUT=/root/Documents/stockmarket/php/stockmarket-app/data/detection_alert_aggregate_20261021.txt

while kill -0 "$DET_PID" 2>/dev/null; do
  sleep 30
done

{
  echo "=== detection_triggers.py --sqlite AGGREGATE ==="
  echo "finished_at: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "python_elapsed_training: $(ps -o etime= -p $DET_PID 2>/dev/null)"
  echo "=== alert_queue by alert_type ==="
  python3 -c "
import sqlite3
conn = sqlite3.connect('/root/Documents/stockmarket/php/stockmarket-app/data/analysis_results.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT alert_type, COUNT(*) c, COUNT(DISTINCT symbol) s, MIN(created_at) mn, MAX(created_at) mx FROM alert_queue GROUP BY alert_type ORDER BY c DESC')
for r in cur.fetchall():
    print('  %s: count=%d symbols=%d first=%s last=%s' % (r['alert_type'], r['c'], r['s'], r['mn'], r['mx']))
cur.execute('SELECT COUNT(*) c, COUNT(DISTINCT symbol) s FROM alert_queue')
print('  TOTAL: count=%d distinct_symbols=%d' % tuple(cur.fetchone()))
"
  echo "=== error tally (HTTP 404 from yfinance) ==="
  python3 -c "
import re
text = open('$LOG').read()
lines = [l for l in text.splitlines() if '404' in l]
from collections import Counter
c = Counter()
for l in lines:
    m = re.search(r'Quote not found for symbol: (\S+)', l)
    if m:
        c[m.group(1)] += 1
for sym, n in sorted(c.items()):
    print('  %s: %d' % (sym, n))
print('  TOTAL 404 lines: %d' % len(lines))
"
  echo "=== final stdout tail of detection run (buffered) ==="
  tail -20 "$LOG"
  echo "=== ALL DONE ==="
} > "$OUT"

cat "$OUT"
