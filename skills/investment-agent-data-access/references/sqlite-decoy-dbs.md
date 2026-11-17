# SQLite Decoy DBs in the investment-agent workspace

Several SQLite files live in `/root/.hermes/workspace/investment-agent/` and look like targets
but are **never written to** by `--sqlite` detection or sync runs. Querying them returns empty
results and misleads you into thinking a run failed.

## The one live store

| Concern | Real path | Table |
|---------|-----------|-------|
| Intraday prices + alerts (ephemeral) | `~/.hermes/cache/analysis_results.db` | `price_intraday`, `alert_queue`, `alert_responses` |

The real path is `config.paths.ANALYTICS_DB` → `Path.home() / '.hermes' / 'cache' / 'analysis_results.db'`.
Import it; do not guess from filenames or `APP_ROOT`.

```
from config.paths import ANALYTICS_DB
print(ANALYTICS_DB)  # ~/.hermes/cache/analysis_results.db
```

## Decoy files (all empty — never written to)

| File | Size | Why it exists |
|------|------|---------------|
| `price_intraday.db` | 0 bytes | Looks like the price target; is a leftover/decoy. |
| `detection_alerts.db` | 0 bytes | Looks like the detection target; is a leftover/decoy. |
| `intraday_alerts.db` | 0 bytes | Decoy. |
| `alerts_intraday.db` | 0 bytes | Decoy. |
| `alerts_ephemeral.db` | 0 bytes | Decoy. |
| `alerts.db` | 0 bytes | Decoy. |
| `investment.db` | 0 bytes | Decoy. |
| `cron_jobs.db` | 0 bytes | Decoy. |
| `cron_queue.db` | 0 bytes | Decoy. |

A naive `sqlite3 <any-of-the-above> ".tables"` returns nothing (or `no such table`); that is
expected, not a sign that the run failed.

## Non-empty look-alike that is ALSO the wrong DB

`/var/www/stockmarket-app/data/analysis_results.db` is the **ksf_stockmarket web app's** SQLite.
It has real tables and stale 2026-07-16 price data. Because the cron command sets
`APP_ROOT=/var/www/stockmarket-app`, it is natural to check there — but
`config.paths.ANALYTICS_DB` hardcodes `~/.hermes/cache/`, so `APP_ROOT` is ignored for the SQLite
path. Querying this file gives you stale data and sends you chasing phantom "stale fetch" bugs.

## Verification recipe

Always confirm the DB path and query it directly:

```bash
python3 -c "
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from config.paths import ANALYTICS_DB
print('DB:', ANALYTICS_DB)
con = sqlite3.connect(ANALYTICS_DB)
cur = con.cursor()
for r in cur.execute('SELECT alert_type, COUNT(*) FROM alert_queue GROUP BY alert_type').fetchall():
    print(r)
con.close()
"
```

For price-sync verification, query `price_intraday` in the same DB; for detection verification,
query `alert_queue`.

## See also

- `sync-price-db-verify.md` — price-sync verification recipe and the `/var/www/...` stale-data trap.
- `detection-triggers.md` — detection-specific gotchas (stdout count ≠ store count, dedup miscount, volume_spike written-but-absent anomaly).
