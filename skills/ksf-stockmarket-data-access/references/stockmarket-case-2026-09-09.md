# Per-entity price storage — stockmarket case, 2026-09-09

Session that produced the `per-entity-price-storage` skill. Captures the
verified-live numbers, the exchange inventory, and the documentation-alignment
pattern (requirements pack + architecture note section + RTM rows written
together) so a future session does not recompute or retype the same picture.

## Verified numbers (live DB, 2026-09-09/10, ksfraser_stock_market on ksfraser.ca)

**These are the real numbers at the time the price-storage refactor work began.**
Earlier entries in this file (~187 MB total, `stockprices` at ~93%) were from a
prior session and were stale by the time the refactor was dug into. Re-verify live
before any size-related decision — never trust a DB size number from memory or a
prior session.

Live sizes at time of work (2026-09-09/10):

| Table | Rows | Total size | % of 11.48 GB DB |
|---|---|---|---|
| **`indicators_json`** | 709,934 | **8,302 MB (8.3 GB)** | **71%** |
| `stockprices` | 10,521,359 | 2,044 MB (2.0 GB) | 17% |
| `indicators` | 951,951 | 1,056 MB (1.0 GB) | 9% |
| `ta_indicators` | 56,858 | 124 MB | 1% |
| `strategy_pipeline_results` | 251,892 | 102 MB | 1% |
| everything else combined | — | ~230 MB | 2% |
| **TOTAL** | — | **~11,755 MB (11.48 GB)** | 100% |

### The trap this session hit

`stockprices` is no longer the dominant table. `indicators_json` (a JSON-blob
per-symbol-per-date indicator snapshot) is 71% of the DB, and `stockprices` is
only 17%. A stockprices-only refactor (BR-15) addresses 17% of the problem; the
indicators are where the real tonnage is. **Before concluding "stockprices is the
size problem," run a full size report and sort descending.** The obvious suspect
may have been overtaken by something less visible.

### Indicators overlap (actionable)

`indicators` (columnar, 1 GB) and `indicators_json` (JSON blob, 8.3 GB) store
largely the same per-symbol-per-date indicator set. The columnar table is the
efficient layout; the JSON blob is ~8× larger for the same information. Both are
read the same way (latest row per symbol, or last 60 days). Before doing any
indicators-side storage work, verify whether `indicators_json` is fully redundant
with `indicators` — if redundant, dropping it is a 7+ GB win and the
indicators-side equivalent of the stockprices refactor.

### Usage pattern that matters for storage decisions

- **UI detail pages** read latest `indicators_json` row + last 60 for one symbol
  (renders ATR, SMA200, RSI, MACD, BB individually).
- **Portfolio display** joins `indicators_json` per holding for a display column.
- **Strategy scoring** (PHP `Strategy/*` classes) scores the latest snapshot — not
  historical rows from these tables.
- **Advisor backtests / Python agents** (GA/NN/RL) read **separate small tables**
  (`daily_indicators`, `daily_tier2`, `ta_values`) — NOT `indicators_json`.
- `indicators_json`/`indicators` are **not** the backtest source.

This means the indicators-side storage decision is about UI-snapshot retention,
not backtest history. If only the latest + recent 60 days are needed, full history
per symbol is over-provisioned.

## Exchange inventory (live `symbol_master.exchange` counts)

| exchange value | active symbols | Routes to |
|---|---|---|
| NASDAQ | 2,691 | ksfraser_sm_nasdaq |
| TSX | 880 | ksfraser_sm_tsx |
| NYSE | 176 | ksfraser_sm_nyse |
| YHD | 97 | (minor — confirm routing; not a primary DB today) |
| TOR | 24 | (minor — confirm routing; not a primary DB today) |
| TSX.V | 15 | ksfraser_sm_v |
| OTC | 8 | (minor — confirm routing; not a primary DB today) |
| NYQ | 8 | ksfraser_sm_nyse (NYSE + NYSE-American) |
| PCX | 7 | (minor — confirm routing; not a primary DB today) |
| NCT, EUR, NGM, LSE, CNY, GBP, USD, ASE, NSE, INDEX, NCM, BTS, HKG, CAD | 1 each | (minor — confirm routing; not a primary DB today) |
| <blank> | 5 (4 + 1) | (minor — confirm routing; not a primary DB today) |

The session chose 6 primary exchange databases plus a `_other` fallback for
minor/uncommon codes. CSE and AMEX have 0 active symbols today but are created
anyway for future-proofing.

## Documentation alignment pattern used

Three artifacts were written together in one pass:

1. `docs/requirements/BR-15-stock-price-storage-refactor.md` — business
   requirement (rationale, acceptance criteria, risks, related).
2. `docs/requirements/FR-15-stock-price-storage-refactor.md` — functional
   requirement (affected components, schema, routing/ingestion contract, tests).
3. `docs/requirements/UC-15-stock-price-storage-refactor.md` — use cases
   (UC-15a migration, UC-15b nightly dual-write, UC-15c routing validation,
   UC-15d window recalculation, UC-15e backtest audit).
4. `docs/architecture/stock-filter-engine.md` §7c — architecture-note section
   with the verified-live picture, routing model, schema, ingestion contract,
   window cadence, integration points, and migration sequence.
5. `docs/requirements/traceability-matrix.md` — one summary RTM row for BR-15
   plus one row per UC (UC-15a through UC-15e).

The RTM rows are the part that is easiest to forget if left as a separate later
task — write them in the same pass as the requirements and the architecture note.

## Dispatcher data dependencies (cross-check for the nightly-pipeline skill)

The Zacks EPS-revision signal dispatcher now reads from and writes to three
tables:

- `zacks_screener_cache` — top-5 bullish/bearish signal selection from the
  per-symbol latest EPS-change snapshot (cache of the scraper's scraped EPS
  data keyed by `zacks_screen_id` + `symbol`).
- `alert_queue` — one row inserted per dispatched signal
  (`alert_type='zacks_eps_revision'`, `severity='high'`, `status='pending'`,
  JSON payload).
- `system_settings` — Discord webhook URL
  (`setting_key='discord_alert_webhook'`).

The RTM row for UC-14c names all three. If the dispatcher is run, verified, or
debugged, treat `zacks_screener_cache` as part of the data contract, not an
implementation detail.
