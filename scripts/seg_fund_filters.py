#!/usr/bin/env python3
"""
Seg-fund stability + class-eligibility screen.

Reads a seg_funds store (default: local SQLite at /root/.hermes/cache/seg_funds.db)
and produces, per fund *series*:

  1. STABILITY rating  -- volatility from available annual returns
     (yr_2019..yr_2025 where present; falls back to trailing return_1y/3y/5y/10y
     when calendar columns are null). The classic "+30% then -30%" pattern shows
     up directly as the annual spread / High rating.

  2. CLASS ELIGIBILITY -- a per-series minimum investment derived HEURISTICALLY
     from the series code (fee-based F/F5/T5 ~ $100k+, institutional/private
     pools ~ $250k, retail A/NL/no-load/front-end $0). This is APPROXIMATE until
     real carrier "wealth series" minimums are sourced (see MIN_RULES).

Given an investable wealth W (default 175000), it marks each series eligible /
ineligible and collapses each fund to its single base (eligible, lowest-min /
lowest-MER) class -- the one to KEEP -- flagging the rest for removal.

Results are written to a reusable table `seg_fund_screen` in the same DB and a
shortlist is printed.

Usage:
    python3 seg_fund_filters.py                 # W=175000, default DB
    python3 seg_fund_filters.py --wealth 250000 --db /path/to/seg_funds.db
    python3 seg_fund_filters.py --top 30        # print 30 eligible base-class rows

NOTE: performance_history is empty in the current store, so volatility uses the
snapshot returns only. It sharpens once NAV history is populated.
"""
import argparse
import sqlite3
import statistics
import re
import sys

DEFAULT_DB = "/root/.hermes/cache/seg_funds.db"
ANNUAL_COLS = ["yr_2019", "yr_2020", "yr_2021", "yr_2022", "yr_2023", "yr_2024", "yr_2025"]
TRAIL_COLS = ["return_1y", "return_3y", "return_5y", "return_10y"]

# --- Heuristic per-series minimum investment (CAD). APPROXIMATE. ---------------
# Replace with carrier-documented minimums when available.
INST_RE = re.compile(r"(?i)(INSTITUTIONAL|PRIVATE|POOL|PMI|MPS4[0-9]{3}|NLCB[4-9])")
FEE_RE = re.compile(r"(?i)(^|[^A-Z])(F\d|T5|T8|FB|FEES)($|[^A-Z])")


def heuristic_min(series_code, load_type):
    """Approximate minimum investment for a series. 0 == no minimum."""
    sc = (series_code or "").strip()
    lt = (load_type or "").lower()
    blob = f"{sc} {lt}"
    if INST_RE.search(blob):
        return 250_000          # institutional / private pooled -- high bar
    if "no-load" in lt or sc.upper().startswith("NL") or "front" in lt or sc.upper().startswith("FE"):
        return 0                # retail no-load / front-end -- no minimum
    if FEE_RE.search(blob):
        return 100_000          # fee-based advisor series -- typical $100k
    if sc.upper() in ("A", "A5", "ADV", "D", "DSC"):
        return 0                # deferred/retail series -- no minimum
    return 0                    # unknown -> treat as eligible, flag below


