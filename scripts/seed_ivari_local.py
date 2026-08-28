#!/usr/bin/env python3
"""
Seed ivari segregated funds (TRAILING returns) into the analysis store from the
ivari "Net Rates of Return and Prices" portal at https://rates.ivari.ca/en.

The portal is an ASP.NET MVC page using unobtrusive AJAX. The "Investment products"
-> "Rates of Return - Seg. Funds" view exposes 7 seg-fund families, each with a
*RATE product code (BigRATE, GS2RATE, TIPs, IMAXXRATE, _5FLRATE, TGIFRATE, NNIP_rate).
Selecting a product rewrites the form action to /Home/<code>/en; submitting (POST) with
the ASP.NET __RequestVerificationToken returns an HTML tablesaw table of trailing
returns (1yr / 2yr / 3yr / 5yr / 10yr / since-inception) per fund.

NOTE: this view exposes TRAILING returns only. They map to fund_series
return_1y / return_3y / return_5y / return_10y / return_incept. There is no
return_2y column in the schema, so the "2 yrs" value is dropped. Calendar-year
returns (yr_2019..yr_2025) are NOT on this portal and would require the Fund Facts
PDFs. Trailing data is still valuable and matches the return_* columns populated for
RBC / Manulife / iA.

DB target: production MySQL via segfund_db.get_conn() (falls back to local SQLite cache).
"""
import os
import re
import json
import http.cookiejar
import urllib.request
import urllib.parse
import segfund_db

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
IVARI_CARRIER_ID = 9
BASE = "https://rates.ivari.ca"
UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Referer": BASE + "/en",
}
# Fallback if the dynamic product list cannot be fetched.
FALLBACK_PRODUCTS = [
    ("BigRATE", "Balanced Investment Growth (BIG)"),
    ("GS2RATE", "GROWSafe and GROWSafe²"),
    ("TIPs", "GROWSafe³"),
    ("IMAXXRATE", "imaxxGIF"),
    ("_5FLRATE", "Five for Life"),
    ("TGIFRATE", "ivari Guaranteed Investment Funds"),
    ("NNIP_rate", "NN IP Segregated Funds"),
]

# Map portal header label -> fund_series column. None means "no column, drop".
COL_MAP = {
    "1 yr": "return_1y",
    "2 yrs": None,
    "3 yrs": "return_3y",
    "5 yrs": "return_5y",
    "10 yrs": "return_10y",
    "since inception*": "return_incept",
}


def category(name):
    n = name.lower()
    if any(k in n for k in ("bond", "fixed income", "mortgage", "income")):
        return "Fixed Income"
    if any(k in n for k in ("money", "cash", "treasury", "savings")):
        return "Money Market"
    if any(k in n for k in ("balanced", "allocation", "portfolio", "conservative", "moderate")):
        return "Balanced"
    if any(k in n for k in ("equity", "growth", "stock", "global", "dividend", "index", "focus")):
        return "Equity"
    return "Other"


def guarantee(name):
    m = re.search(r"(\d{2})/(\d{2})", name)
    return int(m.group(1)) if m else None


def make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get_token(opener):
    req = urllib.request.Request(BASE + "/en", headers=UA)
    resp = opener.open(req, timeout=60)
    html = resp.read().decode("utf-8", "ignore")
    m = re.search(r'__RequestVerificationToken[^>]*value="([^"]+)"', html)
    if not m:
        raise RuntimeError("could not find __RequestVerificationToken on %s/en" % BASE)
    return m.group(1)


def get_products(opener):
    url = BASE + "/Home/GetProductsForFilter/en?filterID=RatesOfReturn"
    req = urllib.request.Request(url, headers=UA)
    try:
        resp = opener.open(req, timeout=60)
        data = json.loads(resp.read().decode("utf-8", "ignore"))
        prods = [(d["optionValue"], d.get("optionDescription", "")) for d in data]
        if prods:
            return prods
    except Exception as e:  # noqa: BLE001
        print("GetProductsForFilter failed (%s); using fallback list" % e)
    return FALLBACK_PRODUCTS


def parse_rates_html(html):
    """Return (as_at_date, [(fund_name, cols, vals), ...])."""
    m = re.search(r"Rates in effect as of\s*([\d/]+)", html, re.I)
    as_at = m.group(1) if m else None
    header = re.search(r"<thead>(.*?)</thead>", html, re.S)
    cols = []
    if header:
        cols = [re.sub(r"<[^>]+>", "", c).strip().lower()
                for c in re.findall(r"<th[^>]*>(.*?)</th>", header.group(1), re.S)]
        cols = [c for c in cols if c and c != "fund name"]  # drop the label column
    tbody = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    body = tbody.group(1) if tbody else html
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        th = re.search(r"<th[^>]*>(.*?)</th>", tr, re.S)
        if not th:
            continue
        name = re.sub(r"<[^>]+>", "", th.group(1)).strip()
        if not name:
            continue
        vals = []
        for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S):
            txt = re.sub(r"<[^>]+>", "", td).strip().replace("%", "").replace(",", "")
            try:
                vals.append(float(txt))
            except ValueError:
                vals.append(None)
        rows.append((name, cols, vals))
    return as_at, rows


