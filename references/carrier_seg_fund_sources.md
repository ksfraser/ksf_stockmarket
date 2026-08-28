# Carrier Segregated Fund Data Sources (working map)

Authoritative reference for where each carrier's **annual (calendar-year) returns** and
**investment minimums** come from. Updated as each carrier is scraped. Goal: never re-search
a URL twice.

## Global conventions
- **Target field:** `fund_series.yr_2019 .. yr_2025` (calendar-year total returns, stored as
  **PERCENTAGES as REAL** — e.g. `11.3`, NOT `0.113`; do NOT divide by 100). `mer` is likewise a percent.
- **Volatility needs** ≥4 annual years per fund AND ≥10 series covering a benchmark year
  (guard in `scripts/seg_fund_filters.py`: `MIN_YEARS=4`, `MIN_YR_COVERAGE=10`).
- **Disk rule (user, 2026-08):** download PDFs → `pdftotext` → extract → `rm` immediately.
  Prefer API / portal DOM scrape over PDFs wherever possible. No PDF corpus accumulates.
- **Local DB:** `/root/.hermes/cache/seg_funds.db`. Carriers: 1 Manulife, 2 RBC Ins,
  3 BMO Ins, 4 Canada Life, 5 iA, 6 SSQ, 7 Empire Life, 8 Humania, 9 ivari,
  10 Equitable, 11 Forresters, 12 VMO, 13 Sun Life.
- **DB creds / prod host** in `/tmp/dbenv.sh` (local IP `192.168.1.102`; prod `ksfraser.ca`).

---

## DONE

### BMO Insurance (carrier_id=3) ✅
- **Source:** Lipper portal `https://digital.lipperweb.com/bmoinsurance/list?lang=en`
- **Method:** browser DOM scrape (3 pages; pagination via bare `<div>` — use
  `browser_console` XPath count of `//div[.//a[contains(@href,'/bmo/')]]`, not `<tr>`).
- **Data:** 292 funds, calendar 2019–2025.
- **Seeder:** `scripts/seed_bmo_local.py` (joins prod `seg_funds` metadata + scraped returns
  into local SQLite).
- **Notes:** prod MariaDB has BMO metadata; local seeds from there. 240/292 series got annual.

### Empire Life (carrier_id=7) ✅
- **Source API:** `https://funds.empire.ca/seg-funds/api/list?searchTerm=&sortProperty=fundName&sortDirection=asc&locale=en-US`
- **Referer:** `https://www.empire.ca/funds/discontinued/class-segs`
- **Method:** `curl` JSON (1.47 MB) → `scripts/seed_empire_local.py`. 544 Class-Seg funds,
  calendar **2018–2025**. `entityId` e.g. `ABON-a`; per-fund `2018`..`2025` floats;
  `relatedResources[].documentId` = `profile-pdfs/<id>-en-US.pdf`, `fundfacts/<id>-en-US.pdf`.
- **Seeder:** `scripts/seed_empire_local.py` (upsert funds + fund_series, carrier_id=7).
- **Notes:** NO PDFs (API). Temp JSON `/tmp/empire_list.json` deleted after seeding.

### Canada Life (carrier_id=4) ✅ — Fundata shelf added separately
- **Source:** `https://canadalifemutualfunds.fundata.com/Default.aspx` (Fundata, server-rendered
  calendar-year "Performance" tab — no API/embedded JSON).
- **Method:** `curl` page HTML (3 MB) → `scripts/parse_canada_life_html.py` (bs4) extracts
  566 funds with calendar 2016–2025 + MER into `/tmp/cl_cal.json` →
  `scripts/seed_canada_life_local.py` upserts 566 funds + series (carrier_id=4, 1 fund = 1 series).
  Volatility proxy = underlying fund returns (seg-fund wrapper only subtracts a small insurance MER).
- **Why a separate shelf:** the ~2,280 pre-loaded `CAN …` rows use allocation-code names with NO
  annual-return source, so they were left untouched. The Fundata shelf is a clean comparable dataset
  (538/566 have full 2019–2025). Screen now ranks 4,769 series; 1,064 have relative beta/alpha/corr.
- **Notes:** NO manual transcription (BS4 parse only — manual copy injected garbage earlier).
  Temp HTML + JSON deleted after parse.

### Equitable Life (carrier_id=10) ✅
- **Source:** Equitable Fundata performance page `https://equitablelife.fundata.com/?language=en`
  (server-rendered HTML table — calendar 2019–2025 + MER, no PDFs).
- **Method:** `curl` HTML (≈776 KB) → `scripts/seed_equitable_local.py` (bs4 parse, SELECT-first
  idempotent upsert on `(fund_id, series_code)`). 119 Fundata series seeded; 198 total carrier rows
  (79 carry full 2019–2025 annuals; the balance are prod metadata rows left untouched).
