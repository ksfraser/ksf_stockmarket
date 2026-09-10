#!/usr/bin/env python3
"""
Seed Sun Life segregated-fund returns into the LOCAL SQLite DB
(/root/.hermes/cache/seg_funds.db) from the page's embedded JSON.

The "Prices and performance" SPA (https://funds.sunlifeglobalinvestments.com/seg-funds-list)
embeds the full dataset in an inline script:
    window.dfSb.__PRELOADED_STATES__['root'] = {"isClient":false,"data":{"webProfiles":[...]}}

Capture + extract:
    curl -s -A "Mozilla/5.0" "https://funds.sunlifeglobalinvestments.com/seg-funds-list" -o /tmp/sunlife.html
    # then parse the inline JSON (brace-tolerant) -> /tmp/sunlife_profiles.json:
    python3 - <<'PY'
    import json
    html=open('/tmp/sunlife.html',encoding='utf-8',errors='ignore').read()
    i=html.find("__PRELOADED_STATES__['root'] = ")
    s=html.index('{',i)
    obj,_=json.JSONDecoder().raw_decode(html,s)
    json.dump(obj['data']['webProfiles'], open('/tmp/sunlife_profiles.json','w'))
    PY

Each webProfile = ONE series. IMPORTANT SCALE: Sun Life stores returns/MER as
DECIMALS (mer=0.0282 => 2.82%, pytd=0.0868 => 8.68%), unlike iA/Manulife which
were already percentages. We multiply by 100 to match the DB's PERCENT convention.
No calendar-year (2019-2025) fields exist on this page -> yr_* stay NULL
(calendar volatility = Unknown; screen still ranks on trailing returns).

Mapping:
    funds.fund_name        <- overview.fundName        (unique per fund)
    fund_series.series_code <- entityId                 (566 unique series)
    fund_series.series_name <- overview.webProfileFundName
    fund_series.load_type    <- overview.seriesName      (A-Class / F-Class / ...)
    fund_series.mer          <- overview.mer * 100
    return_1m/3m/6m          <- compoundPerformance.p1mo/p3mo/p6mo * 100
    return_1y/3y/5y/10y      <- compoundPerformance.p1yr/p3yr/p5yr/p10yr * 100
    ytd_return               <- compoundPerformance.pytd * 100
    price                    <- dailyPerformance.navPS  (NAV)
    as_at_date               <- compoundPerformance.effectiveDate (2026-07-31)
    price_date               <- dailyPerformance.effectiveDate    (2026-08-21)
    fund_status              <- 'Active' (isInactive==False)

Scope: only active/current funds (isInactive == False). All 566 are active.

Idempotent: series upserted SELECT-first on (fund_id, series_code).

Usage:
    python3 scripts/seed_sunlife_local.py /tmp/sunlife_profiles.json
    python3 scripts/seed_sunlife_local.py /tmp/sunlife_profiles.json --dry-run
"""
import sys
import json
import segfund_db

DB_PATH = "/root/.hermes/cache/seg_funds.db"
CARRIER_ID = 13  # Sun Life (per references/carrier_seg_fund_sources.md)


def pct(v):
    """Sun Life decimals -> percent (e.g. 0.0868 -> 8.68)."""
    if v is None:
        return None
    try:
        return round(float(v) * 100, 4)
    except (ValueError, TypeError):
        return None


def num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def clean(s):
    if not s:
        return ""
    return str(s).strip()


