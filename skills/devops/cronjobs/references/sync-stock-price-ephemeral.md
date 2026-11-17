# Ephemeral SQLite price sync (`sync_stock_prices.py --sqlite`)

Verified working invocation (2026-09-25):

```
cd /root/.hermes/workspace/investment-agent
APP_ROOT=/var/www/stockmarket-app \
PYTHONPATH=/home/ksf_stockmarket/ksf_stockmarket/python/src:/root/.hermes/workspace/investment-agent:/root/.hermes/workspace/investment-agent/src \
/usr/bin/python3.10 sync_stock_prices.py --sqlite
```

## Key facts

- `--sqlite` = SQLite-only writes (`price_intraday` table) into `ANALYTICS_DB`
  (`~/.hermes/cache/analysis_results.db`). NO MariaDB writes occur.
- The script DOES still read `watchlist_symbols` from MariaDB (read-only SELECT)
  to get the active symbol list.
- `PYTHONPATH` must include BOTH `/home/ksf_stockmarket/ksf_stockmarket/python/src`
  (for `config` package) and `/root/.hermes/workspace/investment-agent/src`
  (for the workspace `src/` layer, including `dto` package at `repo/src/dto`).
  The workspace `config/` package shadows `python/src/config` and hardcodes
  `CACHE_DIR = Path.home() / '.hermes' / 'cache'`, so `ANALYTICS_DB` resolves
  to `~/.hermes/cache/analysis_results.db` regardless of `APP_ROOT`.
- The workspace contains multiple 0-byte decoy `.db` files (`price_intraday.db`,
  `analysis_results.db`, etc.). Verify persistence by importing `ANALYTICS_DB`
  from `config.paths`, not by inspecting workspace filenames.
- A stale non-empty DB exists at `/var/www/stockmarket-app/data/analysis_results.db`
  (ksf_stockmarket app's SQLite, not the ephemeral store). It holds old
  `price_intraday` rows from July 2026. Do NOT verify against this file.

## Verification recipe

```python
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from config.paths import ANALYTICS_DB
print('DB path:', ANALYTICS_DB)
```

Query the store directly:
```sql
SELECT symbol, COUNT(*) FROM price_intraday GROUP BY symbol;
SELECT COUNT(DISTINCT symbol) FROM price_intraday;
```

## Session result (2026-09-25)

- 16 active symbols fetched from `watchlist_symbols`
- 75 rows upserted (5-day daily interval × 16 symbols ≈ 75 bars)
- Exit code 0, 0 resolution errors reported
- No MariaDB writes (confirmed by `--sqlite` flag + SQLite repository path)
