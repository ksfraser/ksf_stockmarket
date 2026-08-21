#!/usr/bin/env python3
"""
Seed Empire Life Class Segregated Funds (544) into the LOCAL analysis store from the
funds.empire.ca Prices & Performance API, which returns calendar-year returns per fund
(2018-2025) directly -- no PDF parsing required.

API: /seg-funds/api/list?searchTerm=&sortProperty=fundName&sortDirection=asc&locale=en-US
Each row: fundName, entityId, calendar returns keyed by year (2018..2025), relatedResources
(Fund Profile / Fund Facts PDF documentIds -- kept for later minimum extraction).

Local store: carrier_id=7 (Empire Life). Upserts funds + fund_series (yr_2019..2025).
Existing pre-loaded Empire rows are preserved; Class Segs are inserted/updated by name+entityId.
"""
import os, re, sqlite3, sys, json, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LOCAL_DB = os.environ.get("SEG_FUNDS_DB", "/root/.hermes/cache/seg_funds.db")
EMPIRE_CARRIER_ID = 7
API = ("https://funds.empire.ca/seg-funds/api/list?searchTerm=&sortProperty=fundName"
       "&sortDirection=asc&locale=en-US")
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]


def fetch_api():
    req = urllib.request.Request(API, headers={
        "Referer": "https://www.empire.ca/funds/discontinued/class-segs",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def category(name):
    n = name.lower()
    if any(k in n for k in ("bond", "fixed income", "mortgage", "income")):
        return "Fixed Income"
    if any(k in n for k in ("money", "cash", "treasury", "savings")):
        return "Money Market"
    if any(k in n for k in ("balanced", "allocation", "portfolio", "conservative", "moderate")):
        return "Balanced"
    if any(k in n for k in ("equity", "growth", "stock", "global", "dividend", "index", "focus")):
        return "Equity"
    return "Other"


def guarantee(name):
    m = re.search(r"(\d{2})/(\d{2})", name)
    return int(m.group(1)) if m else None


def min_invest(name):
    n = name.lower()
    if "class f" in n or "privilege" in n or "plus" in n or "advisor" in n:
        return 100000
    return 0


def main():
    data = fetch_api()
    funds = data.get("data", [])
    print(f"API returned {len(funds)} Empire Class Segs")
    con = sqlite3.connect(LOCAL_DB)
    cur = con.cursor()
    inserted = updated = 0
    for f in funds:
        name = f["fundName"]
        rets = {int(k): v for k, v in f.items() if k.isdigit() and isinstance(v, (int, float))}
        entity = f.get("entityId")
        cur.execute("SELECT fund_id FROM funds WHERE carrier_id=? AND fund_name=?", (EMPIRE_CARRIER_ID, name))
        row = cur.fetchone()
        if row:
            fid = row[0]
        else:
            cur.execute(
                "INSERT INTO funds (family_id, carrier_id, fund_name, fund_name_clean, category, is_active) "
                "VALUES (0,?,?,?,?,1)",
                (EMPIRE_CARRIER_ID, name, name, category(name)),
            )
            fid = cur.lastrowid
            inserted += 1
        yr = [rets.get(y) for y in YEARS]
        gua = guarantee(name)
        cur.execute("SELECT series_id FROM fund_series WHERE fund_id=? AND series_code=?", (fid, entity))
        srow = cur.fetchone()
        if srow:
            cur.execute(
                "UPDATE fund_series SET yr_2019=?,yr_2020=?,yr_2021=?,yr_2022=?,yr_2023=?,yr_2024=?,yr_2025=?,"
                "guarantee_pct=? WHERE series_id=?",
                (yr[0], yr[1], yr[2], yr[3], yr[4], yr[5], yr[6], gua, srow[0]),
            )
            updated += 1
        else:
            cur.execute(
                "INSERT INTO fund_series (fund_id, series_code, series_name, load_type, mer, guarantee_pct, "
                "yr_2019, yr_2020, yr_2021, yr_2022, yr_2023, yr_2024, yr_2025) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (fid, entity, name, None, None, gua,
                 yr[0], yr[1], yr[2], yr[3], yr[4], yr[5], yr[6]),
            )
    con.commit()
    cur.execute("SELECT COUNT(*) FROM fund_series fs JOIN funds f ON f.fund_id=fs.fund_id "
                "WHERE f.carrier_id=? AND yr_2025 IS NOT NULL", (EMPIRE_CARRIER_ID,))
    have = cur.fetchone()[0]
    con.close()
    print(f"inserted {inserted} new funds, updated {updated} series; Empire series with yr_2025 populated: {have}")


if __name__ == "__main__":
    main()
