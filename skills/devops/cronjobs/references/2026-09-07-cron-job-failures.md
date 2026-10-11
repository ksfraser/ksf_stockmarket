# TV Screener + Zacks Cron Job Failures — 2026-09-07

Session-originated reference: the two cron jobs that were reporting `error` status, their root causes, the fixes, and the verification path.

## Jobs involved

| Job ID | Name | Script | Workdir | Status before fix |
|---|---|---|---|---|
| `c562ed204283` | Ingest TradingView Screener Results Into Stockmarket Tables | `run_ingest_screener.sh` | `/home/ksf_stockmarket/ksf_stockmarket` | ❌ error |
| `7017d7edb803` | TradingView Daily Screener | `run_tv_screener.sh` | `/home/ksf_stockmarket/ksf_stockmarket` | ✅ ok (but path also wrong) |
| `5a2a8f15cbf6` | Nightly Zacks research refresh | `run_zacks_refresh.sh` | `/var/www/stockmarket-app` | ❌ error |

## Root causes

### 1. Script path resolution (jobs c562ed204283, 7017d7edb803, 5a2a8f15cbf6)

The cron scheduler resolves `script` relative to `workdir`. All three jobs set `script` to a basename with no directory prefix. The files:

- `run_ingest_screener.sh` + `run_tv_screener.sh` — existed only at `scripts/run_*.sh` inside the ksf_stockmarket repo, NOT at the repo root. The scheduler looked for `$WORKDIR/run_ingest_screener.sh` and didn't find it.
- `run_zacks_refresh.sh` — did NOT exist at either location in the stockmarket-app repo. The scheduler couldn't find it at all.

**Why TV screener (7017d7edb803) reported `ok` despite the same path bug:** unclear — possibly the job ran before the path issue manifested, or there was a fallback resolution path. The ingest screener (c562ed204283) consistently failed.

### 2. Missing .env sourcing for env-reading scripts (job 5a2a8f15cbf6)

`python/zacks_scraper.py` reads DB credentials directly from environment variables:

```python
host = os.environ.get("DB_HOST", "ksfraser.ca")
user = os.environ.get("DB_USER", "ksfraser_stockmarket")
password = os.environ.get("DB_PASS", "")
database = os.environ.get("DB_NAME", "ksfraser_stock_market")
```

It does NOT go through a shared `db_connector` module with fallback paths. Without the wrapper sourcing `.env`, the cron environment had empty `DB_PASS` → connection failed.

**Contrast:** `python/ingest_screener_symbols.py` uses `python.db_connector` which has config.yaml/env var fusion and may partially mask missing env vars. Scripts that read env vars directly have no fallback.

## Fixes applied

### ksf_stockmarket: commit 3f3b4f4 (fx/seg-fund-ivari → cherry-picked to main as 0e14393)

Files added at repo root (`/home/ksf_stockmarket/ksf_stockmarket/`):
- `run_ingest_screener.sh` — sources `.env`, `exec python3 -u python/ingest_screener_symbols.py`
- `run_tv_screener.sh` — sources `.env`, `exec python3 -u tv_screener.py`

Also fixed `scripts/run_ingest_screener.sh` (was missing `exec` line in some copies).

### stockmarket-app: commit 468232e (feature/zacks-rw → cherry-picked to main as edf5951)

Files added at repo root (`/var/www/stockmarket-app/`):
- `run_zacks_refresh.sh` — sources `.env`, `exec python3 -u python/zacks_scraper.py --all`

## Verification performed

1. **Wrapper path resolution:** confirmed both wrappers exist at repo root AND `scripts/` in their respective repos. `test -f $WORKDIR/$SCRIPT` returns EXISTS for all three jobs.
2. **`.env` sourcing:** ran `bash -c 'set -e; . ./run_*.sh 2>/dev/null; echo DB_HOST=$DB_HOST'` — all three resolve `DB_HOST=ksfraser.ca`.
3. **`python3` resolution:** `which python3` returns `/usr/local/lib/hermes-agent/venv/bin/python3` inside wrapper context.
4. **Live DB connectivity:** 
   - Ingest screener ran clean through pre-price-sync steps (258 symbol-master updates written to MariaDB, price sync triggered for 120 symbols). Full price-sync takes 4+ min; test budget cut it off.
   - Zacks scraper `--status` ran clean (1,921 symbols, latest 2026-09-05).
   - `refresh_perf_windows.php` ran clean (3,328 perf windows + 3,304 volume rows in 14s) — the precomputed table the StockFilter engine needs.
5. **End-to-end smoke:** `cd $WORKDIR && bash $SCRIPT` — all three wrappers start and connect.

## Python `python/` namespace package gap discovered

`python/` in ksf_stockmarket has NO `__init__.py`. Scripts that do `import python.db_connector` require:
1. Repo root on `sys.path` (scripts add it themselves via `Path(__file__).resolve().parents[1]`)
2. `python/` recognized as a package

Without `__init__.py`, a direct inline test (`python3 -c "import python.db_connector"`) fails with `ModuleNotFoundError` even though the actual entry point scripts work (they add `sys.path` themselves). 

**Smoke test artefact:** the inline import test failure was NOT a real problem — it was a test artefact. The actual `bash run_ingest_screener.sh` invocation works because the script adds the repo root to `sys.path`.

## Stash-pop conflict encountered

`git stash pop` on `fx/seg-fund-ivari` introduced a rebase-style conflict in `python/ingest_screener_symbols.py` (`UU` status, `<<<<<<< Updated upstream` markers). The stash was old parked WIP from `fx/seg-fund-filters` (a different branch), and its version of the file conflicted with HEAD. 

**Resolution:** restored both conflicted files from HEAD (`git checkout HEAD -- <file>`) and dropped the stash entirely — the stashed work was not needed.

## "Ready to merge to main" assessment

### Cron wrapper fixes: READY (already merged)

- ksf_stockmarket main: `0e14393` — pure addition (new files at repo root + small scripts/ tweak). Zero conflict risk.
- stockmarket-app main: `edf5951` — pure addition (new files at repo root + `scripts/`). Zero conflict risk.

Both are narrow fixes that address the exact root cause. Safe to merge — and already merged.

### Broader feature branches: NOT READY

- `fx/seg-fund-ivari` (ksf_stockmarket): 28 commits ahead of main, all pushed, working tree clean (only `?? consolidate_symbols.py` and `?? run_tv_screener_resilient.py` untracked). But carries substantial seg-fund work beyond the cron fix — not main-merge-ready as a whole.
- `feature/zacks-rw` (stockmarket-app): 15 commits ahead of main, all pushed, BUT has 8 modified files uncommitted (StockController +283 lines, StockFilter ±101 lines, refresh_perf_windows.php +224 lines, etc.) plus untracked docs/dispatcher. Substantial feature work, partially tested (phpunit 9/9 pass, live-DB verify done) but NOT end-to-end smoke-tested as a full integration. Not main-merge-ready.

**Lesson:** merge-readiness is per-fix, not per-branch. Cherry-pick the narrow safe fix; leave the rest on the feature branch until it's committed, reviewed, and E2E-tested.
