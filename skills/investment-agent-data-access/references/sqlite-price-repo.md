# SQLite price repository — write path, decoy trap, verification

`sync_stock_prices.py --sqlite` (and any entrypoint that passes `sqlite_mode=True`
to `get_repository()`) writes to the SQLite `price_intraday` table. This page
records where it actually lands, why the workspace `price_intraday.db` is a
decoy, and how to verify a run correctly.

## Where writes land

`src/db/__init__.py:get_repository()` branches on `sqlite_mode`:

```python
if sqlite_mode:
    from config.paths import ANALYTICS_DB
    return SQLitePriceRepository(db_path=str(ANALYTICS_DB))
```

`config.paths.ANALYTICS_DB` = `~/.hermes/cache/analysis_results.db`
(`CACHE_DIR / 'analysis_results.db'`, `CACHE_DIR = Path.home() / '.hermes' / 'cache'`).

So **every** `--sqlite` price write lands in
`/root/.hermes/cache/analysis_results.db`, inside its `price_intraday` table —
NOT in any `*.db` file that sits in the workspace root.

The workspace `sync_stock_prices.py` itself does `sys.path.insert(0, .../src)` so
that `from src.db...` resolves, but the DB path comes from `config.paths`, not
from the script's CWD or from `APP_ROOT`.

## The `price_intraday.db` decoy (workspace root)

`/root/.hermes/workspace/investment-agent/price_intraday.db` is a **0-byte empty
file** (dated before the sync run). It has no tables. A naive verification like

```bash
sqlite3 price_intraday.db "SELECT COUNT(*) FROM price_intraday"
```

fails with `no such table: price_intraday` and makes it look like nothing was
written. It is one of several empty decoy DBs in the workspace (`investment.db`,
`cron_jobs.db`, `alerts.db`, `alerts_ephemeral.db`, `alert_queue.sqlite`, …).

Do not touch any workspace-root `*.db` for verification. Import `ANALYTICS_DB`.

## Why `APP_ROOT` does not move the SQLite target

The cron command passes `APP_ROOT=/var/www/stockmarket-app`. A natural guess is
that the SQLite file therefore lives under `/var/www/stockmarket-app/...`. It
does not, for two reasons:

1. The effective `config` package is the workspace `config/` (a regular package
   with `__init__.py`), which **shadows** `python/src/config` (a namespace
   portion). The imported `config.paths` is the workspace one.
2. Workspace `config/paths.py` hardcodes
   `CACHE_DIR = Path.home() / '.hermes' / 'cache'`, so
   `ANALYTICS_DB = ~/.hermes/cache/analysis_results.db` regardless of `APP_ROOT`.

`/var/www/stockmarket-app/data/analysis_results.db` is a **second, non-empty
decoy** — it belongs to the ksf_stockmarket web app (different project), has real
tables and a populated `price_intraday` with stale rows (latest ≈ 2026-07-16).
Checking it after a fresh sync makes it look like the fetcher returned stale
data. Do not query it for `--sqlite` verification.

## Verification recipe (run from the workspace root)

```python
import sqlite3, sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from config.paths import ANALYTICS_DB   # == ~/.hermes/cache/analysis_results.db

con = sqlite3.connect(str(ANALYTICS_DB))
con.row_factory = sqlite3.Row
cur = con.cursor()

# 1) confirm the table exists and get total size
cur.execute("SELECT COUNT(*) FROM price_intraday")
print("total rows:", cur.fetchone()[0])

# 2) per-symbol latest + counts for the watchlist symbols you just synced
cur.execute(
    "SELECT symbol, MAX(price_date), COUNT(*)"
    " FROM price_intraday"
    " WHERE symbol IN (:syms)"
    " GROUP BY symbol ORDER BY symbol",
    {"syms": [":".join(["CEF","CM.TO","CNR.TO","GLD","MICC","MX.TO",
                         "QQQ","RGLD","RUS.TO","RY.TO","SPY","VUN.TO",
                         "WJX.TO","XIC.TO","XIU.TO","ZAG.TO"])]},
)
# (build the IN list properly with placeholders in real code)
```

For a working placeholder-IN version see the inline probe in the cron output or
`references/sync-price-db-verify.md`.

## What "good" looks like after a sync

- `ANALYTICS_DB` = `/root/.hermes/cache/analysis_results.db`.
- All 16 watchlist symbols show `MAX(price_date)` = today (or most recent trading
  day).
- Total `price_intraday` row count went up by ≈ 80 (16 symbols × 5 daily bars
  from `period=5d`); WJX.TO occasionally drops a bar → 79.
- The workspace `price_intraday.db` is still 0 bytes — that is expected.

## `save_all` persistence

`SQLitePriceRepository.save_all()` iterates inside `with self._conn() as conn:`,
and the `sqlite3.Connection` context manager commits on clean exit (rolls back on
exception). So rows are durable when `save_all()` returns. There is no separate
explicit `conn.commit()` in the method — the context manager is the commit point.
The earlier suspicion that data was "not yet visible" was a wrong-DB verification
issue, not a transaction-isolation issue.
