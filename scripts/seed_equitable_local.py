#!/usr/bin/env python3
"""
Seed Equitable Life segregated-fund calendar-year returns (2019-2025) + MER
into the LOCAL SQLite DB (/root/.hermes/cache/seg_funds.db).

Source: Equitable Fundata performance page (server-rendered HTML table):
    https://equitablelife.fundata.com/?language=en
Table exposes columns: 2016..2025 calendar returns, MER (%), Fund Category,
and per-series "Fund Facts PDF Report" links (stable fund id in the URL).

No Fund Facts PDFs are downloaded -- the calendar returns are parsed directly
from the HTML table, consistent with the Canada Life Fundata approach.

Idempotent: series are upserted SELECT-first on (fund_id, series_code), so the
script can be re-run safely without creating duplicate rows.

Usage:
    curl -s -A "Mozilla/5.0" "https://equitablelife.fundata.com/?language=en" -o /tmp/eq_fundata.html
    python3 scripts/seed_equitable_local.py /tmp/eq_fundata.html
    python3 scripts/seed_equitable_local.py /tmp/eq_fundata.html --dry-run   # no writes
"""
import sys
import re
import segfund_db
from bs4 import BeautifulSoup

DB_PATH = "/root/.hermes/cache/seg_funds.db"
CARRIER_ID = 10  # Equitable Life (per references/carrier_seg_fund_sources.md)
AS_AT = "2026-08-23"

# column index within each <tr>'s <td> list (from the Fundata table layout)
NAME_IDX = 2
YEAR_IDX = {2025: 11, 2024: 12, 2023: 13, 2022: 14, 2021: 15, 2020: 16, 2019: 17}
MER_IDX = 26
CAT_IDX = 29
RES_IDX = 30  # Resources & Fund Facts cell (holds the Fund Facts link)


def to_float(v):
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "-", "\u2014", "NA", "N/A", "n/a"):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def extract_rows(html_path):
    html = open(html_path, encoding="utf-8", errors="replace").read()
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        raise SystemExit("No <table> found in %s" % html_path)
    records = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 30:
            continue  # header rows use <th> / have fewer cells
        name = tds[NAME_IDX].get_text(strip=True)
        if not name or "No result" in name or name == "Favourites":
            continue
        rec = {
            "name": name,
            "mer": to_float(tds[MER_IDX].get_text(strip=True)),
            "category": tds[CAT_IDX].get_text(strip=True) or None,
        }
        for y, idx in YEAR_IDX.items():
            rec["yr_%d" % y] = to_float(tds[idx].get_text(strip=True))
        ff_id = ""
        for a in tds[RES_IDX].find_all("a"):
            m = re.search(r"FundFacts/(\d+)", a.get("href", ""))
            if m:
                ff_id = m.group(1)
                break
        # fallback matches the originally-seeded EQ* codes (no zero-pad, pre-append count)
        # so re-runs upsert rather than duplicate the 19 EQ* series already in the DB.
        rec["series_code"] = ("FF" + ff_id) if ff_id else ("EQ%d" % len(records))
        records.append(rec)
    return records


def seed(records, dry_run=False):
    conn, backend = segfund_db.get_conn()
    def q(sql, params=()):
        return segfund_db.run(conn, backend, sql, params)
    n_fund = n_series_ins = n_series_upd = 0
    for r in records:
        res = q(
            "INSERT OR IGNORE INTO funds (carrier_id, fund_name, category) VALUES (?,?,?)",
            (CARRIER_ID, r["name"], r["category"]),
        )
        if res.rowcount:
            n_fund += 1
        row = q(
            "SELECT fund_id FROM funds WHERE carrier_id=? AND fund_name=?",
            (CARRIER_ID, r["name"]),
        ).fetchone()
        if not row:
            continue
        fund_id = row[0]
        # SELECT-first idempotent series upsert (key on fund_id + series_code)
        srow = q(
            "SELECT series_id FROM fund_series WHERE fund_id=? AND series_code=?",
            (fund_id, r["series_code"]),
        ).fetchone()
        if srow:
            if not dry_run:
                q(
                    """UPDATE fund_series SET series_name=?, mer=?, yr_2019=?, yr_2020=?, yr_2021?,
                       yr_2021=?, yr_2022=?, yr_2023=?, yr_2024=?, yr_2025=?,
                       as_at_date=?, updated_at=datetime('now')
                       WHERE series_id=?""",
                    (r["name"], r["mer"], r["yr_2019"], r["yr_2020"], r["yr_2021"],
                     r["yr_2022"], r["yr_2023"], r["yr_2024"], r["yr_2025"], AS_AT, srow[0]),
                )
            n_series_upd += 1
        else:
            if not dry_run:
                q(
                    """INSERT INTO fund_series
                       (fund_id, series_code, series_name, mer, yr_2019, yr_2020, yr_2021,
                        yr_2022, yr_2023, yr_2024, yr_2025, as_at_date, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    (fund_id, r["series_code"], r["name"], r["mer"],
                     r["yr_2019"], r["yr_2020"], r["yr_2021"], r["yr_2022"],
                     r["yr_2023"], r["yr_2024"], r["yr_2025"], AS_AT),
                )
            n_series_ins += 1
    if not dry_run:
        conn.commit()
    conn.close()
    return n_fund, n_series_ins, n_series_upd


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "/tmp/eq_fundata.html"
    dry_run = "--dry-run" in sys.argv
    recs = extract_rows(src)
    print("parsed %d series" % len(recs))
    nf, ns_ins, ns_upd = seed(recs, dry_run=dry_run)
    if dry_run:
        print("[DRY-RUN] would insert funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
    else:
        print("inserted/updated funds: %d, series insert: %d, series update: %d" % (nf, ns_ins, ns_upd))
