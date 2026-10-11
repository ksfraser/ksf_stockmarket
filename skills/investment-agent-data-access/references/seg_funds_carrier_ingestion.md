# Ingesting carrier fund-booklet PDFs into seg_funds.db

Recurring task: Kevin forwards carrier segregated-fund booklets (Manulife, BMO,
Empire Life, …) as PDFs; load them into `seg_funds.db` for the stockmarket app /
investment screening. This DB is SEPARATE from the investment-agent repo's
guarded `ANALYTICS_DB` (analysis_results.db) — ingestion scripts live in
`/root/.hermes/cache/` and are NOT subject to that repo's
`guard_standardized_access` (which blocks raw `sqlite3.connect`). Keep them there.

## Canonical location
- `/root/.hermes/cache/seg_funds.db` — the live working DB (carriers, funds,
  fund_series, fund_codes, fund_families).
- Do NOT use `/root/seg_funds.db` — it is an EMPTY decoy.
- `search_files` skips hidden dirs, so `/root/.hermes/...` won't show in a
  repo-root search; query SQLite directly.

## Schema (key tables)
- `carriers` (carrier_id, name, short_name, scrape_url…). Empire Life =
  **carrier_id 7** (already present — do NOT recreate). Manulife = 1.
- `funds` (fund_id, carrier_id, fund_name, category, risk_rating,
  inception_date). UNIQUE(carrier_id, fund_name).
- `fund_series` (series_id, fund_id, series_code [e.g. 'A','FE','NLCB2'], mer,
  msf, return_1m..10y, ytd_return, as_at_date). UNIQUE(fund_id, series_code).
- `fund_codes` (code_id, fund_id, carrier_id, code_type, code_value,
  series_code). UNIQUE(carrier_id, code_type, code_value, series_code).

## PDF → DB workflow (proven on Empire Life fund-facts/fund-profiles booklets)
1. `pdftotext -layout in.pdf out.txt` (huge text — DO NOT read the whole file
   into context; parse in Python).
2. Split on form-feed `\f` into per-page chunks; collapse each page's
   whitespace: `pg1 = re.sub(r'\s+',' ', pg)`.
3. Extract fund name with a BRAND-PREFIXED regex
   (e.g. `(Empire Life|Concordia)…(Fund|GIF|Pool|Portfolio|Index|Trust)\b
   (?:\s*[—-]\s*Class\s+([A-Z]))?`). Require the brand prefix — every real
   fund starts with it.
4. Extract fields: `MER\s*:\s*([\d.]+)`, `Management Fee\s*:\s*([\d.]+)`,
   `Inception Date\s*:\s*(...)`, `Asset class\s*:\s*(...)` (stop the
   asset-class capture at the next field marker — Management Fee/Fund
   Manager/Net Assets — or it greedily bleeds into "Investment value").
5. Returns: find `"Compound Returns"`, then take the `%`-values AFTER it
   (avoids grabbing Top-10-Holdings weights that appear earlier on the page).
   Layout: 1m,3m,6m,YTD,1y,3y,5y,10y,psi → map to return_1m/3m/6m/1y/3y/5y/10y
   and ytd_return.
6. Fund CODES: per fund there is a "Fund codes" table mapping Series/Class →
   contract codes. Empire Life codes are **`ECF`**-prefixed (e.g. `ECF13003`,
   `ECF13203`, `ECF13303`, `ECF13503` = Front-end/Low-load/No-load/DSC for
   Class M). Earlier Manulife MPIP codes are **`MPS`**-prefixed (`MPS4444`,
   `MPS4456` = Fidelity Global Balanced FE/NLCB2). Pull all `ECF[0-9A-Za-z-]+`
   tokens on the page; insert as `fund_codes` (code_type='fund_code').
7. INSERT with `INSERT OR IGNORE`; dedupe funds by name, series by
   (name, class). Track a `current_fund` across pages so continuation-page data
   (codes/MER/returns) attributes to the right fund (funds span multiple `\f`
   pages).

## Pitfalls (hit and fixed on Empire Life)
- **Multi-line fund names** ("Empire Life American Growth\nGIF - Class K") —
  collapse whitespace per page BEFORE regexing; anchor to the brand prefix.
  Without this, "GIF" alone gets captured as a fund name.
- **Disclaimer/junk records** — footer sentences ("Empire Life Insurance
  Company. Policies are issued by… Any amount that is allocated to a
  Segregated Fund") START with the brand prefix AND END in "Segregated Fund",
  so they match a naive name regex. Filter out names containing
  "Segregated Fund", "Information Folder", "Policies are issued", "endeavour",
  "inaccuracies", "Underlying", "Top 10", "Fundata", "Mutual Fund",
  "Secondary", or `len(name) > 80`.
- **Empty decoy DB** at `/root/seg_funds.db` — always target
  `/root/.hermes/cache/seg_funds.db`.
- **Idempotency** — reruns must not duplicate; use `INSERT OR IGNORE` + dedupe
  keys.

## Reusable artifact
Paradigm loader: `/root/.hermes/cache/load_empire.py` (brand prefixes + ECF
code regex are the only carrier-specific bits — swap them to onboard the next
carrier). Result of the Empire Life load: 73 funds, 217 series, 1,569 ECF
codes, 0 junk; portable seed at `/root/.hermes/cache/empire_life_seed.sql`
(1,859 INSERTs).
