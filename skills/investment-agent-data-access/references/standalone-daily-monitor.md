# Running `daily_monitor_standalone.py` end-to-end

Canonical command (run from repo root `/root/.hermes/workspace/investment-agent`):

```bash
cd /root/.hermes/workspace/investment-agent && python3 daily_monitor_standalone.py --output /tmp/daily_report.txt 2>&1
```

The script is "standalone" (no LLM, no skill layer) but it still depends on the
shared `src/` data layer, so it has THREE import/path traps that break it on a
fresh checkout / cron tick. All three were hit and fixed on 2026-08-20.

## Trap 1 — `analysis_db` relative import under flat loading

**Symptom**
```
Traceback (most recent call last):
  File ".../daily_monitor_standalone.py", line 32, in <module>
    from analysis_db import get_db
  File ".../src/db/analysis_db.py", line 31, in <module>
    from .connection import DataSource
ImportError: attempted relative import with no known parent package
```
**Cause** — `analysis_db.py` is imported as a FLAT top-level module (the script
adds `src/db` to `sys.path` and does `from analysis_db import get_db`). ~44
call sites in the repo do the same. A relative import (`.connection`) only
resolves when the module is loaded as part of the `db` package.
**Fix** (in `src/db/analysis_db.py`):
```diff
-from .connection import DataSource
+from connection import DataSource
```
Flat `connection` resolves because `src/db` is on `sys.path`. This works whether
the module is imported flat OR as `db.analysis_db`. Only convert the SPECIFIC
relative imports that are hit by flat loading; package-internal modules that are
only ever imported as `db.*` keep their relative imports.

## Trap 2 — repo root missing from `sys.path` (`config` not importable)

**Symptom** (after fixing Trap 1):
```
ModuleNotFoundError: No module named 'config'
```
raised from `src/db/connection.py` (`from config.db import get_mariadb_config`).
**Cause** — `config/` lives at the REPO ROOT (`/root/.hermes/workspace/investment-agent/config/db.py`),
NOT under `src`. The script only inserted `src` and `src/<pkg>` subdirs.
**Fix** (in `daily_monitor_standalone.py`, path setup):
```diff
 SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
+# Project root must be on the path so `config` (config/db.py) is importable,
+# since src/db/connection.py does `from config.db import get_mariadb_config`.
+sys.path.insert(0, SCRIPT_DIR)
 for p in ['src', 'src/indicators', 'src/delivery', 'src/analysis', 'src/db', 'src/optimization']:
     sys.path.insert(0, os.path.join(SCRIPT_DIR, p))
```

## Trap 3 — `fetch_daily` doesn't accept `interval`

**Symptom** (after Traps 1+2; every ticker errors):
```
⚠️  RY: YFinanceFetcher.fetch_daily() got an unexpected keyword argument 'interval'
... (all 17 active tickers)
```
**Cause** — `src/db/price_fetcher.py`:
```python
def fetch_ohlcv_dataframe(self, symbol, period="5d", interval="1d"):
    dtos = self.fetch_daily([symbol], lookback_days=5, period=period, interval=interval)  # interval NOT accepted
```
`YFinanceFetcher.fetch_daily` signature was
`(self, symbols, lookback_days=5, start=None, end=None, period=None)` — no `interval`.
**Fix** (in `src/db/price_fetcher.py`) — accept and honor an optional `interval`:
```diff
 def fetch_daily(
     self,
     symbols,
     lookback_days=5,
     start=None,
     end=None,
     period=None,
+    interval: Optional[str] = None,
 ):
     ...
-    kwargs = dict(interval=self.interval, auto_adjust=False, progress=False, threads=True)
+    kwargs = dict(interval=interval or self.interval, auto_adjust=False, progress=False, threads=True)
```
Also widen the abstract method for consistency:
```diff
-    def fetch_daily(self, symbols, lookback_days=5) -> List[StockPriceDTO]:
+    def fetch_daily(self, symbols, lookback_days=5,
+                    interval: Optional[str] = None) -> List[StockPriceDTO]:
```

## Post-fix result

Script exits 0, `/tmp/daily_report.txt` contains real signals. 17/18 holdings
analyzed; the remaining one (`MTY`) failed only because yfinance returned
"possibly delisted; no price data found" (a data-source fetch failure, NOT a code
bug) and `CDZ` is correctly flagged delisted in the DB.

## Other notes
- The façade chain is `get_ohlcv(symbol, period, interval="1d")` →
  `YFinanceMarketData.get_price_history` → `YFinanceFetcher.fetch_ohlcv_dataframe`
  → `fetch_daily`. All rely on Trap-3's `interval` plumbing.
- `fetch_daily` still IGNORES the constructor's `self.period` (pass `period=` per call);
  it now ALSO accepts `interval=` per call (overrides `self.interval`, default "1d").
- Commit the three fixes with the repo's normal flow (stage the changed files by
  name, run the guard `--staged`, commit, push) — see the SKILL.md delivery rules.
