# Python Architecture Standard

> **Version:** 1.0 | **Date:** 2026-06-19 | **Repo:** `ksfraser/ksf_stockmarket`
> **Status:** Canonical coding contract for all Python code in `python/` and `python/src/`.

---

## 1. Purpose

This document is the ** enforceable** standard for Python code in this repository.
It resolves the current situation: v4 architecture is defined at a high level, but
the Python implementation is a collection of scripts with overlapping responsibilities,
no single logging policy, no event boundary rules, and no module ownership model.

This standard follows the same spirit as the PHP PSRs:
- one responsibility per module,
- dependency via constructor/config, not globals,
- events as the only cross-layer boundary,
- centralized logging,
- testability enforced by structure.

---

## 2. Layer Ownership

Every Python module must belong to exactly one layer. Cross-layer imports are
forbidden unless the lower layer publishes an event and the upper layer consumes it.

| Layer | Owner directory | Responsibility | Must not do |
|-------|-----------------|----------------|-------------|
| L0 Screener | `python/src/screener/` or `python/layer0_screener.py` | Universe selection, sleeve tagging | Call orchestrator, write orders |
| L1 Signals | `python/src/strategies/` | Signal generation from indicators | Fetch prices, write portfolio |
| L2 Risk | `python/src/risk/` | Position sizing, stops, caps | Compute indicators |
| L3 Portfolio | `python/src/portfolio/` | Portfolio construction, allocation | Screener logic |
| L4 Risk Mgmt | `python/src/risk/` | Regime, drawdown, correlation | Execute trades |
| Agents | `python/agents/` | GA/NN/RL training + inference | PHP controllers, alerts |
| Data | `python/src/db/` | DTOs, repositories, fetchers | None — this is foundational |
| Orchestration | `python/src/queue_worker.py`, `python/daily_pipeline.py` | Event handling, scheduled runs | Direct agent training |
| Alerts | `python/src/alerts/` | Alert detection, dedup, dispatch | Price fetching, TA calculation |
| API | `python/api/` | HTTP endpoints only | Direct DB writes outside adapter |

### 2.1 API is not a layer
`python/api/app.py` is a thin HTTP adapter. It must delegate immediately to the
appropriate layer service. No business logic in routes.

### 2.2 Scripts belong to a layer
Standalone scripts like `python/fetch_prices.py`, `python/ta_calculator.py`,
`python/scoring_engine.py`, `python/correlation_analysis.py` are **data tools**.
They are entry points, not libraries. Library code must live in `python/src/`
under the appropriate layer.

---

## 3. Event-Driven Boundaries

### 3.1 Event contract
All events use the contracts defined in `python/src/events/event_contract.py`.
New events must be added there first. Every event has:
- `event_id` (UUID)
- `event_type` (string constant)
- `payload` (dict — deserialized JSON from DB)
- `occurred_at`, `processed_at`, `status`, `attempts`, `last_error`

### 3.2 Producer/Consumer rules
| Producer | Event type | Consumer |
|----------|-----------|----------|
| PHP controllers, `ingest_screener_symbols.py` | `screener_symbols_ingested` | `queue_worker.py` → price download → TA |
| TransactionController, advisor runner | `transaction_created` | `queue_worker.py` → activate symbol → price/TA |
| SymbolAdminController | `symbol_activated` / `symbol_deactivated` | `queue_worker.py` or immediate if synchronous |
| `daily_pipeline.py` after prices | `prices_loaded` | `ta_calculator.py` or indicator service |
| `ta_calculator.py` after indicators | `indicators_calculated` | orchestrator, advisor runner |
| Alert checks | `alert_created` | `alerts/queue.py` → Discord |

### 3.3 Queue table rules
- `event_queue` is the **only** producer-consumer boundary.
- Producers insert events. Consumers poll `status='pending'` with `FOR UPDATE SKIP LOCKED`.
- Retry: exponential backoff, max 3 attempts. Final failure routes to `dlq` or alert.
- Idempotency: handlers must be safe to run twice. Use `processed_at` + payload hash
  to detect duplicates.

### 3.4 No hidden coupling
Module A must not call Module B directly if they are in different layers.
If A needs B, A emits an event. Direct cross-layer calls are bugs.

---

## 4. Symbol Lifecycle State Machine

Every symbol progresses through these states. The state lives in `symbol_master`
augmented by `pipeline_state` and `last_state_transition` columns.

```
unknown → candidate → pending_backfill → prices_loaded → ta_ready → analysis_eligible
                ↘ (deactivated) → inactive
                  ↘ (delisted) → dead
```

| State | Meaning | Trigger | Next state |
|-------|---------|---------|-------------|
| `unknown` | Not in symbol_master | — | `candidate` on upsert |
| `candidate` | In symbol_master, no prices | screener/transaction/watchlist | `pending_backfill` |
| `pending_backfill` | Backfill queued | event enqueued | `prices_loaded` |
| `prices_loaded` | Has price rows, missing indicators or stale | price worker completes | `ta_ready` |
| `ta_ready` | Has fresh indicators | indicator worker completes | `analysis_eligible` |
| `analysis_eligible` | Ready for GA/NN/RL | orchestrator picks up | — |
| `inactive` | Symbol deactivated | admin or no activity | — |
| `dead` | Delisted/deregistered | monitoring check | — |

**Rules:**
- Any mutation of `symbol_master.is_active`, `watchlist_symbols`, or `transactions`
  that introduces a new symbol must emit an event that drives this state machine.
- The queue worker must implement `handle_symbols_pending_analysis` to advance
  a symbol through `pending_backfill → prices_loaded → ta_ready`.
