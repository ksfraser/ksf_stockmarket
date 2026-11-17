# Intraday Alert Detection Run — Final Report

**Run command:** `cd /root/Documents/stockmarket/php/stockmarket-app && /usr/bin/python3.10 detection_triggers.py --sqlite`

**Run start (UTC):** 2026-10-15T16:18:40
**Run end (UTC):** 2026-10-15T16:43:51
**Wall clock (min):** 22.9

## 1. Market-hours gate
The app-root shim (`detection_triggers.py` at `stockmarket-app/`) has **no `_market_open()` gate**; it scans its hardcoded `KNOWN_TSX` + `KNOWN_US` watchlist (70 symbols) unconditionally.

## 2. Alert counts by type (this run window, `created_at >= 2026-10-15T16:18:40`)

| alert_type | count |
|---|---|
| (none this run) | 0 |

## 3. Final store state (after checkpoint)

- `alert_queue` total: 34 (pre-run 33)
- `alert_queue` non-null `created_at`: 28; null: 6
- `price_intraday`: 13409
- SQLite target: `/root/Documents/stockmarket/php/stockmarket-app/data/analysis_results.db`
- MariaDB writes: **none**

## 4. Errors / notices

- HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: XIT"}}}
- HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: XIT"}}}
- HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: XIT"}}}
- HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: XIT"}}}
- HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NPI"}}}
- HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NPI"}}}
- HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NPI"}}}
- HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: NPI"}}}

## 5. Store note

Ephemeral SQLite write routing confirmed: no MariaDB writes for this `--sqlite` run.
