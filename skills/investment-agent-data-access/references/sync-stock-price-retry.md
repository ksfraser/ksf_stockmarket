# Syncing stock prices to SQLite: transient lock retry

`sync_stock_prices.py --sqlite` writes to `price_intraday` in
`ANALYTICS_DB` = `~/.hermes/cache/analysis_results.db` (WAL mode,
`busy_timeout=5000`). Under concurrent access the write can still fail
with `sqlite3.OperationalError: database is locked`.

## Observed failure + recovery (2026-09-23)

**First invocation:**
```
2026-09-23 08:00:58,380 [INFO] Fetching active watchlist symbols...
2026-09-23 08:00:59,281 [INFO] Syncing prices for 16 symbols: CEF, CM.TO, ...
Traceback (most recent call last):
  ...
  File ".../sqlite_price_repository.py", line 146, in save_all
    conn.execute(
sqlite3.OperationalError: database is locked
```

**Diagnostics run:**
- `fuser /var/www/stockmarket-app/*.sqlite` → no process holding any sqlite file
- `ls /var/www/stockmarket-app/*.sqlite` → no sqlite files found there
- `sqlite3 ~/.hermes/cache/analysis_results.db "PRAGMA journal_mode"` → `wal`
- `sqlite3 ~/.hermes/cache/analysis_results.db "PRAGMA busy_timeout"` → `0`
  (the busy_timeout is only set **per-connection** by `DataSource`, so a
   standalone `sqlite3` CLI probe sees the default 0 — not evidence the
   running connection has no timeout)

**Second invocation (retry once):** exit 0, **16 symbols, 64 rows upserted**.
No resolution errors. No MariaDB writes (only the read-only watchlist SELECT).

## Response ladder

1. **Retry the exact same command once.** A single `database is locked` under
   WAL is frequently transient — another connection held a write lock for a
   few milliseconds and released it. Re-running immediately usually succeeds.
   **Do not interpret a single lock error as a schema problem, a wrong-DB
   problem, or a yfinance failure.**
2. If it fails **twice**, check `fuser` on `ANALYTICS_DB` and look for
   competing cron jobs (e.g. `detection_triggers.py --sqlite` touching
   `alert_queue` in the same DB file).
3. If it still fails, escalate: raise `busy_timeout` in `DataSource`, or
   serialize the two crons so they never touch the same DB concurrently.

## Why `fuser` can show nothing

`fuser` only shows processes that currently hold an open **file descriptor**.
A process that opened the DB, did its work, and closed the connection
between your `fuser` call and the failed write will not show up. A file-level
`fuser` on the `.sqlite` files is also the wrong path — `ANALYTICS_DB` lives
under `~/.hermes/cache/`, not `/var/www/stockmarket-app/`. Always check the
real DB path (`config.paths.ANALYTICS_DB`), not wherever `APP_ROOT` points.

## Verification after retry

Query `price_intraday` in `ANALYTICS_DB` directly — never guess from
`APP_ROOT` or workspace `*.db` decoys:

```bash
python3 -c "
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from config.paths import ANALYTICS_DB
db = sqlite3.connect(str(ANALYTICS_DB))
for r in db.execute(
    \"SELECT symbol, MAX(price_date), COUNT(*) FROM price_intraday \"
    \"WHERE symbol IN ('CEF','CM.TO','CNR.TO','GLD','MICC','MX.TO','QQQ',\"
    \"'RGLD','RUS.TO','RY.TO','SPY','VUN.TO','WJX.TO','XIC.TO','XIU.TO','ZAG.TO')\"
    \" GROUP BY symbol ORDER BY symbol\").fetchall():
    print(f'{r[0]:12} max={r[1]} rows={r[2]}')
db.close()
"
```

Expected: all 16 symbols present with `max` = today (or most recent trading
day) and `rows` ≈ 4 (5d window on a weekday).

## Do NOT

- Do NOT assume `database is locked` means the DB file is corrupt or the wrong
  file. It means contention — retry first.
- Do NOT spend several re-runs chasing a "stale yfinance fetch" until you have
  confirmed the retry succeeds and the rows are fresh. (This exact waste
  happened 2026-08-21 for a different reason — wrong-DB decoy — but the
  principle holds: confirm the store is fresh before investigating fetch staleness.)
- Do NOT `rm` or `VACUUM` the DB file in response to a lock error.