- **Seeder:** `scripts/seed_equitable_local.py`.
- **Notes:** MER scale correct (avg ~2.95%, stored as percent — do NOT divide by 100). Re-runnable
  without duplicates (verified: 0 inserts / 119 updates on re-run). Temp HTML deleted after seeding.

---

## PENDING (status as of last scan)

### Manulife (carrier_id=1) ✅
- **Source (data stream):** the `https://funds.manulife.ca/en-US/profiles/` "Prices & Performance"
  SPA fires `GET /profiles/api/funds/list/en-US/?skip=N&take=1000` (6 pages, TotalItems=5,605).
  All Manulife seg-fund product lines (GIF Select, MPIP, RetirementPlus, Ideal, etc.). Per
  series: `annRet2017`–`annRet2025` (calendar annuals, %), `mer`, `retNav` (NAV), `retYtd`,
  and compound trailing `compM1/3/6`, `compY1/3/5/10`, `compIncep`. `fundServCode` unique per
  series; `fundName` = 412 unique funds.
- **Seeder:** `scripts/seed_manulife_local.py`. Maps `yr_2019..2025←annRet*`, `return_*←comp*`,
  `price←retNav`, `ytd_return←retYtd`, `fund_status←fundStatus`. As-at 2026-07-31.
- **Note:** default page view shows 575 (a filtered subset); the full API is 5,605 series — all
  imported (658 funds / 6,194 series incl. pre-existing prod metadata rows).

### RBC Insurance (carrier_id=2) ✅ (calendar + trailing) / ⏳ MER·NAV·status
- **Source (data stream):** Lipper portal `https://lipper.rbcinsurance.com/rbc/list` renders a
  PUBLIC DataTables endpoint `POST /List/GetResult/` (tabName=CalendarYear/LongTerm, iDisplayLength=154).
  154 funds; calendar years 2016–2025 + trailing 1/3/5/10y/inception per series (symbol = Lipper id).
  **Values are percentages already** (no ×100). Seeded all 154 with yr_2019..yr_2025 AND
  return_1y/3y/5y/10y/incept. Local chromium loads the portal fine (Browserbase was the tier that timed out).
- **Seeders:** `scripts/seed_rbc_local.py` (calendar), `scripts/seed_rbc_trailing.py` (trailing).
- **Pending:** MER / NAV / per-fund Open-Closed status are NOT in the list tabs — they live on each
  fund's profile/PDF page (154 fetches). `fund_series.fund_status` already supports the needed
  vocabulary ("Closed to deposits and switches-in", "Open to switches-in only", etc.); RBC rows are
  currently defaulted to 'Active' until profile-level status is scraped.

### iA Financial (carrier_id=5) ✅
- **Source (data stream):** the `https://ia.ca/funds-performance` Next.js SPA fires
  `GET /api/sites/ia/fund/yield?locale=en-ca&fundType=savings&date=<as-of>` to fill its
  performance table. Replayed via curl → 1.48 MB JSON, **1,423 series** (94 fund
  families). Per series: `lastYearReturn` (2025 calendar annual, %), `netReturnYearToDate`,
  `netUnitValue` (NAV), and trailing `netReturns1Month/3Months/6Months/1Year/3Years/5Years/10Years`.
  (The per-fund `/api/sites/ia/fund?fundId=<uuid>` endpoint only returns metadata + a PDF
  link — not the performance table; the yield endpoint is the real data stream.)
- **Seeder:** `scripts/seed_ia_local.py`. Maps `yr_2025←lastYearReturn`, `return_*←netReturns*`,
  `price←netUnitValue`, `ytd_return←netReturnYearToDate`. Trailing return columns feed the
  screen's return/relative metrics even though only 2025 is a true calendar year.
- **Note:** iA exposes only the 2025 calendar year (not 2019–2024), so calendar-year volatility
  is Unknown for iA series; they still rank on trailing returns (return_1y/3y/5y/10y).

### SSQ / Beneva (carrier_id=6) — 0 local series
- **Source:** `https://www.beneva.ca/en/savings-investments/segregated-funds` is a **marketing
  page** (capital guarantees, portfolios) — NO performance table / data API. The seg-fund
  returns grid is not publicly exposed (headless clicks on the SPA fail). Needs Fund Facts
  PDFs or an advisor/login portal.
- **Status:** blocked — Fund Facts PDFs required (or re-find a performance endpoint).

### Humania (carrier_id=8) — 0 local series
- **Source:** login_required. Needs credentials or Fund Facts PDFs.

### ivari (carrier_id=9) ✅ (roster + trailing via portal; calendar-year 2019–2025 via Fund Facts PDFs)

