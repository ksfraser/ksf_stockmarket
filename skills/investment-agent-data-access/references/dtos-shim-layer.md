# DTO backward-compat shim layer (src/db/ → dto/)

## What it is

The workspace is mid-migration to a clean layered architecture. The canonical
DTO package is `dto/` (physically `repo/src/dto/`), but existing code across
the repo still imports from `src/db/stock_price_dto.py` and
`src/db/alert_dto.py`. These two modules are **backward-compat shims**, not
independent definitions.

| Shim file | Re-exports from | Why |
|---|---|---|
| `src/db/stock_price_dto.py` | `dto.price` (`StockPriceDTO`, `to_ohlcv_dataframe`) | Old code imports `from src.db.stock_price_dto import StockPriceDTO`. |
| `src/db/alert_dto.py` | `dto.alert` (`AlertDTO`) | Old code imports `from src.db.alert_dto import AlertDTO`. |

The shims exist so **no import site breaks during the phased migration**.
New code should import from `dto.*` directly; old code continues to work
through the shim.

## Why this matters for `sync_stock_prices.py`

`sync_stock_prices.py` does:

```python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
from src.db.stock_price_dto import StockPriceDTO
```

The `sys.path.insert` makes `repo/src` a top-level package directory.
`from src.db.stock_price_dto import ...` then resolves as `src/db/stock_price_dto.py`,
which re-exports `from dto.price import StockPriceDTO, to_ohlcv_dataframe`.
That second import requires `dto` to be importable as a top-level package —
which requires `repo/src` on `sys.path` (or `PYTHONPATH`). The insert above
provides exactly that, which is why the 2-entry `PYTHONPATH` form works for
this script. See `references/sync-stock-prices-invocation.md`.

## Guard implication

The guard (`scripts/guard_standardized_access.py`) allows `src/db/` for the
data layer. The shim files themselves are clean (they only re-export, no raw
I/O), so editing them does not trip the guard. Do NOT remove a shim until all
import sites have been migrated to `dto.*` — removing the shim breaks the old
import path and is NOT guarded against.

## Related

- `references/sync-stock-prices-invocation.md` — the import path + shim
  interaction that makes the 2-entry PYTHONPATH command work.
- `references/entrypoint-invocation.md` — the broader entrypoint path requirements.
