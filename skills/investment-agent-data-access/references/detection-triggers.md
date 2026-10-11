# detection_triggers.py --sqlite (intraday alert detection)

## Canonical cron command
```
cd /root/.hermes/workspace/investment-agent && /usr/bin/python3.10 detection_triggers.py --sqlite
```
Writes alerts to the SQLite `alert_queue` table (ANALYTICS_DB = `~/.hermes/cache/analysis_results.db`).
`--sqlite` ⇒ "no MariaDB alert writes" — but the job STILL reads the monitored-symbol list from
MariaDB `watchlist_symbols` (read-only `pymysql SELECT`) and reads prices from SQLite `price_intraday`.

## Failure transcript (before fix)
Exact command died with:
```
Traceback (most recent call last):
  File ".../detection_triggers.py", line 21, in <module>
    from src.db.price_fetcher import YFinanceFetcher
  File ".../src/db/__init__.py", line 14, in <module>
    from .stock_price_dto import StockPriceDTO
  File ".../src/db/stock_price_dto.py", line 8, in <module>
    from dto.price import StockPriceDTO, to_ohlcv_dataframe
ModuleNotFoundError: No module named 'dto'
```

## Root cause (two-part)
1. **Wrong dir on path.** The top-level `dto` package is at `repo/src/dto`, so `repo/src`
   (not `python/src`) must be importable. The script only inserted `python/src`.
2. **Ordering.** The `sys.path.insert` was at line ~36, AFTER the `from src.db...` import at
   line ~21 that transitively imports `dto`. An insert that runs *after* the import it enables
   is useless — the crash happens before the path is fixed.

## Fix (applied in-session to detection_triggers.py)
Move the path setup ABOVE the `from src.db...` imports:
```python
import pymysql

# repo/src hosts the top-level `dto` package; must be on path BEFORE the
# `from src.db...` imports below (they transitively import `dto`).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'python', 'src'))
from src.db.price_fetcher import YFinanceFetcher
...
```
After the fix the canonical command runs with NO `PYTHONPATH` export. Keep the insert above the
imports whenever the file is edited — moving it below recreates the crash. (Hermes terminal/cron
still blocks `export PYTHONPATH=...`; use inline `PYTHONPATH=... python3 ...` if you ever need it.)

## Verified behavior (run 2026-08-13, ~13:16 MDT = ~17:16 UTC, inside market hours)
- Exit 0; no `Error checking ...` lines.
- SQLite store (`~/.hermes/cache/analysis_results.db`.alert_queue) after run:
  - `oscillator_extremes`: 9 (5 high, 4 medium) — RSI overbought for CEF, GLD, MICC, RGLD,
    RUS.TO, SPY, QQQ, XIC.TO, XIU.TO.
  - `volume_spike`: 0, `natr_spike`: 0, `gap_up`: 0 — genuine (no spike that tick), not an error.
  - All rows `status='pending'`, `created_at='2026-08-13 17:17:17'`.
- Data-source proof (so 0 volume ≠ silent failure): 16 symbols in MariaDB `watchlist_symbols`;
  `price_intraday` returned 10 rows/symbol with real volumes (CEF ≈523k, GLD ≈5.6M, MICC ≈292k).

## Gotcha: stdout count ≠ rows written
`write_alert()` returns `None` on a duplicate open within the 300s dedup window, but each
`run_*_check` does `alerts_written += 1` unconditionally. Re-running within 300s printed
"Oscillator check: 9 alerts written" with `alert_id: None` per line yet inserted 0 new rows
(store stayed at 9). Always verify with:
```sql
SELECT alert_type, severity, COUNT(*) FROM alert_queue GROUP BY alert_type, severity;
```

## Market-hours gate
Outside weekdays 09:30–16:00 ET the job prints "Outside market hours ... skipping detection."
and exits 0 with 0 alerts. That is correct, not a bug.

