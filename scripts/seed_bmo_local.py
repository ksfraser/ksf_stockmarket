#!/usr/bin/env python3
"""
Seed BMO segregated funds into the LOCAL analysis store (fund_series + funds) so the
volatility / beta / class-eligibility screen can include BMO.

Source of fields:
  - production MariaDB seg_funds (carrier='BMO'): fund_name, category, mer, trailing returns, launch_date
  - scraped BMO Lipper Calendar-Year Returns (data/bmo_calendar_2026_page{1,2,3}.txt): yr_2019..yr_2025

Local store is missing BMO entirely (its `funds` table covers other carriers only), so this
inserts BMO from scratch (idempotent: clears existing BMO first).

NOTE: production min_initial_investment is NULL for BMO, so series minimums use the
class heuristic (Class F / Prestige / Plus => fee-based ~100k; Class A => 0).
"""
import os, re, sys, decimal
import segfund_db

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
LOCAL_DB = os.environ.get("SEG_FUNDS_DB", "/root/.hermes/cache/seg_funds.db")
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
PAGES = [os.path.join(DATA, f"bmo_calendar_2026_page{i}.txt") for i in (1, 2, 3)]
BMO_CARRIER_ID = 3


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def load_portal():
    data = {}
    for p in PAGES:
        if not os.path.exists(p):
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
                file_years = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]
                for yr, v in zip(file_years, vals):
                    if yr not in YEARS:
                        continue
                    v = v.strip()
                    rec[yr] = None if v in ("", "-") else float(v)
                data[name] = rec
                data[norm(name)] = rec
    return data


def parse_guarantee(name):
    m = re.search(r"(\d{2})/(\d{2})", name)
    return int(m.group(1)) if m else None


def derive_min(name):
    n = name.lower()
    if "class f" in n or "prestige" in n or "plus" in n:
        return 100000
    return 0


def fnum(x):
    if x is None:
        return None
    if isinstance(x, decimal.Decimal):
        return float(x)
    return x


def main():
    portal = load_portal()
    conn, backend = segfund_db.get_conn()

    def q(sql, params=()):
        return segfund_db.run(conn, backend, sql, params)

    prows = q(
        """SELECT fund_name, carrier, series, category, mer, mer_pct, load_type,
                  min_initial_investment, launch_date, return_1yr, return_3yr, return_5yr,
                  return_10yr, return_inception, fund_code
           FROM seg_funds WHERE carrier='BMO'"""
    ).fetchall()
    print(f"production BMO rows: {len(prows)}")

    fids = [r[0] for r in q("SELECT fund_id FROM funds WHERE carrier_id=?", (BMO_CARRIER_ID,)).fetchall()]
    if fids:
        q("DELETE FROM fund_series WHERE fund_id IN (%s)" % ",".join("?" * len(fids)), fids)
        q("DELETE FROM funds WHERE carrier_id=?", (BMO_CARRIER_ID,))
        print(f"cleared {len(fids)} existing local BMO funds")

    ins_f = "INSERT INTO funds (family_id, carrier_id, fund_name, fund_name_clean, category, inception_date, is_active) VALUES (0,?,?,?,?,?,1)"
    ins_s = """INSERT INTO fund_series
              (fund_id, series_code, series_name, load_type, mer, guarantee_pct,
               return_1y, return_3y, return_5y, return_10y, return_incept,
               yr_2019, yr_2020, yr_2021, yr_2022, yr_2023, yr_2024, yr_2025)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""

    matched = 0
    unmatched = []
    for p in prows:
        fname = p[0]
        rec = portal.get(fname) or portal.get(norm(fname))
        if not rec:
            unmatched.append(fname)
            continue
        matched += 1
        category = p[3]
        mer = fnum(p[4])
        launch = p[8]
        ret1y, ret3y, ret5y, ret10y, retincept = (fnum(p[9]), fnum(p[10]), fnum(p[11]), fnum(p[12]), fnum(p[13]))
        gua = parse_guarantee(fname)
        ins = q(ins_f, (BMO_CARRIER_ID, fname, fname, category, launch))
        fid = ins.lastrowid
        yr = [rec.get(y) for y in YEARS]
        q(ins_s, (fid, p[2] or p[14], fname, p[6], mer, gua,
                   ret1y, ret3y, ret5y, ret10y, retincept, *yr))
    conn.commit()
    conn.close()
    print(f"seeded matched: {matched}  unmatched: {len(unmatched)}")
    for u in unmatched[:20]:
        print("  unmatched:", u)


if __name__ == "__main__":
    main()