def stability(series):
    """Return (rating, basis, n, spread, std, best, worst) for a series row."""
    ann = [series[c] for c in ANNUAL_COLS if series[c] is not None]
    if len(ann) >= 2:
        spread = max(ann) - min(ann)
        std = statistics.pstdev(ann)
        best, worst = max(ann), min(ann)
        rating = "Low" if std < 5 else ("Medium" if std < 12 else "High")
        return (rating, "annual", len(ann), round(spread, 2), round(std, 2), round(best, 2), round(worst, 2))
    tr = [series[c] for c in TRAIL_COLS if series[c] is not None]
    if len(tr) >= 2:
        spread = max(tr) - min(tr)
        std = statistics.pstdev(tr)
        best, worst = max(tr), min(tr)
        rating = "Low" if std < 5 else ("Medium" if std < 12 else "High")
        return (rating, "trailing", len(tr), round(spread, 2), round(std, 2), round(best, 2), round(worst, 2))
    return ("Unknown", "insufficient", 0, None, None, None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--wealth", type=float, default=175_000, help="investable wealth W (CAD)")
    ap.add_argument("--top", type=int, default=20, help="rows to print in shortlist")
    ap.add_argument("--rebuild", action="store_true", help="drop+recreate seg_fund_screen")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Collect series rows joined to fund + carrier for labels.
    rows = cur.execute("""
        SELECT s.series_id, s.fund_id, s.series_code, s.series_name, s.load_type,
               s.mer, s.guarantee_pct, s.return_1y, s.return_3y, s.return_5y,
               s.return_10y, s.return_incept, s.yr_2019, s.yr_2020, s.yr_2021,
               s.yr_2022, s.yr_2023, s.yr_2024, s.yr_2025,
               f.fund_name, f.category, c.short_name AS carrier
        FROM fund_series s
        JOIN funds f ON f.fund_id = s.fund_id
        JOIN carriers c ON c.carrier_id = f.carrier_id
        WHERE s.fund_status = 'Open' OR s.fund_status IS NULL
    """).fetchall()

    # Build screen records + per-fund base-class selection.
    recs = []
    by_fund = {}
    for r in rows:
        rating, basis, n, spread, std, best, worst = stability(r)
        mn = heuristic_min(r["series_code"], r["load_type"])
        eligible = mn <= args.wealth
        rec = {
            "series_id": r["series_id"],
            "fund_id": r["fund_id"],
            "carrier": r["carrier"],
            "fund_name": r["fund_name"],
            "category": r["category"],
            "series_code": r["series_code"],
            "load_type": r["load_type"],
            "mer": r["mer"],
            "guarantee_pct": r["guarantee_pct"],
            "min_invest": mn,
            "eligible": 1 if eligible else 0,
            "stability": rating,
            "vol_basis": basis,
            "ann_n": n,
            "spread": spread,
            "std": std,
            "best_yr": best,
            "worst_yr": worst,
            "ret_5y": r["return_5y"],
            "ret_10y": r["return_10y"],
            "ret_incept": r["return_incept"],
        }
        recs.append(rec)
        by_fund.setdefault(r["fund_id"], []).append(rec)

    # Base class = among ELIGIBLE series of a fund, lowest min then lowest MER.
    for fid, lst in by_fund.items():
        elig = [x for x in lst if x["eligible"]]
        pool = elig if elig else lst  # if none eligible, still pick a rep (none kept anyway)
        if not pool:
            continue
        base = min(pool, key=lambda x: (x["min_invest"] if x["min_invest"] else 0, x["mer"] if x["mer"] is not None else 99))
        for x in lst:
            x["base_class"] = 1 if x is base else 0

    # Persist to seg_fund_screen.
    if args.rebuild:
        cur.execute("DROP TABLE IF EXISTS seg_fund_screen")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seg_fund_screen (
            series_id INTEGER PRIMARY KEY,
            fund_id INTEGER, carrier TEXT, fund_name TEXT, category TEXT,
            series_code TEXT, load_type TEXT, mer REAL, guarantee_pct REAL,
            min_invest INTEGER, eligible INTEGER, stability TEXT, vol_basis TEXT,
            ann_n INTEGER, spread REAL, std REAL, best_yr REAL, worst_yr REAL,
            ret_5y REAL, ret_10y REAL, ret_incept REAL, base_class INTEGER,
            wealth_threshold REAL, computed_at TEXT
        )
    """)
    cur.execute("DELETE FROM seg_fund_screen")
    from datetime import datetime
    now = datetime.utcnow().isoformat(sep=" ")
    for x in recs:
        cur.execute(
            """INSERT INTO seg_fund_screen VALUES (
                :series_id,:fund_id,:carrier,:fund_name,:category,:series_code,
                :load_type,:mer,:guarantee_pct,:min_invest,:eligible,:stability,
                :vol_basis,:ann_n,:spread,:std,:best_yr,:worst_yr,:ret_5y,:ret_10y,
                :ret_incept,:base_class,:wt,:computed_at)""",
            {**x, "wt": args.wealth, "computed_at": now},
        )
    con.commit()

    # ---- Summary -----------------------------------------------------------
    total = len(recs)
    elig = sum(x["eligible"] for x in recs)
    base_kept = sum(1 for x in recs if x["eligible"] and x["base_class"])
    with_annual = sum(1 for x in recs if x["vol_basis"] == "annual")
    stable_low = sum(1 for x in recs if x["stability"] == "Low")
    stable_med = sum(1 for x in recs if x["stability"] == "Medium")
    stable_high = sum(1 for x in recs if x["stability"] == "High")
    unknown = sum(1 for x in recs if x["stability"] == "Unknown")

    print(f"DB: {args.db}")
    print(f"Wealth threshold W = ${args.wealth:,.0f}")
    print(f"Series scanned : {total}")
    print(f"Eligible (min<=W): {elig}  | base-class kept: {base_kept}")
    print(f"Stability: Low={stable_low} Medium={stable_med} High={stable_high} Unknown={unknown}")
    print(f"  (volatility basis: {with_annual} from calendar-year returns, "
          f"{total-with_annual} from trailing / insufficient)")
    print("-" * 78)

    # Shortlist: eligible base-class series, ranked by stability then 5y return.
    rank = {"Low": 0, "Medium": 1, "High": 2, "Unknown": 3}
    short = [x for x in recs if x["eligible"] and x["base_class"]]
    short.sort(key=lambda x: (rank.get(x["stability"], 3), -(x["ret_5y"] or -999)))
    print(f"TOP {min(args.top, len(short))} ELIGIBLE, STABILITY-RANKED (base class per fund):")
    hdr = f"{'carrier':<6}{'stab':<8}{'5y%':>7}{'10y%':>7}{'spread':>8}{'min':>9}  fund / series"
    print(hdr)
    for x in short[: args.top]:
        nm = (x["fund_name"] or "")[:42]
        sc = (x["series_code"] or "")
        print(f"{x['carrier']:<6}{x['stability']:<8}"
              f"{(x['ret_5y'] or 0):>7.1f}{(x['ret_10y'] or 0):>7.1f}"
              f"{(x['spread'] or 0):>8.1f}{x['min_invest']:>9,}"
              f"  {nm} [{sc}]")
    con.close()


if __name__ == "__main__":
    main()