## ⚠️ Anomaly: volume_spike reported as WRITTEN but ABSENT from the store (run 2026-08-13 ~19:00 UTC)
A later run the same day surfaced a **more severe** variant of the stdout-vs-store gotcha:
- Script stdout: `=== Volume Spike Check ===` → `🔴 XIC.TO: Volume spike 2.43x (alert_id: vol-XIC.TO-20260813130058)` and `Volume check: 1 alerts written to alert_queue`.
- Script stdout totals (exit 0): volume_spike 1, oscillator_extremes 9, natr_spike 0, gap 0 = **10 reported written**.
- Actual store (`~/.hermes/cache/analysis_results.db`.alert_queue) at run end:
  - `oscillator_extremes`: **9** (all persisted, `created_at` 2026-08-13 19:00–19:01 UTC).
  - `volume_spike`: **0** — the XIC.TO alert is GONE.
  - Verification queries (all empty for the volume alert):
    ```sql
    SELECT * FROM alert_queue WHERE id='vol-XIC.TO-20260813130058';   -- []
    SELECT alert_type, COUNT(*) FROM alert_queue GROUP BY alert_type;  -- [('oscillator_extremes', 9)]
    SELECT id FROM alert_queue WHERE id LIKE 'vol-%';                 -- []
    ```

### Why this is NOT the dedup miscount
The dedup path (`write_alert` returns `None` within 300s) prints `alert_id: None`. Here the printed
id is a **real** value (`vol-XIC.TO-20260813130058`), so `save()` returned a non-None id and the
`run_volume_check` counter incremented on a genuine return — yet no row exists. Dedup would have
returned `None`; this didn't. Conclusion: the volume-check write is being dropped *after* `save()`
returns, or routed elsewhere.

### Controlled reproduction (save path itself works)
```python
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.getcwd(), 'python', 'src'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
sys.path.insert(0, os.getcwd())
from src.db.alert_repository import AlertRepository
from src.db.alert_dto import AlertDTO
repo = AlertRepository(sqlite_mode=True)
tid = "vol-TESTREPRO-00000000000000"
rid = repo.save(AlertDTO(alert_id=tid, alert_type="volume_spike",
                         symbol="TESTREPRO", severity="high", payload={"x":1}))
# rid == tid, and the row IS readable from alert_queue; delete after:
c = sqlite3.connect("/root/.hermes/cache/analysis_results.db")
c.execute("DELETE FROM alert_queue WHERE id=?", (tid,)); c.commit(); c.close()
```
The test row persisted and read back fine — so `AlertRepository.save` + the SQLite `alert_queue`
table are functional. The real run's volume alert still vanished. **Suspected bug lives in
`run_volume_check` / the volume-spike write orchestration, not in the repository.**

---

## ⚠️ Anomaly class: alert reported as WRITTEN (real id + incremented count) but ABSENT from the store

Observed in two separate runs now — the printed `alert_id` is a real value and the per-check
counter increments, yet the row never lands in `alert_queue`. This is NOT the dedup miscount
(dedup yields `alert_id: None`; here the id is non-None).

### Case 1 — volume_spike (run 2026-08-13 ~19:00 UTC)
- Stdout: `🔴 XIC.TO: Volume spike 2.43x (alert_id: vol-XIC.TO-20260813130058)` +
  `Volume check: 1 alerts written to alert_queue`.
- Store at run end: `volume_spike` = **0**, `oscillator_extremes` = 9 (all persisted).
- Verification queries all empty for the volume alert:
  ```sql
  SELECT * FROM alert_queue WHERE id='vol-XIC.TO-20260813130058';   -- []
  SELECT alert_type, COUNT(*) FROM alert_queue GROUP BY alert_type;  -- [('oscillator_extremes', 9)]
  SELECT id FROM alert_queue WHERE id LIKE 'vol-%';                 -- []
  ```

### Case 2 — gap_up (run 2026-09-09 ~12:30 ET)
- Stdout: `🚀 CEF: Gap up 3.15% (alert_id: gap-CEF-20260909123058)` +
  `Gap check: 1 alerts written to alert_queue`, total `1`.
- Store at run end (`~/.hermes/cache/analysis_results.db`.alert_queue): **0 rows** — the gap
  alert is gone, and the entire table was empty post-run.
- Verification: `SELECT COUNT(*) FROM alert_queue;` → `0`.
- Note: this run's oscillator/volume/natr counts were also 0 (genuinely no spike that tick),
  so the only reported alert was the gap — and it did not persist.

### Why this is NOT the dedup miscount
The dedup path (`write_alert` returns `None` within 300s) prints `alert_id: None`. Here the printed
id is a **real** value, so `save()` returned a non-None id and the `run_*_check` counter incremented
on a genuine return — yet no row exists. Dedup would have returned `None`; this didn't.

