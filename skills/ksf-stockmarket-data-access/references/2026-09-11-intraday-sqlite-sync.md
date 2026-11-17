# 2026-09-11 Intraday SQLite Sync Run

## Command

```bash
cd /root/.hermes/workspace/investment-agent
APP_ROOT=/var/www/stockmarket-app \
  PYTHONPATH=/home/ksf_stockmarket/ksf_stockmarket/python/src:. \
  /usr/bin/python3.10 sync_stock_prices.py --sqlite
```

## Stdout

```
2026-09-11 08:45:45,190 [INFO] Fetching active watchlist symbols...
2026-09-11 08:45:46,132 [INFO] Syncing prices for 16 symbols: CEF, CM.TO, CNR.TO, GLD, MICC, MX.TO, QQQ, RGLD, RUS.TO, RY.TO, SPY, VUN.TO, WJX.TO, XIC.TO, XIU.TO, ZAG.TO
2026-09-11 08:45:47,568 [INFO] Upserted 80 rows into price_intraday (SQLite).
```

- Symbol count: **16**
- Resolution errors: **0** (no WARNING/ERROR lines)
- Rows upserted: **80** (5 bars × 16 symbols)

## SQLite readback (post-run)

Target: `/root/.hermes/cache/analysis_results.db` → `price_intraday`.
Table already existed with 185,311 rows across 49 symbols before this run.

Per-symbol snapshot for the 16 synced symbols after this run:

| Symbol   | Last price_date | Rows |
|----------|-----------------|------|
| CEF      | 2026-09-11      | 1275 |
| CM.TO    | 2026-09-11      | 1275 |
| CNR.TO   | 2026-09-11      | 2216 |
| GLD      | 2026-09-11      | 1275 |
| MICC     | 2026-09-11      | 191  |
| MX.TO    | 2026-09-11      | 3898 |
| QQQ      | 2026-09-11      | 1275 |
| RGLD     | 2026-09-11      | 1275 |
| RUS.TO   | 2026-09-11      | 1275 |
| RY.TO    | 2026-09-11      | 1275 |
| SPY      | 2026-09-11      | 1275 |
| VUN.TO   | 2026-09-11      | 1275 |
| WJX.TO   | 2026-09-11      | 1275 |
| XIC.TO   | 2026-09-11      | 1275 |
| XIU.TO   | 2026-09-11      | 1275 |
| ZAG.TO   | 2026-09-11      | 1275 |

All 16 symbols show `2026-09-11` as latest — confirming fresh data landed.

## Notes

- `APP_ROOT` and `PYTHONPATH` are set as env vars in the command line; they are
  not sourced from a file. `PYTHONPATH` adds both the repo `src/` and the
  workspace `src/` to the import path.
- `python3.10` is used (not `python3`/`python3.11`) per the existing cron
  invocation pattern.
- The workspace-level `price_intraday.db` is a zero-byte decoy — never written
  to. The real target is `~/.hermes/cache/analysis_results.db`.
