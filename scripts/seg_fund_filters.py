#!/usr/bin/env python3
"""
Seg-fund stability + class-eligibility + relative-behaviour screen.

Reads a seg_funds store (default: local SQLite /root/.hermes/cache/seg_funds.db)
and produces, per fund *series*:

  1. STABILITY rating -- volatility from available ANNUAL returns
     (yr_2019..yr_2025 where present; falls back to trailing return_1y/3y/5y/10y
     when calendar columns are null). Annual std-dev IS the volatility the user
     cares about ("+30% then -30%" = a wide annual spread / High rating).

  2. RELATIVE behaviour vs the cross-section (needs >=2 annual years):
       * beta    -- sensitivity of the fund to the equal-weighted average fund
                   (beta<1 = defensive, >1 = more volatile than the pack)
       * alpha   -- Jensen-style excess return vs that average (out/under-perf)
       * corr    -- correlation with the average fund
       * contrary-- True when corr<0 (a diversifier / "often contrary")
       * neg_years -- count of down years (the "why buy a bond fund that lost
                      money?" signal)
     There is no single market index for seg funds, so the equal-weighted fund
     average is used as the natural benchmark.

  3. CLASS ELIGIBILITY -- per-series minimum investment from carrier "wealth
     series" definitions. CURRENTLY HEURISTIC (fee-based F/F5/T5 ~ $100k+,
     institutional/private pools ~ $250k, retail A/NL/no-load/front-end $0).
     Replace with sourced minimums when available (see MIN_RULES).

  4. GUARANTEE level -- parsed from fund_name (75/75, 75/100, 100/100) as an
     INFORMATIONAL column only. For a 52-yr-old investor these maturity/death
     guarantees are effectively post-retirement features, NOT a live safety
     signal, so they do NOT drive ranking.

Given an investable wealth W (default 175000), it marks each series eligible /
ineligible and collapses each fund to its single base (eligible, lowest-min /
lowest-MER) class -- the one to KEEP -- flagging the rest for removal.

Results are written to a reusable table `seg_fund_screen` and a shortlist printed.

Usage:
    python3 seg_fund_filters.py                      # W=175000, default DB
    python3 seg_fund_filters.py --wealth 250000
    python3 seg_fund_filters.py --top 30
    python3 seg_fund_filters.py --contrarian         # list contrary funds
    python3 seg_fund_filters.py --rebuild             # drop+recreate screen tbl

NOTE: in the current store performance_history is empty and yr_* are NULL for
all carriers, so volatility/relative metrics use the trailing-return proxy and
flag vol_basis='trailing' / 'insufficient'. Populate yr_2019..yr_2025 (from
carrier Lipper portals / fund-fact PDFs) to unlock true annual metrics.
"""
import argparse
import sqlite3
import statistics
import re
import sys
from datetime import datetime

DEFAULT_DB = "/root/.hermes/cache/seg_funds.db"
ANNUAL_COLS = ["yr_2019", "yr_2020", "yr_2021", "yr_2022", "yr_2023", "yr_2024", "yr_2025"]
TRAIL_COLS = ["return_1y", "return_3y", "return_5y", "return_10y"]
GUAR_RE = re.compile(r"(?i)\b(\d{1,2})\s*/\s*(\d{1,2})\b")

# --- Heuristic per-series minimum investment (CAD). APPROXIMATE. ---------------
INST_RE = re.compile(r"(?i)(INSTITUTIONAL|PRIVATE|POOL|PMI|MPS4[0-9]{3}|NLCB[4-9])")
FEE_RE = re.compile(r"(?i)(^|[^A-Z])(F\d|T5|T8|FB|FEES)($|[^A-Z])")


def heuristic_min(series_code, load_type):
    sc = (series_code or "").strip()
    lt = (load_type or "").lower()
    blob = f"{sc} {lt}"
    if INST_RE.search(blob):
        return 250_000
    if "no-load" in lt or sc.upper().startswith("NL") or "front" in lt or sc.upper().startswith("FE"):
        return 0
    if FEE_RE.search(blob):
        return 100_000
    if sc.upper() in ("A", "A5", "ADV", "D", "DSC"):
        return 0
    return 0


def parse_guarantee(fund_name):
    m = GUAR_RE.search(fund_name or "")
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return max(a, b)  # maturity guarantee level (e.g. 75/75->75, 100/100->100)
    return None