### Controlled reproduction (save path itself works)
```python
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.getcwd(), 'python', 'src'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
sys.path.insert(0, os.getcwd())
from src.db.alert_repository import AlertRepository
from src.db.alert_dto import AlertDTO
repo = AlertRepository(sqlite_mode=True)
tid = "gap-TESTREPRO-00000000000000"
rid = repo.save(AlertDTO(alert_id=tid, alert_type="gap_up",
                         symbol="TESTREPRO", severity="high", payload={"x":1}))
# rid == tid, and the row IS readable from alert_queue; delete after:
c = sqlite3.connect("/root/.hermes/cache/analysis_results.db")
c.execute("DELETE FROM alert_queue WHERE id=?", (tid,)); c.commit(); c.close()
```
The test row persists and reads back fine — so `AlertRepository.save` + the SQLite `alert_queue`
table are functional. The real run's alert still vanished. **Suspected bug lives in the specific
check's write orchestration (`run_gap_check` / `run_volume_check` → `write_alert(...)`), not in the
repository.** Both affected types (`volume_spike`, `gap_up`) share the same `write_alert()` call site;
`oscillator_extremes` (which DOES persist) is the counter-example.

### Operational rule (embed this)
After ANY `detection_triggers.py --sqlite` run, do not trust the printed counts or printed ids — reconstruct against the store:

```sql
SELECT alert_type, COUNT(*) FROM alert_queue GROUP BY alert_type;
SELECT alert_type, COUNT(*) FROM alert_queue WHERE created_at >= '<RUN_DATE>';
```

If ANY reported alert type has count > 0 in stdout but 0 in the store, treat it as a suspected persistence bug — not a benign dedup — and investigate the corresponding `run_*_check` / `write_alert(...)` path. The `oscillator_extremes` type is the known-good control: it persists reliably and can be used to confirm the store write path is up. Note: `created_at` in this table is UTC (`CURRENT_TIMESTAMP`), so compare against the UTC run date.

---

## Session verification — 2026-09-23 (cron, 15:46 ET / 19:46 UTC, --sqlite)
Confirmed the same patterns: `sqlite_mode` writes ONLY to SQLite `ANALYTICS_DB`
(`~/.hermes/cache/analysis_results.db`); workspace `.db` files are decoys; stdout
count ≠ store count for `volume_spike`/`gap_up`, `oscillator_extremes` remains the
reliable persistence control.

Run result (`detection_triggers.py --sqlite`, exit 0, no errors):
- `oscillator_extremes`: 2 persisted (`osc-RUS.TO-20260923094642` RSI 93.7 overbought /
high, 5 days; `osc-WJX.TO-20260923094643` RSI 85.8 overbought / medium, 2 days).
- `volume_spike`: 0 (genuine, no trigger).
- `natr_spike`: 0 (genuine, no trigger).
- `gap_up`: 0 (genuine, no trigger).
- SQLite store verified with: `SELECT alert_type, severity, COUNT(*) FROM alert_queue GROUP BY alert_type, severity;` — only `oscillator_extremes` (high/medium) present.
- No MariaDB writes occurred (intraday `--sqlite` mode). Read-only `watchlist_symbols` SELECT hit MariaDB as expected.
- `sqlite3.OperationalError: database is locked` was NOT observed this run; if it occurs, retry once before diagnosing (WAL + concurrent access is transient).

---

## Session note — 2026-09-21 verification (cron run, weekday, 15:46 ET / 19:46 UTC)
Verified with the canonical command above (`--sqlite`, exit 0, no errors):
- SQLite store = `~/.hermes/cache/analysis_results.db` (`ANALYTICS_DB` from `config.paths`); workspace `price_intraday.db` / `detection_alerts.db` / `alerts.db` are all decoys (empty, 0 bytes, no tables) — do NOT verify against them.
- `alert_queue` after run: 2 rows (`oscillator_extremes` high only: `CNR.TO` RSI 28.9 / 7 days; `RUS.TO` RSI 74.2 / 3 days). `volume_spike`/`natr_spike`/`gap_up` = 0 (genuine, not errors).
- User instruction embedded: **Do NOT expect MariaDB writes during intraday.** `--sqlite` = SQLite-only writes (`ANALYTICS_DB`); read-only `watchlist_symbols` SELECT still hits MariaDB. Confirm persistence via the SQLite store (not stdout counts) — the stdout-vs-store anomaly (`volume_spike` / `gap_up` reported-written-but-absent) applies; `oscillator_extremes` remains the known-good persistence control.
