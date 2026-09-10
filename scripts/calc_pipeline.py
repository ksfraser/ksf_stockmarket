#!/usr/bin/env python3
"""
calc_pipeline.py - Seg-fund analytics pipeline.

Per fund *series* computes and writes to `seg_fund_metrics` (rebuilt each run,
idempotent):

  1. VOLATILITY - annual std-dev of calendar returns (Low/Medium/High).
     Reuses seg_fund_filters.stability().

  2. MARKET behaviour - beta / alpha / corr vs the equal-weighted cross-section
     of OPEN funds (the investable universe). Reuses seg_fund_filters.rel_metrics().

  3. SECTOR (peer-group) behaviour - beta / alpha / corr vs the mean of the
     fund's own NORMALIZED peer group (Equity / Balanced / Fixed Income /
     Money Market / Other). Same methodology as (2) but the benchmark is the
     peer average, not the all-fund average.

  4. MAX DRAWDOWN - from a NAV path reconstructed from trailing total-return
     NAV levels (anchor 100 now; historical levels 100/(1+r) at the 1/3/5/10y
     offsets). A genuine NAV-path drawdown at trailing resolution -- higher
     than year-end calendar points and it works for funds with sparse annual
     history (the old annual-only code reported 0% for any fund with <2
     calendar years). Falls back to the annual calendar path when a fund has
     no trailing returns.

  5. LIPPER-STYLE composite score (0-5). NOT the licensed Lipper Leader number
     (that needs a Lipper data feed). It is our own quintile-rank composite
     across 4 components available in our data:
         - Total Return   (return_5y, higher better)
         - Consistent Return (volatility std, lower better)
         - Preservation   (1 - max_drawdown, higher better)
         - Expense        (MER, lower better)
     Tax Efficiency is excluded (no tax data in source). Each component is
     percentile-ranked within the fund's peer group -> 0-5; overall = mean of
     the available components (>=2 required, else NULL).

The benchmark averages (market + peer) are computed from OPEN/NULL-status
series only, so closed funds are still scored but measured against the
investable universe.

Usage:
    python3 scripts/calc_pipeline.py                 # default DB
    python3 scripts/calc_pipeline.py --db /path/db
    python3 scripts/calc_pipeline.py --dry-run
"""
import argparse
import os
import statistics
import segfund_db
import sys
from datetime import datetime

# allow `from seg_fund_filters import ...` when run from any cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seg_fund_filters import (  # reuse proven helpers
    stability,
    rel_metrics,
    ANNUAL_COLS,
    TRAIL_COLS,
    MIN_YEARS,
)

DEFAULT_DB = "/root/.hermes/cache/seg_funds.db"
MIN_YR_COVERAGE = 10          # a benchmark year needs >=10 reporting series
MIN_PEER_COVERAGE = 5         # a peer-group year needs >=5 series


# --------------------------------------------------------------------------
# peer-group normalization (funds.category is free-text + has numeric junk)
# --------------------------------------------------------------------------
def norm_category(cat):
    c = (cat or "").strip().lower()
    if not c:
        return "Other"
    if "money market" in c or "high interest" in c:
        return "Money Market"
    if ("fixed" in c or "debt" in c or "high yield" in c or "multi-sector" in c
            or "bond" in c or "income" in c):
        return "Fixed Income"
    if "balanced" in c or "portfolio solution" in c or "tactical" in c:
        return "Balanced"
    if ("equity" in c or "stock" in c or "dividend" in c or "specialty" in c
            or "emerging" in c or "regional" in c):
        return "Equity"
    return "Other"


def nav_path_drawdown(row):
    """Max drawdown from a NAV path reconstructed from trailing total-return
    NAV levels (scale-invariant, so no price/NAV column required).

    Anchor = 100 at "now"; historical levels = 100 / (1 + r) at the KNOWN
    offsets of the trailing returns (1/3/5/10y). These are the REAL historical
    NAV levels implied by the trailing data, so the drawdown is a genuine
    NAV-path drawdown -- higher resolution than year-end calendar points and
    it works for funds with sparse annual history (the old code returned 0%
    for any fund with <2 calendar years, even when it had a real drawdown in
    its trailing window)."""
    pts = [(0, 100.0)]
    for col, off in (("return_1y", 1), ("return_3y", 3),
                     ("return_5y", 5), ("return_10y", 10)):
        v = row[col]
        if v is not None:
            pts.append((off, 100.0 / (1.0 + v / 100.0)))
    if len(pts) < 2:
        return None, "insufficient"
    pts.sort(key=lambda p: p[0])
    peak = pts[0][1]
    mdd = 0.0
    for _, lvl in pts:
        if lvl > peak:
            peak = lvl
        dd = (lvl - peak) / peak
        if dd < mdd:
            mdd = dd
    return round(-mdd * 100.0, 2), "nav-trailing"


