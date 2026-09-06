# FR-11: Seg-Fund Filter Engine

**BABOK v2.0** | **Category:** Functional Requirement | **Parent:** BR-11
**Module:** Segregated Funds
**Author:** KSF | **Status:** Draft | **Date:** 2026-09-04

## Statement
The system shall filter the `seg_funds` list by risk rating, death benefit, maturity
benefit, and 5-bucket return distributions. Filters compose with AND across dimensions
and OR within a dimension's checkboxes.

## Affected Components
- `src/Controller/SegFundsController.php` — extend `listFunds()` to accept new filter
  params; expose `riskDistribution()` and `returnDistribution()` for the UI's 5-bucket
  dropdown.
- `templates/seg_funds.php` — add filter checkboxes; reflect state in URL.
- New helper: `src/Util/SegFundFilter.php` — encapsulates bucket boundary computation
  (NTILE(5) over active universe) and the WHERE-clause builder.

## Filters (additive to existing carrier/category/series/search)
| Dimension        | Param          | Type            | Logic                |
|------------------|----------------|-----------------|----------------------|
| Risk Rating      | `risk_rating`  | CSV (5 values)  | IN (...)             |
| Death Benefit %  | `death_pct`    | CSV (75, 100)   | IN (...)             |
| Maturity Benefit | `mat_pct`      | CSV (75, 100)   | IN (...)             |
| 1Y Bucket        | `bucket_1y`    | enum            | NTILE(5) lookup      |
| 5Y Bucket        | `bucket_5y`    | enum            | NTILE(5) lookup      |
| 10Y Bucket       | `bucket_10y`   | enum            | NTILE(5) lookup      |
| YTD Bucket       | `bucket_ytd`   | enum            | NTILE(5) lookup      |

## Bucket boundaries
Computed live per request as:
```sql
WITH ranked AS (
  SELECT id, return_5yr,
         NTILE(5) OVER (ORDER BY return_5yr ASC) AS q
  FROM seg_funds WHERE is_active=1 AND return_5yr IS NOT NULL
)
SELECT q, MIN(return_5yr), MAX(return_5yr), COUNT(*) FROM ranked GROUP BY q ORDER BY q;
```
The 5 quintile ranges are returned to the UI as labels in the dropdown
(`<5%`, `5–9%`, `10–15%`, `16–20%`, `≥20%`) — labels are example values, real ranges come
from the live distribution.

## DB schema (preconditions)
- `seg_funds.risk_rating` ENUM('Low','Low-Med','Medium','Med-High','High') NULL.
- `seg_funds.death_benefit_pct` TINYINT NULL.
- `seg_funds.maturity_benefit_pct` TINYINT NULL.
- All three are populated by a backfill migration (see `sql/migrate_segfund_filters.sql`).

## Tests / Validation
- `?action=seg_funds&risk=High` — verify result count drops to high-rated funds only.
- `?action=seg_funds&death_pct=100` — verify only 100/100 series + Optimal 100/100
  appear.
- `?action=seg_funds&bucket_5y=10-15` — verify result count is ~20% of total.
- Combined `?action=seg_funds&risk=Medium&death_pct=75&bucket_5y=10-15` — verify AND
  semantics.
- All four return HTTP 200 with non-empty body.

## Risks
- Bucket labels in URLs are example values; the actual numeric boundaries are
  per-request. Document this in the UI tooltip ("ranges computed from current
  distribution; reload to refresh").
- `risk_rating` backfill must default unmapped funds to 'Medium' to avoid orphan
  empty-filter behaviour.

## Related
- BR-11, BR-12
- FR-12 (Personal Screens — same filter engine is reused)