- The orchestrator must only process symbols in `analysis_eligible` state and
  must transition them to `analysis_pending` while running, then `analysis_eligible`
  on completion. This prevents concurrent agent runs on the same symbol.

---

## 5. Module Structure

### 5.1 Package layout
```
python/
  src/
    db/                        # DTOs, repositories (SQLite/MariaDB), fetchers (yFinance, etc.)
    events/                    # Contracts + repository
    alerts/                    # Detection, dedup, dispatch
    monitoring/                # Volume, price, delisting
    strategies/                # L1 signal generation
    risk/                      # L2 + L4 risk
    portfolio/                 # L3 portfolio construction
    advisors/                  # Advisor runner + strategies
    queue_worker.py            # Event loop
    database.py                # High-level DB facade if needed
    symbol_resolver.py         # Canonical yfinance resolver
  agents/                      # GA, NN, RL, Blender, Orchestrator
  api/                         # Flask/fastapi HTTP adapter
  daily_pipeline.py            # Scheduled entry point
  config_loader.py             # Config-driven factory
  db_connector.py              # Legacy connector (deprecated in favor of python/src/db/)
```

### 5.2 Import rules
- `python/src/*` must **never** import from top-level `python/*` scripts
  (`fetch_prices.py`, `ta_calculator.py`, etc.) directly.
- All external access goes through interfaces defined in `python/src/`.
- Test fixtures in `tests/conftest.py` may provide in-memory SQLite adapters.

### 5.3 PHP resolver mirror
`php/src/Util/SymbolResolver.php` implements the same resolution logic as
`python/src/symbol_resolver.py`. Both must stay in sync:
- exchange_mapping lookup
- symbol_master exchange hint
- `.UN` / `.B.TO` hyphen normalization

---

## 6. Logging

### 6.1 One formatter
A single formatter is configured in one place (application entrypoint or a
dedicated logging bootstrap module). Library code must **not** call
`logging.basicConfig`.

### 6.2 Per-module logger
Every module gets a module-level logger:
```python
import logging
logger = logging.getLogger(__name__)
```

No other logger creation is allowed.

### 6.3 Levels
- `DEBUG`: development-only details, large payloads, per-tick state
- `INFO`: normal lifecycle events (state transitions, event processed, agent run)
- `WARNING`: recoverable anomalies (rate limit hit, missing optional column)
- `ERROR`: handler failure, event moved to failed/retry
- `CRITICAL`: data integrity risk (price gap > 5 days, indicator table absent)

### 6.4 Structured context
Event handlers must include `event_id`, `symbol`, and `state` in extra context
when available. Do not concatenate strings manually; use lazy formatting:
```python
logger.info("processed event %s", event_id)
```

---

## 7. Testing

### 7.1 Three tiers
| Tier | Location | Purpose | Fixtures |
|------|----------|---------|----------|
| Unit | `tests/unit/` | One class/function in isolation | SQLite in-memory via `conftest.py` |
| Integration | `tests/integration/` | DB adapter, queue, end-to-end path | SQLite or MariaDB preview |
| UAT | `tests/uat/` | Business scenario | Seeded data, full pipeline run |

### 7.2 Fixture rules
- Shared fixtures live in `tests/conftest.py`. No inline DB setup in test methods.
- MariaDB tests must be opt-in via env var (`MARIADB_TEST=1`) and must not run
  in default CI.
- All seeded data must be torn down in `teardown_method` or fixture finalizer.

### 7.3 Coverage target
- New code: ≥ 80% line coverage for `python/src/*`.
- Event handlers: ≥ 90% (they are the integration backbone).
- Agents: ≥ 60% (training code is hard to unit test; integration/UAT more important).

### 7.4 Test naming
`test_<method_or_function>_<scenario>_<expected_outcome>()`
Example: `test_handle_screener_symbols_ingested_when_new_symbol_backfills_successfully`.

---

## 8. Dependency Injection

### 8.1 Constructor injection
All services receive their dependencies via `__init__`:
```python
class PriceWorker:
    def __init__(self, db: Database, event_bus: EventBus, config: Config) -> None:
        ...
```

### 8.2 Config-driven factories
Complex construction uses factories keyed by `config.yaml`. See `python/config_loader.py`.
Agents and workers must be instantiable from declarations, not scattered `if/else`.

### 8.3 No singletons in library code
Application entrypoints may create singleton instances; library code must not.

---

## 9. Current Gap Remediation

To bring the codebase into compliance without breaking what runs:

1. **Refactor queue handlers** in `python/src/queue_worker.py` from stubs to real
   implementations that advance the symbol state machine.
2. **Move price/indicator logic** out of standalone scripts into `python/src/` services
   with a single entrypoint script that calls them.
3. **Centralize logging bootstrap** in one module imported first by every entrypoint.
4. **Add state columns** to `symbol_master` and migrate existing symbols to
   `analysis_eligible` where prices and indicators exist, `pending_backfill` otherwise.
5. **Wire event producers** from PHP controllers and `ingest_screener_symbols.py`
   so the waterfall is: screener/transaction → event → state machine → price → TA → analysis.
6. **Keep `orchestrator.py` intact** but add a guard: skip symbols not in
   `analysis_eligible` state.

---

## 10. Enforcement

- Every PR must state which layer(s) it touches and why.
- New modules must include docstrings stating layer assignment and event types
  produced/consumed.
- Reviews must verify: no basicConfig in library code, no direct cross-layer calls,
  tests updated for new state transitions.

This document is living. Update it when new layers, event types, or conventions are
introduced.
