# Phase 3 — service-extraction recipes (exact before/after)

Companion to the "Phase 3 — service-extraction recipes" section in SKILL.md.
These are the real edits from commit `23de7ab` (the first Phase 3 slice).

## 1. `src/analysis/symbol_performance.py`

### Remove unused `yfinance` import + add `DataSource` + fix missing import
Before:
```python
import pymysql # noqa: F401 — register adapter
import pandas as pd
import yfinance as yf

from src.db.sqlite_price_repository import SQLitePriceRepository
from src.db.stock_price_dto import StockPriceDTO
```
After:
```python
import pymysql # noqa: F401 — register adapter
import pandas as pd

from src.db.sqlite_price_repository import SQLitePriceRepository
from src.db.stock_price_dto import StockPriceDTO
from src.db.connection import DataSource
from config.db import get_mariadb_config
```
> `get_mariadb_config` was CALLED at line 125 but never imported — a latent
> `NameError` that only surfaced at runtime when the service instantiated the repo.
> `py_compile` did NOT catch it.

### Route MariaDB through DataSource
Before:
```python
    def _conn(self):
        return pymysql.connect(**self._conn_params)
```
After:
```python
    def _conn(self):
        return DataSource.mariadb_connection(self._conn_params)
```
> `self._conn_params` is `get_mariadb_config()` (a dict). `DataSource.mariadb_connection`
> merges it over its defaults and filters `None`, so this is byte-compatible with the
> old `pymysql.connect(**config)`.

## 2. `src/rules/rule_registry.py`

### Add import
```python
from db.connection import DataSource
```

### Replace all `sqlite3.connect(self.db_path)` (×13)
Before:
```python
        with sqlite3.connect(self.db_path) as conn:
```
After:
```python
        with DataSource.sqlite_connection(self.db_path) as conn:
```
> `DataSource.sqlite_connection` already sets `conn.row_factory = sqlite3.Row`,
> so any `conn.row_factory = sqlite3.Row` lines in the file are now redundant but
> harmless. Keep `import sqlite3` only if `sqlite3.Row` is referenced in type hints.

## 3. `src/services/symbol_performance_service.py` (new)

Service wraps the existing `SymbolPerformanceRepository` + `SymbolPerformanceCalculator`
(kept in place for backward-compat). Key construction detail:
```python
from config.paths import ANALYTICS_DB
from src.db.sqlite_price_repository import SQLitePriceRepository

class SymbolPerformanceService:
    def __init__(self, benchmark: str = "SPY"):
        self.benchmark = benchmark
        self._repo = None
        self._calc = None

    @property
    def calc(self) -> SymbolPerformanceCalculator:
        if self._calc is None:
            self._calc = SymbolPerformanceCalculator(
                SQLitePriceRepository(ANALYTICS_DB), self.benchmark
            )
        return self._calc
```
> `SQLitePriceRepository.__init__(self, db_path: str)` REQUIRES `db_path` — it is
> NOT optional. Pass `ANALYTICS_DB` from `config.paths`.

## Smoke-test pattern (mandatory — py_compile is not enough)

```python
import os, sys, tempfile
ROOT = "/root/.hermes/workspace/investment-agent"
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "src"))

# residual guard patterns gone
for f, pats in [
    ("src/analysis/symbol_performance.py", ["pymysql.connect(", "import yfinance"]),
    ("src/rules/rule_registry.py",        ["sqlite3.connect("]),
]:
    txt = open(os.path.join(ROOT, f)).read()
    assert all(p not in txt for p in pats), f"residual in {f}"

import py_compile
for f in ["src/analysis/symbol_performance.py", "src/rules/rule_registry.py",
          "src/services/symbol_performance_service.py"]:
    py_compile.compile(os.path.join(ROOT, f), doraise=True)

# service loads + builds through the layer
from src.services.symbol_performance_service import SymbolPerformanceService
assert SymbolPerformanceService.best_benchmarks(2)[:1] == ["SPY"]
_ = SymbolPerformanceService("SPY").calc   # builds via DataSource-backed repo

# rule_registry creates its schema THROUGH DataSource at runtime
import rules.rule_registry as rr, sqlite3 as _sq
tmp = os.path.join(tempfile.mkdtemp(), "rules.db")
rr.RuleRegistry(db_path=tmp)   # __init__ runs _ensure_schema + _seed_if_empty
conn = _sq.connect(tmp)
tbls = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
conn.close()
assert "business_rules" in tbls
print("PHASE 3 SMOKE OK")
```

Run `scripts/verify_phase_refactor.py --files <...> --service <...>` for the fast
pre-guard scan, then the runtime round-trip above before committing.
