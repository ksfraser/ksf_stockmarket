#!/usr/bin/env python3
"""
Seed Canada Life seg-fund shelf (Fundata) into the LOCAL analysis store.

Source: https://canadalifemutualfunds.fundata.com/Default.aspx?language=en
Data extracted server-side from the page HTML (calendar-year "Performance" tab)
into /tmp/cl_cal.json by scripts/parse_canada_life_html.py -- no manual copy.

Each Fundata row already includes its share class (e.g. "...Advanced Portfolio A"),
so we store 1 fund + 1 series per row (fund_name = full name, series_code = class).
Upsert is idempotent (SELECT-first) so the script is re-runnable.

NOTE: The local DB already holds ~2,240 Canada Life series under a *different*
naming convention ("CAN Canadian Core Bond 100/100", allocation-code based) with
no annual-return source identified. Those opaque rows are left untouched; this
seeder adds the well-sourced Fundata shelf as a separate, comparable dataset.
Returns are the underlying fund calendar-year figures (volatility proxy for the
seg-fund wrapper, which subtracts a small insurance MER).
"""
import os, re, sqlite3, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LOCAL_DB = os.environ.get("SEG_FUNDS_DB", "/root/.hermes/cache/seg_funds.db")
CL_CARRIER_ID = 4
JSON_SRC = "/tmp/cl_cal.json"
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

MARKERS = "†‡*#§\u2020\u2021\u2022"


def clean(name):
    return re.sub(r"[" + re.escape(MARKERS) + r"]", "", name).strip()


def series_code(name):
    n = clean(name)
    if re.search(r"\s-\s", n):
        return re.split(r"\s-\s", n)[-1].strip() or "BASE"
    parts = n.rsplit(" ", 1)
    return parts[1] if len(parts) > 1 else "BASE"


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


def to_num(v):
    v = (v or "").strip()
    if v in ("", "-"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main():
    rows = json.load(open(JSON_SRC))
    print(f"loaded {len(rows)} Canada Life rows from {JSON_SRC}")
    con = sqlite3.connect(LOCAL_DB)
    cur = con.cursor()
    inserted = updated = skipped = 0
    for r in rows:
        raw = r["name"]
        name = clean(raw)
        if not name:
            skipped += 1
            continue
        code = series_code(raw)
        yr = [to_num(r.get(f"yr_{y}")) for y in YEARS]
        mer = to_num(r.get("mer"))
        # upsert fund
        cur.execute("SELECT fund_id FROM funds WHERE carrier_id=? AND fund_name=?",
                    (CL_CARRIER_ID, name))
        row = cur.fetchone()
        if row:
            fid = row[0]
        else:
            cur.execute(
                "INSERT INTO funds (family_id, carrier_id, fund_name, fund_name_clean, category, is_active) "
                "VALUES (0,?,?,?,?,1)",
                (CL_CARRIER_ID, name, name, category(name)),
            )
            fid = cur.lastrowid
            inserted += 1
        # upsert series
        cur.execute("SELECT series_id FROM fund_series WHERE fund_id=? AND series_code=?",
                    (fid, code))
        srow = cur.fetchone()
        if srow:
            cur.execute(
                "UPDATE fund_series SET yr_2019=?,yr_2020=?,yr_2021=?,yr_2022=?,yr_2023=?,yr_2024=?,yr_2025=?,"
                "mer=?,series_name=?,updated_at=datetime('now') WHERE series_id=?",
                (yr[0], yr[1], yr[2], yr[3], yr[4], yr[5], yr[6], mer, name, srow[0]),
            )
            updated += 1
        else:
            cur.execute(
                "INSERT INTO fund_series (fund_id, series_code, series_name, load_type, mer, "
                "yr_2019, yr_2020, yr_2021, yr_2022, yr_2023, yr_2024, yr_2025) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (fid, code, name, None, mer, yr[0], yr[1], yr[2], yr[3], yr[4], yr[5], yr[6]),
            )
    con.commit()
    cur.execute(
        "SELECT COUNT(*) FROM fund_series fs JOIN funds f ON f.fund_id=fs.fund_id "
        "WHERE f.carrier_id=? AND yr_2025 IS NOT NULL", (CL_CARRIER_ID,))
    have = cur.fetchone()[0]
    con.close()
    print(f"inserted {inserted} new funds, updated {updated} series, skipped {skipped}; "
          f"Canada Life series with yr_2025 populated: {have}")


if __name__ == "__main__":
    main()
