# Exchange routing module — reference implementation

Reference implementation of the exchange-routing / stockprices-DAO layer built in the
2026-09-13 session. Captured here so a future session that builds a similar DB-routing layer
can find the pattern rather than re-deriving it.

## Files

- **Module:** `python/src/db/exchange_routing.py` (the router)
- **Unit tests:** `tests/unit/test_exchange_routing.py` (SQLite + mock fixtures)
- **Branch:** `fx/stockprices-exchange-routing` (the feature branch for the whole DAO work)

## Module: exchange_routing.py

Location: `python/src/db/exchange_routing.py`

### Public API

| Function | Purpose |
|----------|---------|
| `normalise_exchange(raw: str) -> str` | Raw exchange name → DB-safe suffix. Mirrors stored-proc `REPLACE(exchange, '.', '_')`. TSX.V → tsx_v. |
| `exchange_db_name(exchange_raw: str) -> str` | Returns `ksfraser_sm_<normalised>`. e.g. TSX.V → `ksfraser_sm_tsx_v`. |
| `resolve_exchange_for_symbol(symbol, conn=, default_exchange=) -> str` | Looks up `symbol_master.exchange`, returns raw exchange, cached per session. Falls back to default if not found or lookup fails. |
| `resolve_exchange_db_name_for_symbol(symbol, conn=, default_exchange=) -> str` | Convenience: resolve_exchange_for_symbol + exchange_db_name, without opening a connection. |
| `get_exchange_connection(symbol, conn=, default_exchange=, database=) -> Connection` | Opens a pymysql connection to the exchange DB. Reads credentials from env vars (same source as db_connector). Has a documented multi-host stub in the except block for future per-exchange host/user/db lookup. |

### Design decisions

**1. Normalisation mirrors the stored procs.**

The stored procs do `REPLACE(exchange, '.', '_')`. The code does the same, plus a broader
sanitisation regex (`[^A-Za-z0-9_]+` → `_`) so future odd exchange names (hyphens, spaces)
don't produce invalid database names. The single place that knows the mapping is this module —
the stored procs and the code stay consistent by construction.

**2. Credentials come from env vars, not from importing db_connector.**

This module lives at `python/src/db/` but `db_connector` lives at `python/db_connector.py`
(repo root). Different import paths — a `python/src/` module cannot `import db_connector`
directly without the repo root on its import path. Rather than fight the import layout, the
module reads the same env vars (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_PORT`) that
`db_connector` reads. Same credential source of truth, no import coupling.

This is captured as a pitfall in the `devops/cronjobs` skill under
"Pitfall: python/src/ modules can't import db_connector directly."

**3. Exchange DB connection is read-only routing — the repository owns writes.**

`get_exchange_connection()` just returns a connection. The repository decides whether to
write to the exchange DB (dual-write) or rely on the nightly `migrate_stockprices` proc.
The router stays out of the write-policy decision.

**4. Multi-host stub is documented, not implemented.**

When exchanges move to separate hosts/users in the future, the `except` block in
`get_exchange_connection()` has a commented placeholder showing the intended lookup sources:
(a) DB table `ksf_exchange_routing`, (b) JSON file `config/exchange_routing.json`, (c) env
vars `DB_HOST_<EXCHANGE>`. Pick one, uncomment, replace the stub. The stub is there so a
future dev can find it by reading the code.

**5. Symbol→exchange cache is per-session, keyed by (symbol, default_exchange).**

`resolve_exchange_for_symbol()` caches lookups so repeated calls for the same symbol don't hit
the DB. The cache key includes `default_exchange` so a different default produces a different
cache entry (a real lookup would return the same exchange regardless, but the cache is there for
performance, not correctness — the key just needs to be consistent). Clear via
`clear_symbol_exchange_cache()`.

### Unit tests: test_exchange_routing.py

Location: `tests/unit/test_exchange_routing.py`

Mirrors the style of `tests/unit/test_db_adapter.py`: SQLite in-memory fixtures for the
symbol_master lookup path, direct tests for the pure functions (normalise_exchange,
exchange_db_name), and stubbed tests for the connection path (no MariaDB needed).

Key test classes:

- `TestNormaliseExchange` — pure function, 11 tests: TSX.V→tsx_v, identity, case-insensitive,
  whitespace, double-period, empty raises, whitespace-only raises, all-dots raises.
- `TestExchangeDbName` — 5 tests: TSX.V, TSX, NYSE, prefix constant.
- `TestResolveExchangeForSymbol` — 8 tests using mock connections (unittest.mock.MagicMock)
  and SQLite fixtures: known symbol, unknown→default, case-insensitive, whitespace, empty
  table, cache, cache cleared, lookup failure→default.
- `TestResolveExchangeDbNameForSymbol` — 2 tests: resolves name, unknown→default.
- `TestGetExchangeConnectionStub` — 3 tests: signature, stub documentation present,
  missing credentials→error logged.

One test (`test_cache_different_default_not_used`) was removed during the session because the
cache design was settled on **symbol-only** (not (symbol, default) pair). The reasoning: the
default is only used as a fallback when the symbol isn't in symbol_master, so it doesn't affect
the cached result for a symbol that IS in symbol_master. The cache key is just `symbol`.

### Edge cases handled

- Empty/blank exchange string → ValueError
- Whitespace-only exchange → ValueError (normalises to empty)
- All-dots exchange → ValueError
- Symbol not in symbol_master → default_exchange
- symbol_master lookup failure (exception) → default_exchange + warning log
- Missing DB_PASS env var → connection error logged + re-raised (caller decides)

## Related

- [2026-09-13 indicators migration: log trim + monitor restart + cron pause sweep](2026-09-13-indicators-migration-recovery.md)
- `devops/cronjobs` skill — pitfall on `python/src/` import path, self-removing monitors, workflow preference for tests+d accompanying docs.
