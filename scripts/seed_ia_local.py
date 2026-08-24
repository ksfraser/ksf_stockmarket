#!/usr/bin/env python3
"""
Seed iA Financial segregated-fund returns into the LOCAL SQLite DB
(/root/.hermes/cache/seg_funds.db) using the page's data stream:

    GET https://ia.ca/api/sites/ia/fund/yield?locale=en-ca&fundType=savings&date=<as-of>

That XHR populates the "Fund performance and overview" table on
https://ia.ca/funds-performance (a Next.js SPA — the table is JS-rendered,
so the data is captured from the API, not the static HTML).

Return fields arrive as {"value": <pct>, "isSimulation": <bool>}; we take .value.
The schema carries BOTH calendar columns (yr_2019..yr_2025) and trailing
columns (return_1m/3m/6m/1y/3y/5y/10y, ytd_return, price), so we map:
    yr_2025          <- lastYearReturn          (2025 calendar annual, %)
    return_1m        <- netReturns1Month
    return_3m        <- netReturns3Months
    return_6m        <- netReturns6Months
    return_1y        <- netReturns1Year         (annualized trailing)
    return_3y        <- netReturns3Years
    return_5y        <- netReturns5Years
    return_10y       <- netReturns10Years
    ytd_return       <- netReturnYearToDate
    price            <- netUnitValue            (NAV, $)
    price_date/as_at <- the as-of date from the API call

iA only exposes the 2025 calendar year (not 2019-2024), so calendar-year
volatility (yr_2019..yr_2024) is left NULL; the trailing return_* columns
still feed the screen's return/relative metrics.

Idempotent: series upserted SELECT-first on (fund_id, series_code), so the
script can be re-run safely without creating duplicate rows.

Usage:
    curl -s -G "https://ia.ca/api/sites/ia/fund/yield" \
      --data-urlencode "locale=en-ca" --data-urlencode "fundType=savings" \
      --data-urlencode "date=Fri Aug 21 2026 00:00:00 GMT-0600 (Mountain Daylight Time)" \
      -o /tmp/ia_yield_savings.json
    python3 scripts/seed_ia_local.py /tmp/ia_yield_savings.json
    python3 scripts/seed_ia_local.py /tmp/ia_yield_savings.json --dry-run   # no writes
"""
import sys
import json
import html
import sqlite3

DB_PATH = "/root/.hermes/cache/seg_funds.db"
CARRIER_ID = 5  # iA Financial (per references/carrier_seg_fund_sources.md)
AS_AT = "2026-08-21"  # as-of date passed to the API call


def to_float(v):
    if v is None:
        return None
    if isinstance(v, dict):
        v = v.get("value")
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
        name = clean(e.get("fundName"))
        code = clean(e.get("fundCode"))
        if not name or not code:
            continue
        records.append({
            "name": name,
            "series_code": code,
            "mer": None,  # not provided by the yield stream
            "yr_2025": to_float(e.get("lastYearReturn")),
            "return_1m": to_float(e.get("netReturns1Month")),
            "return_3m": to_float(e.get("netReturns3Months")),
            "return_6m": to_float(e.get("netReturns6Months")),
            "return_1y": to_float(e.get("netReturns1Year")),
            "return_3y": to_float(e.get("netReturns3Years")),
            "return_5y": to_float(e.get("netReturns5Years")),
            "return_10y": to_float(e.get("netReturns10Years")),
            "ytd_return": to_float(e.get("netReturnYearToDate")),
            "price": to_float(e.get("netUnitValue")),
        })
    return records


def seed(records, dry_run=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n_fund = n_series_ins = n_series_upd = 0
    for r in records:
        cur.execute(
            "INSERT OR IGNORE INTO funds (carrier_id, fund_name) VALUES (?,?)",
            (CARRIER_ID, r["name"]),
        )
        if cur.rowcount:
            n_fund += 1
        cur.execute(
            "SELECT fund_id FROM funds WHERE carrier_id=? AND fund_name=?",
            (CARRIER_ID, r["name"]),
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
                    """UPDATE fund_series SET series_name=?, mer=?, yr_2025=?, return_1m=?,
                       return_3m=?, return_6m=?, return_1y=?, return_3y=?, return_5y=?,
                       return_10y=?, ytd_return=?, price=?, price_date=?, as_at_date=?,
                       updated_at=datetime('now')
                       WHERE series_id=?""",
                    (r["name"], r["mer"], r["yr_2025"], r["return_1m"], r["return_3m"],
                     r["return_6m"], r["return_1y"], r["return_3y"], r["return_5y"],
                     r["return_10y"], r["ytd_return"], r["price"], AS_AT, AS_AT, srow[0]),
                )
            n_series_upd += 1
        else:
            if not dry_run:
                cur.execute(
                    """INSERT INTO fund_series
                       (fund_id, series_code, series_name, mer, yr_2025, return_1m, return_3m,
                        return_6m, return_1y, return_3y, return_5y, return_10y, ytd_return,
                        price, price_date, as_at_date, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    (fund_id, r["series_code"], r["name"], r["mer"], r["yr_2025"],
                     r["return_1m"], r["return_3m"], r["return_6m"], r["return_1y"],
                     r["return_3y"], r["return_5y"], r["return_10y"], r["ytd_return"],
                     r["price"], AS_AT, AS_AT),
                )
            n_series_ins += 1
    if not dry_run:
        conn.commit()
    conn.close()
    return n_fund, n_series_ins, n_series_upd


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "/tmp/ia_yield_savings.json"
    dry_run = "--dry-run" in sys.argv
    recs = extract(src)
    print("parsed %d series" % len(recs))
    nf, ns_ins, ns_upd = seed(recs, dry_run=dry_run)
    if dry_run:
        print("[DRY-RUN] would insert funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
    else:
        print("inserted/updated funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
