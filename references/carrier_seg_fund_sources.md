# Carrier Segregated Fund Data Sources (working map)

Authoritative reference for where each carrier's **annual (calendar-year) returns** and
**investment minimums** come from. Updated as each carrier is scraped. Goal: never re-search
a URL twice.

## Global conventions
- **Target field:** `fund_series.yr_2019 .. yr_2025` (calendar-year total returns, decimals).
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

---

## PENDING (status as of last scan)

### Manulife (carrier_id=1) — 589 local series, 0 annual
- **Source portal:** `https://funds.manulife.ca/en-US/profiles/` (SPA — calendar-year NOT in DOM)
- **Real annual source:** Fund Facts PDFs (download→parse→rm). 142 GIF funds via Manulife SPA.

### RBC Insurance (carrier_id=2) — 0 local series
- **Source portal:** `https://lipper.rbcinsurance.com/rbc/list` (BLOCKED/timeouts on Browserbase)
- **Have:** email-gateway CSV `/home/kevin/Documents/rbc_gif_funds_2026-08-17.csv` (34 funds,
  trailing-only, no annual). Needs user forward or RBC Fund Facts PDFs.

### iA Financial (carrier_id=5) — 0 local series
- **Source:** `https://ia.ca/funds-performance` — investigate (Fundata-style?).

### SSQ / Beneva (carrier_id=6) — 0 local series
- **Source:** `https://www.beneva.ca/en/savings-investments/segregated-funds` (non-Lipper SPA;
  headless clicks fail — MUI menuitems "Could not compute box model"). Fallback `web_search`
  or Fund Facts PDFs.

### Humania (carrier_id=8) — 0 local series
- **Source:** login_required. Needs credentials or Fund Facts PDFs.

### ivari (carrier_id=9) — 0 local series
- **Source:** `https://rates.ivari.ca/EN/rates/default.asp?Lang=EN&ShowList=IP` — investigate.

### Equitable Life (carrier_id=10) — 79 local series, 0 annual
- **Source:** `https://www.equitable.ca/segregated-funds` (Fundata EGIF — trailing-only,
  NO calendar-year in portal). Real annual = Fund Facts PDFs (download→parse→rm).

### Forresters (carrier_id=11) — 0 local series
- **Source:** `https://funds.cifinancial.com/en/funds/segregated/` (CI Financial / Fundata-style)
  — investigate for calendar-year.

### VMO (carrier_id=12) — 0 local series
- **Source:** login_required. Needs credentials or Fund Facts PDFs.

### Sun Life (carrier_id=13) — 202 local series, 0 annual
- **Source:** `https://funds.sunlifeglobalinvestments.com/seg-funds-list` (799 pre-loaded
  trailing in prod). Real annual = Fund Facts PDFs / email forward (download→parse→rm).
