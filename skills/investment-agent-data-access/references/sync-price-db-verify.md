# Verifying an intraday price sync (--sqlite) run

`python3.10 sync_stock_prices.py --sqlite` upserts into `price_intraday`.
It does NOT write to MariaDB (only a read-only `SELECT` of `watchlist_symbols`).

## The trap (2026-08-21)

The cron command includes `APP_ROOT=/var/www/stockmarket-app`. Do NOT conclude the
SQLite store is `/var/www/stockmarket-app/data/analysis_results.db`. That file is a
**decoy**: it belongs to the ksf_stockmarket web app (a different project), it has
REAL tables + a populated `price_intraday` (historical RY.TO/SPY series, rows dated
up to 2026-07-16), and a name/path shape identical to `ANALYTICS_DB`. Checking it
after a sync shows stale data and falsely implies the fetch returned stale prices.

Root cause: the effective `config` package is the workspace `config/` (regular
package, has `__init__.py`), which SHADOWS `python/src/config` (namespace portion).
Workspace `config/paths.py` hardcodes `CACHE_DIR = Path.home()/'.hermes'/'cache'`,
so `ANALYTICS_DB` ignores `APP_ROOT`. Always import the resolved constant instead of
guessing a filename or trusting `APP_ROOT`.

## Correct verification (run from /root/.hermes/workspace/investment-agent)

```python
import sqlite3, sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from config.paths import ANALYTICS_DB          # == ~/.hermes/cache/analysis_results.db
from config.db import get_mariadb_config
import pymysql
MYSQL = get_mariadb_config()
con = pymysql.connect(**MYSQL); cur = con.cursor(pymysql.cursors.DictCursor)
cur.execute("SELECT symbol FROM watchlist_symbols WHERE is_active=1")
syms = [r['symbol'] for r in cur.fetchall()]; con.close()

c = sqlite3.connect(str(ANALYTICS_DB))
ph = ','.join('?'*len(syms))
rows = c.execute(
    f"SELECT symbol, MAX(price_date), COUNT(*) FROM price_intraday "
    f"WHERE symbol IN ({ph}) GROUP BY symbol ORDER BY symbol", syms).fetchall()
stale = [(s,m) for s,m in rows if str(m) < '2026-08-17']   # adjust the date floor
print("DB:", ANALYTICS_DB)
for s,m,n in rows: print(f"  {s:12} max={m} rows={n}")
print("any stale?:", stale or "NONE")
# rows owned by the latest 5d window (expect ~ len(syms)*5)
w = c.execute(
    f"SELECT COUNT(*) FROM price_intraday WHERE symbol IN ({ph}) "
    f"AND price_date >= date('now','-5 days')", syms).fetchone()[0]
print("rows in last 5d window:", w)
c.close()
```

## What "good" looks like

- `DB` printed is `/root/.hermes/cache/analysis_results.db`.
- All 16 watchlist symbols show `max` = today (or the most recent trading day) → `any stale?` = `NONE`.
- `rows in last 5d window` ≈ `16 * 5` (= 80; WJX.TO occasionally drops a bar → 79).

## If you see stale 2026-07-16 data

You almost certainly queried the wrong DB (`/var/www/stockmarket-app/data/...` or a
repo-root `*.db`). Re-run the snippet above and confirm `DB` is `~/.hermes/cache/...`.
Do NOT go hunting for a yfinance-staleness bug until you have confirmed you are
reading `ANALYTICS_DB` — the real store is fresh; the decoy is not.
