# Sys.path Ordering Pitfall — python/src/ must precede python/

## The problem

The ksf_stockmarket Python tree has two `db/` locations:

- `python/src/db/` — **no `__init__.py`**, holds `exchange_routing.py` (and other DAO modules). This is a **namespace package**.
- `python/db/` — **has `__init__.py`**, holds the legacy adapter layer (`adapter.py`, `mysql_adapter.py`, `sqlite_adapter.py`). This is a **regular package**.

When both directories are on `sys.path`, Python resolves `import db` to whichever `db/` directory appears **first** in `sys.path`. If `python/` (which contains `db/__init__.py`) is searched before `python/src/` (which contains `db/exchange_routing.py` but no `__init__.py`), then:

1. `import db` succeeds — loads `python/db/__init__.py` (the regular package)
2. `from db.exchange_routing import ...` **FAILS** with `ModuleNotFoundError: No module named 'db.exchange_routing'`

because Python found the `db` package in `python/db/` and never looks in `python/src/db/` for submodules.

This broke `stock_analysis_writer.py` — the import order in that script had `python/` at sys.path[0] and `python/src/` at sys.path[1], so `db.exchange_routing` could never be found.

## The fix (two options)

**Option A — insert `python/src/` at sys.path[0] before `python/`** (what `stock_analysis_writer.py` does now):

```python
_PY_SRC = Path('/home/ksf_stockmarket/ksf_stockmarket/python/src')
_PY_ROOT = Path('/home/ksf_stockmarket/ksf_stockmarket/python')
if str(_PY_SRC) not in sys.path:
    sys.path.insert(0, str(_PY_SRC))   # wins position 0
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))   # wins position 1 (after python/src/)
```

Since `insert(0, ...)` puts later calls closer to index 0, insert `python/` first, then `python/src/` on top. The result: `python/src/` at [0], `python/` at [1].

**Option B — add `python/src/db/__init__.py`** (what was done as a complementary fix):

Even a docstring-only `__init__.py` makes `python/src/db/` a regular package, so Python searches both `db/` directories as regular packages and the one at the lower sys.path index wins. With `python/src/` before `python/` in sys.path, `python/src/db/` wins.

Both options together are the safest combination — the `__init__.py` prevents namespace-package ambiguity, and the path ordering ensures the right `db/` wins.

## How to detect this bug

Symptom: `from db.exchange_routing import ...` raises `ModuleNotFoundError: No module named 'db.exchange_routing'` even though `python/src/db/exchange_routing.py` exists on disk.

Quick diagnosis:

```bash
cd /home/ksf_stockmarket/ksf_stockmarket
python3 -c "
import sys
# replicate the script's path setup
sys.path.insert(0, 'python/src')
sys.path.insert(0, 'python')
import db
print('db package loaded from:', db.__file__)
print('db.__path__:', db.__path__)
"
```

If `db.__file__` points to `python/db/__init__.py`, the wrong package is winning. If it points to `python/src/db/__init__.py` (or `python/src/db` as a namespace), the right one is winning.

## General rule

When a project has **two directories containing the same package name** at different path depths, the sys.path ordering determines which one wins. Always verify the import resolution with the above diagnostic before trusting that a cross-directory import will work. This is distinct from the more general `PYTHONPATH` env-var hijack pitfall (see `references/cron-env-loading-pattern.md` in the software-development skill) — here the issue is intra-repo path ordering, not env var injection.

## Files affected in this session

- `python/src/db/__init__.py` — created (was missing, now exists with docstring)
- `scripts/stock_analysis_writer.py` — sys.path setup corrected to insert `python/src/` before `python/`
