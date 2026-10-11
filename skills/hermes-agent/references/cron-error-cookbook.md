# Cron Error Cookbook — reproduction recipes

Four real failures from one maintenance pass, captured as copy-pasteable recipes.
Each lists the symptom, root cause, and the exact fix.

---

## 1. performance-recalc  (script: calculate_performance.sh → scripts/calculate_performance.py)

**Symptom A — `ModuleNotFoundError: No module named 'dto'`**
(after the first `config` import was already fixed by adding the repo root to PYTHONPATH).

Root cause: the wrapper set
`PYTHONPATH="/root/.hermes/workspace/investment-agent:${PYTHONPATH:-}"`.
The transitive import `from dto.price import ...` needs `dto` which lives at
`investment-agent/src/dto` — so `src/` must also be on the path.

Fix (in the `.sh`):
```bash
export PYTHONPATH="/root/.hermes/workspace/investment-agent:/root/.hermes/workspace/investment-agent/src:${PYTHONPATH:-}"
```

**Symptom B (next run) — `sqlite3.OperationalError: no such column: exchange`**
in `SQLitePriceRepository._ensure_schema` against
`/var/www/stockmarket-app/data/analysis_results.db`.

Root cause: `price_intraday` already existed with an OLD schema (no
`base_symbol/exchange/unit_class`). `CREATE TABLE IF NOT EXISTS` was a no-op;
the subsequent `CREATE INDEX ... ON price_intraday(exchange)` failed.

Fix — migrate, preserve data (13,409 rows):
```bash
DB=/var/www/stockmarket-app/data/analysis_results.db
sqlite3 "$DB" "ALTER TABLE price_intraday ADD COLUMN base_symbol TEXT; \
               ALTER TABLE price_intraday ADD COLUMN exchange TEXT; \
               ALTER TABLE price_intraday ADD COLUMN unit_class TEXT;"
sqlite3 "$DB" "PRAGMA table_info(price_intraday);"   # confirm 12 cols now
sqlite3 "$DB" "SELECT COUNT(*) FROM price_intraday;"  # still 13409
```
Re-run → `EXIT: 0`.

---

## 2. Nightly Indicator Calculator  (nightly_indicator_calculator.sh → python/indicator_calculator.py)

**Symptom — `Script timed out after 120s`.**

Root cause: 5 symbols ≈ 111s; job runs `0 2 * * *` alongside ~6 other heavy
jobs, so 02:00 contention pushes it past the hard 120s runner kill.

Fix — lower the per-run limit (verified ≈60s, safe margin):
```bash
# in nightly_indicator_calculator.sh
python3.10 python/indicator_calculator.py --limit 2 --verbose 2>&1 | tee /tmp/nightly_indicator_calculator.log
```
Verify: `✓ 5,670 indicator rows in 60s` → `EXIT: 0`.
Caveat: only 2 symbols/night now. For full coverage, implement a stateful
offset sweep instead of cramming into 120s.

---

## 3. Nightly Analyst Ratings  (populate_analyst_ratings.sh → python/populate_analyst_ratings.py)

**Symptom A — `can't open file '/root/.hermes/scripts/python/populate_analyst_ratings.py'`.**
Root cause: the runner executed the script from `/root/.hermes/scripts/`, so the
relative `python/populate_analyst_ratings.py` resolved to a non-existent path.

Fix — absolute path + full PYTHONPATH in the `.sh`:
```bash
REPO_DIR="/home/ksf_stockmarket/ksf_stockmarket"
export PYTHONPATH="${REPO_DIR}:${REPO_DIR}/python:${REPO_DIR}/python/src"
python3.10 "${REPO_DIR}/python/populate_analyst_ratings.py" 2>&1 | tee /tmp/populate_analyst_ratings.log
```

**Symptom B — even after the path fix it runs for many minutes (>120s).**
Root cause: `LIMIT_PER_RUN = 1000` symbols, each with a yfinance call + sleep.
Inherently exceeds the 120s kill.

Fix — add a wall-clock budget so it exits cleanly before the kill (imports
`os` and `time` at top of the script):
```python
def run() -> None:
    symbols = load_symbols_prioritized()
    print(f"Priority list: {len(symbols)} symbols")
    start = time.time()
    budget = int(os.getenv("ANALYST_RATINGS_BUDGET", "90"))
    processed = 0
    ...
    for idx, original_symbol in enumerate(symbols, 1):
        if time.time() - start > budget:
            print(f"Time budget {budget}s reached after {processed} processed — stopping (re-run to continue).")
            break
        ticker = resolve_ticker(original_symbol)
        ...
```
Verify with a short budget: `ANALYST_RATINGS_BUDGET=15 python3.10 python/populate_analyst_ratings.py`
→ `Time budget 15s reached ...` + `EXIT: 0`.

---

## 4. hermes-memory-skills-backup  (no_agent script job)

**Symptom — job errors because the script can't be found.**
Root cause: `script` field was `"bash /root/.hermes/backup_memory_skills.sh"`
(a command + path). The runner resolves `script` as `<scripts_dir>/<name>`,
so a command/path string doesn't resolve, and the file wasn't in the scripts dir.

Fix:
```bash
cp /root/.hermes/backup_memory_skills.sh /root/.hermes/scripts/backup_memory_skills.sh
# then:
cronjob(action='update', job_id='<id>', script='backup_memory_skills.sh')
```
