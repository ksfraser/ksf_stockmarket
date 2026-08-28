#!/usr/bin/env python3
"""
Seed ivari seg-fund calendar-year (yr_2019..yr_2025) returns from Fund Facts PDFs.

Source: ivari.ca Fund Facts PDFs (ivari.ca/files/<CODE>.pdf), one per investment-product
post (custom post type ffpu_investment_prod). The PDFs are discovered via the WordPress
REST media endpoint (parent = post id) and downloaded with curl (the /files/ path is NOT
Cloudflare-gated). Calendar-year returns live in the "Year-by-year returns" chart.

Most Fund Facts charts are text and parse directly. A few (GS/GS2 "Class 2" funds) embed
the chart as an IMAGE -> those are skipped here (logged as OCR-needed) and handled separately.

Matching: PDF (family, core-description) -> DB (family, core-description).
  - family: BIG / GS/GS2 / GS3 / imaxxGIF / NN IP / 5FL / MM / None
  - core-description excludes family tokens AND "Class 2" (Class 2 is the same underlying
    fund, just a different sales-charge series, so its returns are identical).
This yields a clean 1:1 family mapping and correct per-family returns.

Idempotent: only UPDATEs existing fund_series rows (no inserts).

DB target: production MySQL via segfund_db.get_conn() (falls back to local SQLite cache).
"""
import re, fitz, sys
from pathlib import Path
import segfund_db

PDF_DIR = Path('/root/.hermes/cache/ivari_ff/pdfs')
CARRIER = 9
DRY = '--apply' not in sys.argv


def fam(name):
    n = name.lower()
    if 'gs/gs2' in n:
        return 'gs/gs2'
    if 'gs3' in n:
        return 'gs3'
    if 'imaxx' in n:
        return 'imaxxgif'
    if 'nn ip' in n or 'nnip' in n:
        return 'nn ip'
    if '5fl' in n:
        return '5fl'
    if 'big' in n:
        return 'big'
    if ' mm' in n or n.endswith('mm'):
        return 'mm'
    return None


def norm_core(name):
    n = name.lower()
    n = re.sub(r'^ivari\s*', '', n)
    n = re.sub(r'\b(gs/gs2|gs2|gs3|imaxxgif|imaxx gif|nn ip|nnip|5fl|big|mm)\b', ' ', n)
    n = re.sub(r'class\s*\d+', ' ', n)
    n = re.sub(r'\b\d+/\d+\b', ' ', n)
    n = re.sub(r'[^a-z0-9 ]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def parse_pdf(path):
    doc = fitz.open(str(path))
    txt = ''.join(p.get_text() for p in doc)
    m = re.search(r'ivari\s+(.{5,90}?)\s+(All information is as of|QUICK FACTS|What does the fund|This Fund Facts|Date fund created)', txt)
    desc = m.group(1).strip() if m else None
    if not desc:
        return None
    ay = re.search(r'as of December 31,?\s*(\d{4})', txt, re.I)
    as_at = f"{ay.group(1)}-12-31" if ay else None
    yr = {}
    yb = re.search(r'Year-by-year returns', txt, re.I)
    if yb:
        region = txt[yb.start():yb.start() + 500]
        years = re.findall(r'(20(?:1[5-9]|2[0-5]))', region)
        rets = re.findall(r'(-?\d+\.\d+)\s*%', region)
        for y, r in zip(years, rets):
            yr[int(y)] = float(r)
    return {'desc': desc, 'fam': fam(desc), 'core': norm_core('ivari ' + desc),
            'as_at': as_at, 'yr': yr}


def main():
    conn, backend = segfund_db.get_conn()

    def q(sql, params=()):
        return segfund_db.run(conn, backend, sql, params)

    funds = q("SELECT fund_id, fund_name FROM funds WHERE carrier_id=?", (CARRIER,)).fetchall()
    key_to_ids = {}
    for fid, fn in funds:
        key_to_ids.setdefault((fam(fn), norm_core(fn)), []).append(fid)

    plan = []
    skipped_empty = []
    unmatched_pdf = []
    for fn in sorted(PDF_DIR.glob('*.pdf')):
        p = parse_pdf(fn)
        if not p:
            unmatched_pdf.append((fn.name, 'NO DESC'))
            continue
        k = (p['fam'], p['core'])
        ids = key_to_ids.get(k, [])
        if not ids:
            unmatched_pdf.append((fn.name, p['desc']))
            continue
        if not p['yr']:
            skipped_empty.append((fn.name, p['desc'], ids))
            continue
        plan.append((fn.name, p['desc'], p['fam'], ids, p['yr'], p['as_at']))

    all_ids = [fid for fid, _ in funds]
    covered = set(i for _, _, _, ids, _, _ in plan for i in ids)
    print(f"DRY_RUN={DRY}  backend={backend}")
    print(f"PDFs with data (will upsert): {len(plan)}")
    print(f"Skipped (empty yr / image chart -> OCR needed): {len(skipped_empty)}")
    print(f"Unmatched PDFs (no DB fund): {len(unmatched_pdf)}")
    print(f"DB ivari funds: {len(all_ids)} | covered: {len(covered)} | uncovered: {len(set(all_ids) - covered)}")
    print("Uncovered fund_ids:", sorted(set(all_ids) - covered))
    print("\nSkipped-empty (OCR needed):")
    for s in skipped_empty:
        print("  ", s)
    print("\nUnmatched PDFs:")
    for u in unmatched_pdf:
        print("  ", u)

    if DRY:
        return

    # Ensure every matched fund has at least one fund_series row to hold the
    # calendar-year data. The trailing-returns seed only created series rows for
    # funds present in the rates portal, so ~27 ivari funds (mostly GS3/imaxxGIF
    # families) have a funds row but no fund_series row. Create a minimal one.
    fname = {fid: fn for fid, fn in funds}
    update_ids = set(i for _, _, _, ids, _, _ in plan for i in ids)
    created = 0
    for fid in update_ids:
        if q("SELECT COUNT(*) FROM fund_series WHERE fund_id=?", (fid,)).fetchone()[0] == 0:
            q(
                "INSERT INTO fund_series (fund_id, series_code, series_name, fund_status) "
                "VALUES (?,?,?,?)",
                (fid, 'DEFAULT', fname.get(fid), 'Open'))
            created += 1
    conn.commit()
    print(f"  ensured series rows: created {created} new (previously-missing) series rows")

    for fn, desc, f, ids, yr, as_at in plan:
        vals = [yr.get(2019), yr.get(2020), yr.get(2021), yr.get(2022),
                yr.get(2023), yr.get(2024), yr.get(2025), as_at]
        for fid in ids:
            q(
                "UPDATE fund_series SET yr_2019=?,yr_2020=?,yr_2021=?,yr_2022=?,"
                "yr_2023=?,yr_2024=?,yr_2025=?,as_at_date=? WHERE fund_id=?",
                vals + [fid])
    conn.commit()
    print(f"\nAPPLIED: {len(plan)} PDF mappings -> {len(update_ids)} fund rows updated "
          f"({created} newly created).")


if __name__ == '__main__':
    main()
