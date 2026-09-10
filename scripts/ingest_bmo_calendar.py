#!/usr/bin/env python3
"""
Ingest BMO Lipper Calendar-Year Returns (scraped from digital.lipperweb.com/bmoinsurance)
into the LOCAL seg_funds store (fund_series.yr_2019..yr_2025).

Source files: data/bmo_calendar_2026_page{1,2,3}.txt  (pipe-delimited:
fund_name | 2025 | 2024 | 2023 | 2022 | 2021 | 2020 | 2019 | 2018 | 2017 | 2016)
"-" = N/A.

The local schema only stores yr_2019..yr_2025, so 2016/2017/2018 are dropped.

Matching: by fund_name (exact, then normalized lower/collapse-space fallback).
Reports matched / unmatched so gaps are visible.
"""
import os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
DB_PATH = os.environ.get("SEG_FUNDS_DB", "/root/.hermes/cache/seg_funds.db")
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
PAGES = [os.path.join(DATA, f"bmo_calendar_2026_page{i}.txt") for i in (1, 2, 3)]


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def load_portal():
    data = {}
    for p in PAGES:
        if not os.path.exists(p):
            print("WARN missing", p, file=sys.stderr)
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|")
                name = parts[0].strip()
                vals = parts[1:]
                rec = {}
                # file columns: 2025,2024,2023,2022,2021,2020,2019,2018,2017,2016
                file_years = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]
                for yr, v in zip(file_years, vals):
                    if yr not in YEARS:
                        continue
                    v = v.strip()
                    rec[yr] = None if v in ("", "-") else float(v)
                data[name] = rec
    return data


def main():
    portal = load_portal()
    print(f"portal funds loaded: {len(portal)}")
    if not os.path.exists(DB_PATH):
        print("DB not found:", DB_PATH)
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # find BMO carrier id
    cur.execute("SELECT carrier_id, name FROM carriers WHERE lower(name) LIKE '%bmo%'")
    carriers = cur.fetchall()
    print("BMO carriers:", carriers)
    if not carriers:
        print("no BMO carrier row")
        sys.exit(1)
    bmo_ids = [c[0] for c in carriers]
    ph = ",".join("?" * len(bmo_ids))
    cur.execute(
        f"""SELECT fs.series_id, fs.series_name, f.fund_name, fs.series_code
            FROM fund_series fs JOIN funds f ON f.fund_id=fs.fund_id
            WHERE f.carrier_id IN ({ph})""",
        bmo_ids,
    )
    rows = cur.fetchall()
    print(f"local BMO series: {len(rows)}")

    by_series = {norm(r[1]): r for r in rows}
    by_fund = {norm(r[2]): r for r in rows}

    matched = 0
    unmatched = []
    updated = 0
    for name, rec in portal.items():
        row = by_series.get(norm(name)) or by_fund.get(norm(name))
        if not row:
            unmatched.append(name)
            continue
        matched += 1
        sid = row[0]
        sets = []
        params = []
        for yr in YEARS:
            sets.append(f"yr_{yr}=?")
            params.append(rec.get(yr))
        params.append(sid)
        cur.execute(f"UPDATE fund_series SET {','.join(sets)} WHERE series_id=?", params)
        updated += 1

    con.commit()
    con.close()
    print(f"matched: {matched}  updated: {updated}  unmatched: {len(unmatched)}")
    if unmatched:
        print("--- UNMATCHED (first 30) ---")
        for u in unmatched[:30]:
            print("  ", u)


if __name__ == "__main__":
    main()