def stability(series):
    ann = [series[c] for c in ANNUAL_COLS if series[c] is not None]
    if len(ann) >= 2:
        spread = max(ann) - min(ann)
        std = statistics.pstdev(ann)
        rating = "Low" if std < 5 else ("Medium" if std < 12 else "High")
        return (rating, "annual", len(ann), round(spread, 2), round(std, 2), round(max(ann), 2), round(min(ann), 2))
    tr = [series[c] for c in TRAIL_COLS if series[c] is not None]
    if len(tr) >= 2:
        spread = max(tr) - min(tr)
        std = statistics.pstdev(tr)
        rating = "Low" if std < 5 else ("Medium" if std < 12 else "High")
        return (rating, "trailing", len(tr), round(spread, 2), round(std, 2), round(max(tr), 2), round(min(tr), 2))
    return ("Unknown", "insufficient", 0, None, None, None, None)


def rel_metrics(series_ann, market, years_sorted):
    """beta, alpha, corr, neg_years, contrary -- needs >=2 shared years."""
    yrs = [y for y in years_sorted if y in series_ann and y in market]
    if len(yrs) < 2:
        return (None, None, None, None, None)
    ri = [series_ann[y] for y in yrs]
    rm = [market[y] for y in yrs]
    mi, mm = statistics.mean(ri), statistics.mean(rm)
    cov = sum((a - mi) * (b - mm) for a, b in zip(ri, rm)) / len(yrs)
    varm = sum((b - mm) ** 2 for b in rm) / len(yrs)
    stdi = statistics.pstdev(ri)
    stdm = statistics.pstdev(rm)
    beta = round(cov / varm, 3) if varm else 0.0
    alpha = round(mi - beta * mm, 2)
    corr = round(cov / (stdi * stdm), 3) if (stdi and stdm) else 0.0
    neg = sum(1 for v in ri if v < 0)
    return (beta, alpha, corr, neg, corr < 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--wealth", type=float, default=175_000)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--contrarian", action="store_true", help="list contrary (corr<0) funds")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

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

    # --- annual matrix -> cross-sectional "market" per year ---
    series_ann = {}
    all_years = set()
    for r in rows:
        d = {}
        for c in ANNUAL_COLS:
            v = r[c]
            if v is not None:
                d[int(c[3:])] = v
                all_years.add(int(c[3:]))
        series_ann[r["series_id"]] = d
    years_sorted = sorted(all_years)
    market = {}
    for y in years_sorted:
        vals = [d[y] for d in series_ann.values() if y in d]
        if len(vals) >= 2:
            market[y] = statistics.mean(vals)

    recs = []
    by_fund = {}
    for r in rows:
        rating, basis, n, spread, std, best, worst = stability(r)
        mn = heuristic_min(r["series_code"], r["load_type"])
        beta, alpha, corr, neg, contrary = rel_metrics(series_ann.get(r["series_id"], {}), market, years_sorted)
        gu = parse_guarantee(r["fund_name"])
        # mean return for risk-adjusted + bond-fund sanity
        ann = series_ann.get(r["series_id"], {})
        mean_ret = statistics.mean(ann.values()) if len(ann) >= 1 else (r["return_5y"] or r["return_1y"])
        cat = (r["category"] or "").lower()
        poor = 1 if (("bond" in cat or "fixed" in cat or "income" in cat or "money" in cat)
                     and mean_ret is not None and (mean_ret < 3 or (neg or 0) > 0)) else 0
        rec = {
            "series_id": r["series_id"], "fund_id": r["fund_id"], "carrier": r["carrier"],
            "fund_name": r["fund_name"], "category": r["category"], "series_code": r["series_code"],
            "load_type": r["load_type"], "mer": r["mer"], "guarantee_pct": gu if gu else r["guarantee_pct"],
            "min_invest": mn, "eligible": 1 if mn <= args.wealth else 0, "stability": rating,
            "vol_basis": basis, "ann_n": n, "spread": spread, "std": std,
            "best_yr": best, "worst_yr": worst, "ret_5y": r["return_5y"], "ret_10y": r["return_10y"],
            "ret_incept": r["return_incept"], "beta": beta, "alpha": alpha, "corr": corr,
            "neg_years": neg, "contrary": 1 if contrary else 0, "poor_risk_adj": poor,
            "mean_ret": round(mean_ret, 2) if mean_ret is not None else None,
        }
        recs.append(rec)
        by_fund.setdefault(r["fund_id"], []).append(rec)

    for fid, lst in by_fund.items():
        pool = [x for x in lst if x["eligible"]] or lst
        if not pool:
            continue
        base = min(pool, key=lambda x: (x["min_invest"] or 0, x["mer"] if x["mer"] is not None else 99))
        for x in lst:
            x["base_class"] = 1 if x is base else 0

    cur.execute("DROP TABLE IF EXISTS seg_fund_screen")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seg_fund_screen (
            series_id INTEGER PRIMARY KEY, fund_id INTEGER, carrier TEXT, fund_name TEXT,
            category TEXT, series_code TEXT, load_type TEXT, mer REAL, guarantee_pct REAL,
            min_invest INTEGER, eligible INTEGER, stability TEXT, vol_basis TEXT, ann_n INTEGER,
            spread REAL, std REAL, best_yr REAL, worst_yr REAL, ret_5y REAL, ret_10y REAL,
            ret_incept REAL, beta REAL, alpha REAL, corr REAL, neg_years INTEGER,
            contrary INTEGER, poor_risk_adj INTEGER, mean_ret REAL, base_class INTEGER,
            wealth_threshold REAL, computed_at TEXT)
    """)
    cur.execute("DELETE FROM seg_fund_screen")
    now = datetime.utcnow().isoformat(sep=" ")
    for x in recs:
        cur.execute(
            """INSERT INTO seg_fund_screen VALUES (
                :series_id,:fund_id,:carrier,:fund_name,:category,:series_code,:load_type,
                :mer,:guarantee_pct,:min_invest,:eligible,:stability,:vol_basis,:ann_n,
                :spread,:std,:best_yr,:worst_yr,:ret_5y,:ret_10y,:ret_incept,:beta,:alpha,
                :corr,:neg_years,:contrary,:poor_risk_adj,:mean_ret,:base_class,:wt,:computed_at)""",
            {**x, "wt": args.wealth, "computed_at": now},
        )
    con.commit()

    total = len(recs)
    elig = sum(x["eligible"] for x in recs)
    base_kept = sum(1 for x in recs if x["eligible"] and x["base_class"])
    with_annual = sum(1 for x in recs if x["vol_basis"] == "annual")
    low = sum(1 for x in recs if x["stability"] == "Low")
    med = sum(1 for x in recs if x["stability"] == "Medium")
    high = sum(1 for x in recs if x["stability"] == "High")
    unk = sum(1 for x in recs if x["stability"] == "Unknown")
    rel_ok = sum(1 for x in recs if x["beta"] is not None)
    contr = sum(1 for x in recs if x["contrary"])
    poor = sum(1 for x in recs if x["poor_risk_adj"])

    print(f"DB: {args.db}")
    print(f"Wealth W = ${args.wealth:,.0f}")
    print(f"Scanned {total} series | eligible {elig} | base-class kept {base_kept}")
    print(f"Stability: Low={low} Medium={med} High={high} Unknown={unk}")
    print(f"  vol basis: {with_annual} annual / {total-with_annual} trailing-or-insufficient")
    print(f"Relative (beta/alpha/corr) computed for {rel_ok} series | contrary(corr<0)={contr} | poor-risk-adj={poor}")
    print("-" * 88)

    if args.contrarian:
        cs = [x for x in recs if x["contrary"] and x["eligible"]]
        cs.sort(key=lambda x: (x["corr"] if x["corr"] is not None else 0))
        print(f"CONTRARIAN (corr<0) ELIGIBLE FUNDS -- top {min(args.top,len(cs))}:")
        for x in cs[: args.top]:
            print(f"  {x['carrier']:<6}corr={x['corr']:>5} beta={x['beta']:>5} alpha={x['alpha']:>5} "
                  f"{x['stability']:<7} {(x['fund_name'] or '')[:46]} [{x['series_code']}]")
        con.close()
        return

    rank = {"Low": 0, "Medium": 1, "High": 2, "Unknown": 3}
    short = [x for x in recs if x["eligible"] and x["base_class"]]
    short.sort(key=lambda x: (rank.get(x["stability"], 3), -(x["alpha"] or -999), -(x["mean_ret"] or -999)))
    print(f"TOP {min(args.top, len(short))} ELIGIBLE, STABILITY-RANKED (base class per fund):")
    print(f"{'cr':<6}{'stab':<8}{'5y%':>6}{'a%':>6}{'bta':>6}{'corr':>6}{'neg':>4}{'min':>9}  fund / series")
    for x in short[: args.top]:
        print(f"{x['carrier']:<6}{x['stability']:<8}"
              f"{(x['ret_5y'] or 0):>6.1f}{(x['alpha'] or 0):>6.1f}"
              f"{(x['beta'] or 0):>6.2f}{(x['corr'] or 0):>6.2f}"
              f"{(x['neg_years'] or 0):>4}{x['min_invest']:>9,}"
              f"  {(x['fund_name'] or '')[:42]} [{x['series_code']}]")
    con.close()


if __name__ == "__main__":
    main()
