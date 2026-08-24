#!/usr/bin/env python3
"""
Seed RBC Insurance segregated-fund CALENDAR-YEAR returns into the LOCAL SQLite DB
(/root/.hermes/cache/seg_funds.db) from the Lipper portal's data stream.

Source: https://lipper.rbcinsurance.com/rbc/list  (tab "Calendar Year")
The grid is rendered by a public DataTables endpoint:
    POST https://lipper.rbcinsurance.com/List/GetResult/
    body includes tabName=CalendarYear, iDisplayLength=154
Response JSON: {iTotalRecords, aaData:[ [checkboxHtml, nameLinkHtml, "2016", .. "2025", comm, actions], ... ]}

Capture:
    curl -s -X POST "https://lipper.rbcinsurance.com/List/GetResult/" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      --data @/tmp/rbc_body.txt -o /tmp/rbc_calyear.json
    # /tmp/rbc_body.txt = the tabName=CalendarYear form body (iDisplayLength=154)

Column mapping (verified against rendered table headers
  ["SELECT","FUND NAME","2016","2017","2018","2019","2020","2021","2022","2023","2024","2025","COMM28","ACTION"]):
    row[0]  -> symbol  (id='<digits>' in the checkbox input)
    row[1]  -> fund/series name (text of the <a> link)
    row[5]  -> 2019   (yr_2019)
    row[6]  -> 2020   (yr_2020)
    row[7]  -> 2021   (yr_2021)
    row[8]  -> 2022   (yr_2022)
    row[9]  -> 2023   (yr_2023)
    row[10] -> 2024   (yr_2024)
    row[11] -> 2025   (yr_2025)
  Values are PERCENTAGES already (13.12 = 13.12%) -> stored as-is (no x100).

SCOPE: all 154 listed funds are current/active (portal "As of July 31, 2026").

TODO (follow-up, endpoint is public): seed trailing returns (1yr/3yr/5yr/10yr) and
MER/NAV from the "Long Term" / "Fund Details" tabs (capture their GetResult sColumns,
curl, merge by symbol). This seeder sets only calendar years; trailing/MER stay NULL
until that follow-up runs (UPDATE will fill them idempotently).

Idempotent: series upserted SELECT-first on (fund_id, series_code).

Usage:
    python3 scripts/seed_rbc_local.py /tmp/rbc_calyear.json
    python3 scripts/seed_rbc_local.py /tmp/rbc_calyear.json --dry-run
"""
import sys
import json
import re
import sqlite3

DB_PATH = "/root/.hermes/cache/seg_funds.db"
CARRIER_ID = 2  # RBC Insurance (per references/carrier_seg_fund_sources.md)
AS_AT = "2026-07-31"  # portal "As of: July 31, 2026"


def to_float(v):
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "-", "NA", "N/A", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse(rows):
    out = []
    for r in rows:
        if len(r) < 12:
            continue
        sm = re.search(r"id='(\d+)'", r[0] or "")
        nm = re.search(r"<a[^>]*>([^<]*)</a>", r[1] or "")
        sym = sm.group(1) if sm else None
        name = nm.group(1).strip() if nm else None
        if not sym or not name:
            continue
        out.append({
            "series_code": sym,
            "fund_name": name,
            "series_name": name,
            "yr_2019": to_float(r[5]),
            "yr_2020": to_float(r[6]),
            "yr_2021": to_float(r[7]),
            "yr_2022": to_float(r[8]),
            "yr_2023": to_float(r[9]),
            "yr_2024": to_float(r[10]),
            "yr_2025": to_float(r[11]),
        })
    return out


def extract(json_path):
    with open(json_path, encoding="utf-8") as fh:
        d = json.load(fh)
    return parse(d.get("aaData", []))


def seed(records, dry_run=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n_fund = n_series_ins = n_series_upd = 0
    for r in records:
        cur.execute(
            "INSERT OR IGNORE INTO funds (carrier_id, fund_name) VALUES (?,?)",
            (CARRIER_ID, r["fund_name"]),
        )
        if cur.rowcount:
            n_fund += 1
        cur.execute(
            "SELECT fund_id FROM funds WHERE carrier_id=? AND fund_name=?",
            (CARRIER_ID, r["fund_name"]),
        )
        row = cur.fetchone()
        if not row:
            continue
        fund_id = row[0]
        cur.execute(
            "SELECT series_id FROM fund_series WHERE fund_id=? AND series_code=?",
            (fund_id, r["series_code"]),
        )
        srow = cur.fetchone()
        if srow:
            if not dry_run:
                cur.execute(
                    """UPDATE fund_series SET series_name=?, yr_2019=?, yr_2020=?, yr_2021=?, yr_2022=?,
                       yr_2023=?, yr_2024=?, yr_2025=?, as_at_date=?, fund_status=?, updated_at=datetime('now')
                       WHERE series_id=?""",
                    (r["series_name"], r["yr_2019"], r["yr_2020"], r["yr_2021"], r["yr_2022"],
                     r["yr_2023"], r["yr_2024"], r["yr_2025"], AS_AT, "Active", srow[0]),
                )
            n_series_upd += 1
        else:
            if not dry_run:
                cur.execute(
                    """INSERT INTO fund_series
                       (fund_id, series_code, series_name, yr_2019, yr_2020, yr_2021, yr_2022, yr_2023,
                        yr_2024, yr_2025, as_at_date, fund_status, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    (fund_id, r["series_code"], r["series_name"], r["yr_2019"], r["yr_2020"],
                     r["yr_2021"], r["yr_2022"], r["yr_2023"], r["yr_2024"], r["yr_2025"], AS_AT, "Active"),
                )
            n_series_ins += 1
    if not dry_run:
        conn.commit()
    conn.close()
    return n_fund, n_series_ins, n_series_upd


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "/tmp/rbc_calyear.json"
    dry_run = "--dry-run" in sys.argv
    recs = extract(src)
    print("parsed %d series" % len(recs))
    nf, ns_ins, ns_upd = seed(recs, dry_run=dry_run)
    if dry_run:
        print("[DRY-RUN] would insert funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
    else:
        print("inserted/updated funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
