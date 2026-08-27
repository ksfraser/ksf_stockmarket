#!/usr/bin/env python3
"""
Seed ivari segregated-fund NAMES + current daily NAVs from the rates portal:

    POST https://rates.ivari.ca/Home/<Product>/en
      form: ShowList=IP, View_Category=RatesOfReturn, View=<Product>,
            __RequestVerificationToken=<from /en>, Submit=Go
    -> server-rendered tablesaw table in #result (latest ~week of daily unit values)

The portal's "Rates of Return - Seg. Funds" (and UnitValues) view returns only the
last ~week of daily unit values per fund family, so this seeder captures:
  - the full ivari seg-fund roster (fund_name) across the 7 Investment-product families
  - current NAV (price) + price_date + daily-change %

Calendar-year returns (yr_2019..yr_2025) are NOT exposed on this portal -- they live
in ivari's 126 public Fund Facts PDFs and are added in a later pass
(see references/carrier_seg_fund_sources.md, ivari section). Until then, ivari series
carry price/NAV but NULL annual returns, so the Lipper screen will leave them unscored.

Idempotent: SELECT-first upsert on (fund_id, series_code). Re-runnable.

Usage:
    python3 scripts/seed_ivari_local.py                 # live write
    python3 scripts/seed_ivari_local.py --dry-run       # no writes
"""
import sys
import re
import sqlite3
import requests
from bs4 import BeautifulSoup

DB_PATH = "/root/.hermes/cache/seg_funds.db"
CARRIER_ID = 9  # ivari (per references/carrier_seg_fund_sources.md)
BASE = "https://rates.ivari.ca"
PRODUCTS = ["BigUNIT", "GS2UNIT", "GS3UNIT", "IMAXXUNIT", "_5FLUNIT", "TGIFUNIT", "NNIP_unit"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def clean(s):
    return re.sub(r"\s+", " ", str(s)).replace("\xa0", " ").strip()


def parse_date_col(h):
    """'08/26/2026' -> '2026-08-26' (None if not a date)."""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", h or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else None


def to_num(v):
    m = re.search(r"-?\d+\.?\d*", v or "")
    return float(m.group()) if m else None


def fetch(session, token, product):
    data = {
        "ShowList": "IP",
        "View_Category": "RatesOfReturn",
        "View": product,
        "__RequestVerificationToken": token,
        "Submit": "Go",
    }
    r = session.post(f"{BASE}/Home/{product}/en", data=data)
    if r.status_code != 200:
        print(f"  ! {product}: HTTP {r.status_code}", file=sys.stderr)
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    t = soup.find("table")
    if not t:
        return []
    header = [c.get_text(" ", strip=True) for c in t.find("tr").find_all(["th", "td"])]
    date_cols = [(i, h) for i, h in enumerate(header) if parse_date_col(h)]
    if not date_cols:
        return []
    last_i, last_h = date_cols[-1]
    daily_i = header.index("Daily Chg.") if "Daily Chg." in header else None
    out = []
    for tr in t.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        name = clean(cells[0])
        if not name:
            continue
        out.append({
            "name": name,
            "price": to_num(cells[last_i]) if last_i < len(cells) else None,
            "price_date": parse_date_col(last_h),
            "price_change_1d_pct": to_num(cells[daily_i]) if daily_i is not None and daily_i < len(cells) else None,
        })
    return out


def seed(records, dry_run=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n_fund = n_ins = n_upd = 0
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
        code = r["name"]  # portal gives no separate series code; fund name is unique per fund
        cur.execute(
            "SELECT series_id FROM fund_series WHERE fund_id=? AND series_code=?",
            (fund_id, code),
        )
        srow = cur.fetchone()
        if srow:
            if not dry_run:
                cur.execute(
                    """UPDATE fund_series SET series_name=?, price=?, price_date=?,
                       price_change_1d_pct=?, as_at_date=?, updated_at=datetime('now')
                       WHERE series_id=?""",
                    (r["name"], r["price"], r["price_date"], r["price_change_1d_pct"],
                     r["price_date"], srow[0]),
                )
            n_upd += 1
        else:
            if not dry_run:
                cur.execute(
                    """INSERT INTO fund_series
                       (fund_id, series_code, series_name, price, price_date,
                        price_change_1d_pct, as_at_date, updated_at)
                       VALUES (?,?,?,?,?,?,?,datetime('now'))""",
                    (fund_id, code, r["name"], r["price"], r["price_date"],
                     r["price_change_1d_pct"], r["price_date"]),
                )
            n_ins += 1
    if not dry_run:
        conn.commit()
    conn.close()
    return n_fund, n_ins, n_upd


def main():
    dry_run = "--dry-run" in sys.argv
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    r = session.get(f"{BASE}/en")
    tok = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', r.text)
    if not tok:
        print("FATAL: could not read __RequestVerificationToken", file=sys.stderr)
        sys.exit(1)
    token = tok.group(1)
    all_recs = []
    for p in PRODUCTS:
        recs = fetch(session, token, p)
        print(f"{p}: {len(recs)} funds", file=sys.stderr)
        all_recs.extend(recs)
    print(f"parsed {len(all_recs)} series total")
    nf, ni, nu = seed(all_recs, dry_run=dry_run)
    if dry_run:
        print(f"[DRY-RUN] funds inserted {nf}, series insert {ni}, series update {nu}")
    else:
        print(f"funds inserted {nf}, series insert {ni}, series update {nu}")


if __name__ == "__main__":
    main()