def extract(json_path):
    with open(json_path, encoding="utf-8") as fh:
        profiles = json.load(fh)
    records = []
    for p in profiles:
        if p.get("isInactive"):
            continue  # active/current only
        ov = p.get("overview", {}) or {}
        perf = p.get("performance", {}) or {}
        cp = perf.get("compoundPerformance", {}) or {}
        dp = perf.get("dailyPerformance", {}) or {}
        fname = clean(ov.get("fundName"))
        scode = clean(p.get("entityId"))
        if not fname or not scode:
            continue
        records.append({
            "fund_name": fname,
            "series_code": scode,
            "series_name": clean(ov.get("webProfileFundName")) or fname,
            "category": clean(ov.get("assetClass")) or clean(ov.get("fundCategoryName")),
            "risk_rating": clean(ov.get("riskRatingName")),
            "load_type": clean(ov.get("seriesName")),
            "mer": pct(ov.get("mer")),
            "return_1m": pct(cp.get("p1mo")),
            "return_3m": pct(cp.get("p3mo")),
            "return_6m": pct(cp.get("p6mo")),
            "return_1y": pct(cp.get("p1yr")),
            "return_3y": pct(cp.get("p3yr")),
            "return_5y": pct(cp.get("p5yr")),
            "return_10y": pct(cp.get("p10yr")),
            "ytd_return": pct(cp.get("pytd")),
            "price": num(dp.get("navPS")),
            "as_at": clean(cp.get("effectiveDate")),
            "price_date": clean(dp.get("effectiveDate")),
            "fund_status": "Active",
        })
    return records


def seed(records, dry_run=False):
    conn, backend = segfund_db.get_conn()
    def q(sql, params=()):
        return segfund_db.run(conn, backend, sql, params)
    n_fund = n_series_ins = n_series_upd = 0
    for r in records:
        res = q(
            "INSERT OR IGNORE INTO funds (carrier_id, fund_name, category, risk_rating) VALUES (?,?,?,?)",
            (CARRIER_ID, r["fund_name"], r["category"], r["risk_rating"]),
        )
        if res.rowcount:
            n_fund += 1
        row = q(
            "SELECT fund_id FROM funds WHERE carrier_id=? AND fund_name=?",
            (CARRIER_ID, r["fund_name"]),
        ).fetchone()
        if not row:
            continue
        fund_id = row[0]
        srow = q(
            "SELECT series_id FROM fund_series WHERE fund_id=? AND series_code=?",
            (fund_id, r["series_code"]),
        ).fetchone()
        if srow:
            if not dry_run:
                q(
                    """UPDATE fund_series SET series_name=?, load_type=?, mer=?, return_1m=?, return_3m=?,
                       return_6m=?, return_1y=?, return_3y=?, return_5y=?, return_10y=?, ytd_return=?,
                       price=?, as_at_date=?, price_date=?, fund_status=?, updated_at=datetime('now')
                       WHERE series_id=?""",
                    (r["series_name"], r["load_type"], r["mer"], r["return_1m"], r["return_3m"],
                     r["return_6m"], r["return_1y"], r["return_3y"], r["return_5y"], r["return_10y"],
                     r["ytd_return"], r["price"], r["as_at"], r["price_date"], r["fund_status"], srow[0]),
                )
            n_series_upd += 1
        else:
            if not dry_run:
                q(
                    """INSERT INTO fund_series
                       (fund_id, series_code, series_name, load_type, mer, return_1m, return_3m, return_6m,
                        return_1y, return_3y, return_5y, return_10y, ytd_return, price, as_at_date,
                        price_date, fund_status, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    (fund_id, r["series_code"], r["series_name"], r["load_type"], r["mer"],
                     r["return_1m"], r["return_3m"], r["return_6m"], r["return_1y"], r["return_3y"],
                     r["return_5y"], r["return_10y"], r["ytd_return"], r["price"], r["as_at"],
                     r["price_date"], r["fund_status"]),
                )
            n_series_ins += 1
    if not dry_run:
        conn.commit()
    conn.close()
    return n_fund, n_series_ins, n_series_upd


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "/tmp/sunlife_profiles.json"
    dry_run = "--dry-run" in sys.argv
    recs = extract(src)
    print("parsed %d active series" % len(recs))
    nf, ns_ins, ns_upd = seed(recs, dry_run=dry_run)
    if dry_run:
        print("[DRY-RUN] would insert funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
    else:
        print("inserted/updated funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