# --------------------------------------------------------------------------
def max_drawdown(annual_vals):
    yrs = [y for y in annual_vals if annual_vals[y] is not None]
    if len(yrs) < 2:
        return None
    yrs.sort()
    idx = 100.0
    series = [idx]
    for y in yrs:
        idx *= (1.0 + annual_vals[y] / 100.0)
        series.append(idx)
    peak = series[0]
    mdd = 0.0
    for v in series:
        if v > peak:
            peak = v
        dd = (v - peak) / peak
        if dd < mdd:
            mdd = dd
    return round(-mdd * 100.0, 2)  # positive % decline


# --------------------------------------------------------------------------
# percentile rank -> 0-5 Lipper-style component score
# --------------------------------------------------------------------------
def pct_rank(values, target):
    vals = [v for v in values if v is not None]
    if not vals or target is None:
        return None
    below = sum(1 for v in vals if v <= target)
    return below / len(vals)


def comp_score(pctl, lower_is_better):
    if pctl is None:
        return None
    s = (1.0 - pctl) if lower_is_better else pctl
    return round(s * 5.0, 1)


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn, backend = segfund_db.get_conn()
    if backend == "mysql":
        # mysql.connector returns tuple rows by default; emulate sqlite3.Row
        # so the dict-style r["col"] access below works against prod too.
        _base_cursor = conn.cursor
        conn.cursor = lambda *a, **k: _base_cursor(dictionary=True)
    def q(sql, params=()):
        return segfund_db.run(conn, backend, sql, params)

    rows = q("""
        SELECT s.series_id, s.fund_id, s.series_code, s.series_name, s.mer,
               s.fund_status, s.return_1y, s.return_3y, s.return_5y,
               s.return_10y, s.return_incept,
               s.yr_2019, s.yr_2020, s.yr_2021, s.yr_2022, s.yr_2023,
               s.yr_2024, s.yr_2025,
               f.fund_name, f.category, c.short_name AS carrier
        FROM fund_series s
        JOIN funds f ON f.fund_id = s.fund_id
        JOIN carriers c ON c.carrier_id = f.carrier_id
    """).fetchall()

    benchmark_ids = {r["series_id"] for r in rows
                     if r["fund_status"] in (None, "Open", "Active")}

    # annual matrix for every series
    all_ann = {}
    all_years = set()
    for r in rows:
        d = {}
        for c in ANNUAL_COLS:
            v = r[c]
            if v is not None:
                d[int(c[3:])] = v
                all_years.add(int(c[3:]))
        all_ann[r["series_id"]] = d
    years_sorted = sorted(all_years)

    # market (all-fund) benchmark per year, from benchmark series only
    market = {}
    for y in years_sorted:
        vals = [all_ann[s][y] for s in benchmark_ids if y in all_ann.get(s, {})]
        if len(vals) >= MIN_YR_COVERAGE:
            market[y] = statistics.mean(vals)

    # per-peer-group benchmark per year
    by_cat = {}  # cat -> {series_id: {year:val}}
    for r in rows:
        cat = norm_category(r["category"])
        by_cat.setdefault(cat, {})[r["series_id"]] = all_ann[r["series_id"]]
    market_cat = {}
    for cat, smap in by_cat.items():
        market_cat[cat] = {}
        for y in years_sorted:
            vals = [d[y] for sid, d in smap.items()
                    if sid in benchmark_ids and y in d]
            if len(vals) >= MIN_PEER_COVERAGE:
                market_cat[cat][y] = statistics.mean(vals)

    # raw per-series metrics
    recs = []
    for r in rows:
        cat = norm_category(r["category"])
        rating, basis, n, spread, std, best, worst = stability(r)
        m_beta, m_alpha, m_corr, neg, contrary = rel_metrics(
            all_ann.get(r["series_id"], {}), market, years_sorted)
        s_beta, s_alpha, s_corr, _, _ = rel_metrics(
            all_ann.get(r["series_id"], {}), market_cat.get(cat, {}), years_sorted)
        mdd, mdd_basis = nav_path_drawdown(r)
        if mdd is None:
            mdd = max_drawdown(all_ann.get(r["series_id"], {}))
            mdd_basis = "annual" if mdd is not None else "insufficient"
        recs.append({
            "series_id": r["series_id"], "fund_id": r["fund_id"],
            "carrier": r["carrier"], "fund_name": r["fund_name"],
            "category": cat, "category_raw": r["category"],
            "fund_status": r["fund_status"], "mer": r["mer"],
            "volatility_rating": rating, "vol_basis": basis, "std": std, "ann_n": n,
            "max_drawdown": mdd,
            "drawdown_basis": mdd_basis,
            "market_beta": m_beta, "market_alpha": m_alpha, "market_corr": m_corr,
            "sector_beta": s_beta, "sector_alpha": s_alpha, "sector_corr": s_corr,
            "ret5": r["return_5y"], "preservation": (1.0 - mdd / 100.0) if mdd is not None else None,
        })

    # Lipper-style component scores: rank within peer group
    comp_lists = {c: {"ret5": [], "std": [], "pres": [], "mer": []} for c in by_cat}
    for x in recs:
        cl = comp_lists[x["category"]]
        cl["ret5"].append((x["series_id"], x["ret5"]))
        cl["std"].append((x["series_id"], x["std"]))
        cl["pres"].append((x["series_id"], x["preservation"]))
        cl["mer"].append((x["series_id"], x["mer"]))

    scores = {}
    for cat, cl in comp_lists.items():
        for key, lower in (("ret5", False), ("std", True), ("pres", False), ("mer", True)):
            vals = [v for _, v in cl[key]]
            for sid, v in cl[key]:
                p = pct_rank(vals, v)
                scores.setdefault(sid, {})[key] = comp_score(p, lower)

    for x in recs:
        sc = scores.get(x["series_id"], {})
        tr = sc.get("ret5")
        co = sc.get("std")
        pr = sc.get("pres")
        ex = sc.get("mer")
        comps = [v for v in (tr, co, pr, ex) if v is not None]
        overall = round(statistics.mean(comps), 1) if len(comps) >= 2 else None
        x["lipper_total_return"] = tr
        x["lipper_consistent"] = co
        x["lipper_preservation"] = pr
        x["lipper_expense"] = ex
        x["lipper_style_score"] = overall

    if args.dry_run:
        print("[DRY-RUN] would write %d series to seg_fund_metrics" % len(recs))
        conn.close()
        return

    q("DROP TABLE IF EXISTS seg_fund_metrics")
    q("""
        CREATE TABLE IF NOT EXISTS seg_fund_metrics (
            series_id INTEGER PRIMARY KEY, fund_id INTEGER, carrier TEXT,
            fund_name TEXT, category TEXT, category_raw TEXT, fund_status TEXT,
            mer REAL, volatility_rating TEXT, vol_basis TEXT, std REAL, ann_n INTEGER,
            max_drawdown REAL, drawdown_basis TEXT,
            market_beta REAL, market_alpha REAL, market_corr REAL,
            sector_beta REAL, sector_alpha REAL, sector_corr REAL,
            lipper_total_return REAL, lipper_consistent REAL,
            lipper_preservation REAL, lipper_expense REAL, lipper_style_score REAL,
            computed_at TEXT)
    """)
    now = datetime.utcnow().isoformat(sep=" ")
    for x in recs:
        q("""
            INSERT INTO seg_fund_metrics VALUES (
                :series_id,:fund_id,:carrier,:fund_name,:category,:category_raw,
                :fund_status,:mer,:volatility_rating,:vol_basis,:std,:ann_n,
                :max_drawdown,:drawdown_basis,:market_beta,:market_alpha,:market_corr,
                :sector_beta,:sector_alpha,:sector_corr,:lipper_total_return,
                :lipper_consistent,:lipper_preservation,:lipper_expense,
                :lipper_style_score,:computed_at)
        """, {**x, "computed_at": now})
    conn.commit()

    # summary
    n = len(recs)
    with_mkt = sum(1 for x in recs if x["market_beta"] is not None)
    with_sec = sum(1 for x in recs if x["sector_beta"] is not None)
    with_mdd = sum(1 for x in recs if x["max_drawdown"] is not None)
    with_lip = sum(1 for x in recs if x["lipper_style_score"] is not None)
    print("DB: %s" % args.db)
    print("Computed %d series" % n)
    print("  market beta/alpha/corr : %d" % with_mkt)
    print("  sector beta/alpha/corr : %d" % with_sec)
    print("  max drawdown          : %d" % with_mdd)
    print("  Lipper-style score     : %d" % with_lip)
    conn.close()


if __name__ == "__main__":
    main()
