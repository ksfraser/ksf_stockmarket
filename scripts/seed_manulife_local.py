#!/usr/bin/env python3
"""
Seed Manulife segregated-fund returns into the LOCAL SQLite DB
(/root/.hermes/cache/seg_funds.db) from the page's data stream:

    GET https://funds.manulife.ca/profiles/api/funds/list/en-US/?skip=0&take=1000
    (paginate skip=0,1000,...5605; TotalItems=5605; all Manulife seg-fund
     product lines: GIF Select, MPIP, RetirementPlus, Ideal, etc.)

The "Prices & Performance" SPA (https://funds.manulife.ca/en-US/profiles/)
renders this via XHR. Each item is ONE series (fundServCode unique). We map:
    funds.fund_name          <- fundName            (412 unique funds)
    fund_series.series_code   <- fundServCode        (5605 unique series)
    fund_series.series_name   <- entityName         (full series name)
    fund_series.mer           <- mer (%)
    yr_2019..yr_2025          <- annRet2019..annRet2025   (calendar annual, %)
    return_1m/3m/6m           <- compM1/3/6          (compound trailing)
    return_1y/3y/5y/10y       <- compY1/3/5/10       (compound trailing annualized)
    return_incept             <- compIncep
    ytd_return                <- retYtd
    price                     <- retNav (NAV, $)
    fund_status               <- fundStatus
    as_at_date/price_date     <- PerformanceAsOfDate (2026/07/31)

Idempotent: series upserted SELECT-first on (fund_id, series_code).

Usage:
    for s in 0 1000 2000 3000 4000 5000; do
      curl -s "https://funds.manulife.ca/profiles/api/funds/list/en-US/?skip=$s&take=1000" -o /tmp/manu_$s.json
    done
    # combine: python3 -c "import json; items=[]; [items.extend(json.load(open(f))['Items']) for f in ['/tmp/manu_%d.json'%s for s in (0,1000,2000,3000,4000,5000)]]; json.dump(items, open('/tmp/manu_all.json','w'))"
    python3 scripts/seed_manulife_local.py /tmp/manu_all.json
    python3 scripts/seed_manulife_local.py /tmp/manu_all.json --dry-run   # no writes
"""
import sys
import json
import html
import sqlite3

DB_PATH = "/root/.hermes/cache/seg_funds.db"
CARRIER_ID = 1  # Manulife (per references/carrier_seg_fund_sources.md)
AS_AT = "2026-07-31"  # PerformanceAsOfDate from the API response


def to_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def clean(s):
    if not s:
        return ""
    return html.unescape(str(s)).replace("\xa0", " ").strip()


def extract(json_path):
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    records = []
    for e in data:
        fname = clean(e.get("fundName"))
        code = clean(e.get("fundServCode"))
        if not fname or not code:
            continue
        records.append({
            "fund_name": fname,
            "series_code": code,
            "series_name": clean(e.get("entityName")) or fname,
            "category": clean(e.get("assetClass")) or clean(e.get("fundCategory")),
            "risk_rating": clean(e.get("riskRating")),
            "fund_status": clean(e.get("fundStatus")),
            "mer": to_float(e.get("mer")),
            "yr_2019": to_float(e.get("annRet2019")),
            "yr_2020": to_float(e.get("annRet2020")),
            "yr_2021": to_float(e.get("annRet2021")),
            "yr_2022": to_float(e.get("annRet2022")),
            "yr_2023": to_float(e.get("annRet2023")),
            "yr_2024": to_float(e.get("annRet2024")),
            "yr_2025": to_float(e.get("annRet2025")),
            "return_1m": to_float(e.get("compM1")),
            "return_3m": to_float(e.get("compM3")),
            "return_6m": to_float(e.get("compM6")),
            "return_1y": to_float(e.get("compY1")),
            "return_3y": to_float(e.get("compY3")),
            "return_5y": to_float(e.get("compY5")),
            "return_10y": to_float(e.get("compY10")),
            "return_incept": to_float(e.get("compIncep")),
            "ytd_return": to_float(e.get("retYtd")),
            "price": to_float(e.get("retNav")),
        })
    return records


def seed(records, dry_run=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n_fund = n_series_ins = n_series_upd = 0
    for r in records:
        cur.execute(
            "INSERT OR IGNORE INTO funds (carrier_id, fund_name, category, risk_rating) VALUES (?,?,?,?)",
            (CARRIER_ID, r["fund_name"], r["category"], r["risk_rating"]),
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
                    """UPDATE fund_series SET series_name=?, mer=?, yr_2019=?, yr_2020=?, yr_2021=?,
                       yr_2022=?, yr_2023=?, yr_2024=?, yr_2025=?, return_1m=?, return_3m=?,
                       return_6m=?, return_1y=?, return_3y=?, return_5y=?, return_10y=?,
                       return_incept=?, ytd_return=?, price=?, fund_status=?, price_date=?,
                       as_at_date=?, updated_at=datetime('now')
                       WHERE series_id=?""",
                    (r["series_name"], r["mer"], r["yr_2019"], r["yr_2020"], r["yr_2021"],
                     r["yr_2022"], r["yr_2023"], r["yr_2024"], r["yr_2025"], r["return_1m"],
                     r["return_3m"], r["return_6m"], r["return_1y"], r["return_3y"],
                     r["return_5y"], r["return_10y"], r["return_incept"], r["ytd_return"],
                     r["price"], r["fund_status"], AS_AT, AS_AT, srow[0]),
                )
            n_series_upd += 1
        else:
            if not dry_run:
                cur.execute(
                    """INSERT INTO fund_series
                       (fund_id, series_code, series_name, mer, yr_2019, yr_2020, yr_2021, yr_2022,
                        yr_2023, yr_2024, yr_2025, return_1m, return_3m, return_6m, return_1y,
                        return_3y, return_5y, return_10y, return_incept, ytd_return, price,
                        fund_status, price_date, as_at_date, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    (fund_id, r["series_code"], r["series_name"], r["mer"], r["yr_2019"],
                     r["yr_2020"], r["yr_2021"], r["yr_2022"], r["yr_2023"], r["yr_2024"],
                     r["yr_2025"], r["return_1m"], r["return_3m"], r["return_6m"], r["return_1y"],
                     r["return_3y"], r["return_5y"], r["return_10y"], r["return_incept"],
                     r["ytd_return"], r["price"], r["fund_status"], AS_AT, AS_AT),
                )
            n_series_ins += 1
    if not dry_run:
        conn.commit()
    conn.close()
    return n_fund, n_series_ins, n_series_upd


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "/tmp/manu_all.json"
    dry_run = "--dry-run" in sys.argv
    recs = extract(src)
    print("parsed %d series" % len(recs))
    nf, ns_ins, ns_upd = seed(recs, dry_run=dry_run)
    if dry_run:
        print("[DRY-RUN] would insert funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
    else:
        print("inserted/updated funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