def main():
    opener = make_opener()
    token = get_token(opener)
    products = get_products(opener)
    print("ivari RatesOfReturn products: %d" % len(products))

    conn, backend = segfund_db.get_conn()

    def q(sql, params=()):
        return segfund_db.run(conn, backend, sql, params)

    inserted = updated = total_series = 0

    for code, desc in products:
        data = urllib.parse.urlencode({
            "ShowList": "IP",
            "View_Category": "RatesOfReturn",
            "View": code,
            "Submit": "Submit",
            "__RequestVerificationToken": token,
        }).encode()
        req = urllib.request.Request(BASE + "/Home/%s/en" % code, data=data, headers=UA)
        try:
            resp = opener.open(req, timeout=60)
        except Exception as e:  # noqa: BLE001
            print("  POST %s failed: %s" % (code, e))
            continue
        html = resp.read().decode("utf-8", "ignore")
        as_at, rows = parse_rates_html(html)
        print("  %-12s %-42s -> %d fund rows (as_at=%s)" % (code, desc[:42], len(rows), as_at))

        for name, cols, vals in rows:
            if not vals:
                continue
            ret = {}
            for i, c in enumerate(cols):
                if i < len(vals) and c in COL_MAP and COL_MAP[c]:
                    ret[COL_MAP[c]] = vals[i]
            if not ret:
                continue
            gua = guarantee(name)
            row = q("SELECT fund_id FROM funds WHERE carrier_id=? AND fund_name=?",
                    (IVARI_CARRIER_ID, name)).fetchone()
            if row:
                fid = row[0]
            else:
                ins = q(
                    "INSERT INTO funds (family_id, carrier_id, fund_name, fund_name_clean, category, is_active) "
                    "VALUES (0,?,?,?,?,1)",
                    (IVARI_CARRIER_ID, name, name, category(name)))
                fid = ins.lastrowid
                inserted += 1
            series_code = "G%d" % gua if gua else "DEFAULT"
            srow = q("SELECT series_id FROM fund_series WHERE fund_id=? AND series_code=?",
                     (fid, series_code)).fetchone()
            if srow:
                q(
                    "UPDATE fund_series SET return_1y=?,return_3y=?,return_5y=?,return_10y=?,"
                    "return_incept=?,guarantee_pct=?,as_at_date=? WHERE series_id=?",
                    (ret.get("return_1y"), ret.get("return_3y"), ret.get("return_5y"),
                     ret.get("return_10y"), ret.get("return_incept"), gua, as_at, srow[0]))
                updated += 1
            else:
                q(
                    "INSERT INTO fund_series (fund_id, series_code, series_name, load_type, mer, "
                    "guarantee_pct, return_1y, return_3y, return_5y, return_10y, return_incept, as_at_date) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (fid, series_code, name, None, None, gua,
                     ret.get("return_1y"), ret.get("return_3y"), ret.get("return_5y"),
                     ret.get("return_10y"), ret.get("return_incept"), as_at))
            total_series += 1

    conn.commit()
    have = q(
        "SELECT COUNT(*) FROM fund_series fs JOIN funds f ON f.fund_id=fs.fund_id "
        "WHERE f.carrier_id=? AND return_1y IS NOT NULL", (IVARI_CARRIER_ID,)).fetchone()[0]
    if total_series > 0:
        q("UPDATE carriers SET scrape_url=?, scrape_status='done' WHERE carrier_id=?",
          (BASE + "/en", IVARI_CARRIER_ID))
        conn.commit()
    # defensive cleanup: drop any legacy/dup series whose code equals the fund name
    q(
        "DELETE FROM fund_series WHERE series_id IN ("
        "SELECT fs.series_id FROM fund_series fs JOIN funds f ON f.fund_id=fs.fund_id "
        "WHERE f.carrier_id=? AND fs.series_code = f.fund_name)", (IVARI_CARRIER_ID,))
    conn.commit()
    conn.close()
    print("inserted %d new funds, updated %d series; ivari series with return_1y: %d "
          "(total series seen: %d)" % (inserted, updated, have, total_series))


if __name__ == "__main__":
    main()
