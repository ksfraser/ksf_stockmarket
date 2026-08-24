#!/usr/bin/env python3
"""
Update RBC Insurance seg-fund TRAILING returns in the LOCAL SQLite DB
(/root/.hermes/cache/seg_funds.db) from the Lipper portal's data stream.

Source: https://lipper.rbcinsurance.com/rbc/list  (tab "Long Term")
Public DataTables endpoint:
    POST https://lipper.rbcinsurance.com/List/GetResult/  tabName=LongTerm, iDisplayLength=154
Capture:
    curl -s -X POST "https://lipper.rbcinsurance.com/List/GetResult/" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      --data @/tmp/rbc_body_longterm.txt -o /tmp/rbc_longterm.json

Column mapping (verified against response; values are PERCENTAGES already, no x100):
    row[0]  -> symbol  (id='<digits>' in checkbox)
    row[1]  -> name
    row[2]  -> return_1y   (1YEARPERFMONTH)
    row[3]  -> return_3y   (3YEARPERFMONTH)
    row[4]  -> return_5y   (5YEARPERFMONTH)
    row[5]  -> return_10y  (10YEARPERFMONTH)
    row[6]  -> 15yr (N/A typically; no schema column -> ignored)
    row[7]  -> return_incept (INCEPTIONMONTH)
    row[8]  -> CUSDATA (ignored)
    row[9]  -> action (ignored)

Idempotent: UPDATE fund_series by series_code (symbol) within carrier_id=2.

Usage:
    python3 scripts/seed_rbc_trailing.py /tmp/rbc_longterm.json
    python3 scripts/seed_rbc_trailing.py /tmp/rbc_longterm.json --dry-run
"""
import sys
import json
import re
import sqlite3

DB_PATH = "/root/.hermes/cache/seg_funds.db"
CARRIER_ID = 2  # RBC Insurance


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
        if len(r) < 8:
            continue
        sm = re.search(r"id='(\d+)'", r[0] or "")
        sym = sm.group(1) if sm else None
        if not sym:
            continue
        out.append({
            "series_code": sym,
            "return_1y": to_float(r[2]),
            "return_3y": to_float(r[3]),
            "return_5y": to_float(r[4]),
            "return_10y": to_float(r[5]),
            "return_incept": to_float(r[7]),
        })
    return out


def seed(recs, dry_run=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n = 0
    for r in recs:
        cur.execute(
            """UPDATE fund_series SET return_1y=?, return_3y=?, return_5y=?, return_10y=?,
               return_incept=?, updated_at=datetime('now')
               WHERE series_code=? AND fund_id IN (SELECT fund_id FROM funds WHERE carrier_id=?)""",
            (r["return_1y"], r["return_3y"], r["return_5y"], r["return_10y"],
             r["return_incept"], r["series_code"], CARRIER_ID),
        )
        n += cur.rowcount
    if not dry_run:
        conn.commit()
    conn.close()
    return n


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "/tmp/rbc_longterm.json"
    dry_run = "--dry-run" in sys.argv
    with open(src, encoding="utf-8") as fh:
        d = json.load(fh)
    recs = parse(d.get("aaData", []))
    print("parsed %d series" % len(recs))
    n = seed(recs, dry_run=dry_run)
    if dry_run:
        print("[DRY-RUN] would update %d RBC series" % n)
    else:
        print("updated %d RBC series" % n)