- **Portal (trailing returns):** `https://rates.ivari.ca/en` ("Net Rates of Return and Prices"),
  ASP.NET MVC form (`frmSelector`) with unobtrusive AJAX. Select *Investment products* +
  *Rates of Return – Seg. Funds* → POST per *RATE code* (`BigRATE, GS2RATE, TIPs, IMAXXRATE,
  _5FLRATE, TGIFRATE, NNIP_rate`) returns **trailing** returns (1/2/3/5/10y/incept) per fund.
  - **Seeder:** `scripts/seed_ivari_local.py` — GET token → GET product list → POST each RATE
    code → parse tablesaw table → upsert `funds` + `fund_series` (carrier_id=9). Maps
    return_1y/3y/5y/10y/incept (no return_2y column → "2 yrs" dropped). Idempotent.
    Seeded **122 funds / 95 series / 89 with return_1y** (as-at 2026-07-31 for BIG/GROWSafe/NN IP).
  - **NOTE:** portal is **trailing-only** — NOT calendar-year. Calendar returns come from Fund Facts.

- **Fund Facts (calendar-year 2019–2025):** ivari publishes one Fund Facts PDF per investment
  product at `https://ivari.ca/files/<CODE>.pdf` (WordPress media; `<CODE>` is the fund code,
  e.g. `USEIN_TGIF` = "ivari U.S. Equity Index GIF"). Discovered via the WP REST media endpoint
  (`/wp-json/wp/v2/media?post=<ffpu_investment_prod id>`, EN only — FR `*_FR` excluded). Page
  HTML/REST are Cloudflare-gated stubs, but `/files/*.pdf` downloads fine via `curl`.
  - **Parse:** `pymupdf` extracts the "Year-by-year returns" chart → years + returns paired in
    descending order (2025…2015). As-at = "as of December 31, YYYY" (most families as-of 2024;
    the base/None family as-of 2025).
  - **Match:** PDF `(family, core-description)` → DB `(family, core-description)`. Family ∈
    {BIG, GS/GS2, GS3, imaxxGIF, NN IP, 5FL, MM, None}; "Class 2" is ignored (same underlying
    fund, different sales-charge series → identical returns). Family-aware so e.g. GS3 returns
    are NOT written into BIG/imaxxGIF rows (they differ materially).
  - **Seeder:** `scripts/seed_ivari_fundfacts_local.py` — idempotent UPDATE of `fund_series`
    `yr_2019…yr_2025` + `as_at_date` for matched fund_ids. **Auto-creates a `DEFAULT` series row**
    for the ~27 funds (mostly GS3/imaxxGIF) the trailing seed left without a `fund_series` row,
    so their calendar data has a home.
  - **Coverage:** **114 / 122 funds** (93%) have 2019–2024; the 22 base/None-family funds also
    have 2025. Gaps (8): **BIG** (15209) & **MM** (15294) have no Fund Facts PDF published; the
    6 **GS/GS2 Class 2** funds (15210/15211/15212/15213/15219/15220) have PDFs but the chart is an
    embedded *image* (empty text layer) → need OCR (ksf-tesseract container, port 8100).

- **Status:** portal pass DONE (roster + trailing); Fund Facts calendar-year pass DONE
  (114/122, 27 series rows auto-created). 8 funds pending (2 no-PDF, 6 OCR).

### Forresters (carrier_id=11) — 0 local series
- **Listed source** `https://funds.cifinancial.com/en/funds/segregated/` returns HTTP 400;
  CI Financial does not expose a `fundata.com` subdomain. Re-find the source or use
  Fund Facts PDFs.

### VMO (carrier_id=12) — 0 local series
- **Source:** login_required. Needs credentials or Fund Facts PDFs.

### Sun Life (carrier_id=13) ✅
- **Source (embedded JSON):** `https://funds.sunlifeglobalinvestments.com/seg-funds-list` embeds
  `window.dfSb.__PRELOADED_STATES__['root'].data.webProfiles` (566 series, all `isInactive=false`
  → all current/active). Per series: `overview.mer`, `performance.compoundPerformance`
  (p1mo/p3mo/p6mo/pytd/p1yr/p3yr/p5yr/p10yr — DECIMALS, ×100 for DB), `dailyPerformance.navPS` (NAV).
- **Seeder:** `scripts/seed_sunlife_local.py`. **SCALE FIX:** Sun Life stores returns/MER as
  decimals (0.0868 = 8.68%) — multiplied by 100 to match the DB percent convention (iA/Manulife
  were already percentages). No calendar-year (2019–2025) fields on this page → yr_* NULL
  (calendar volatility Unknown; trailing returns still captured).
- **Scope:** active/current only (all 566 are active).
