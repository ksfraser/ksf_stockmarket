#!/usr/bin/env python3
"""Extract Canada Life calendar-year returns from the Fundata server-rendered HTML.
No browser/JS needed: the table is in the static HTML. Maps header text -> column
so there is zero positional guessing.
"""
import json, re, sys
from bs4 import BeautifulSoup

HTML = "/tmp/cl_page.html"
OUT = "/tmp/cl_cal.json"

YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

def norm_header(t):
    # strip sort hints / footnotes
    t = re.sub(r"\(Click to sort[^)]*\)", "", t)
    return t.strip()

with open(HTML, encoding="utf-8", errors="replace") as f:
    soup = BeautifulSoup(f.read(), "lxml")

# Find the table whose header contains a calendar-year cell (e.g. "2025")
target = None
for table in soup.find_all("table"):
    heads = [norm_header(h.get_text(" ", strip=True)) for h in table.find_all("th")]
    if any(h in ("2025", "2024") for h in heads) and any(h == "2016" for h in heads):
        target = table
        header = heads
        break

if target is None:
    print("ERROR: calendar-year table not found", file=sys.stderr)
    sys.exit(1)

print(f"table found; header cols={len(header)}", file=sys.stderr)
# Build column index map
idx = {}
for i, h in enumerate(header):
    if re.fullmatch(r"(20[12]\d)", h):
        idx[int(h)] = i
    elif h.lower().startswith("fund name"):
        idx["name"] = i
    elif h.startswith("MER"):
        idx["mer"] = i
print("mapped years:", sorted(idx.get(y, "?") for y in YEARS if y in idx), file=sys.stderr)

name_i = idx["name"]
mer_i = idx.get("mer")

rows = []
for tr in target.find_all("tr"):
    cells = tr.find_all(["td", "th"])
    if len(cells) < max(idx.values()) + 1:
        continue
    name = cells[name_i].get_text(" ", strip=True) if name_i < len(cells) else ""
    if not name or "Fund name" in name:
        continue
    rec = {"name": name}
    for y in YEARS:
        ci = idx.get(y)
        v = cells[ci].get_text(" ", strip=True) if ci is not None and ci < len(cells) else ""
        rec[f"yr_{y}"] = v
    if mer_i is not None and mer_i < len(cells):
        rec["mer"] = cells[mer_i].get_text(" ", strip=True)
    rows.append(rec)

print(f"extracted {len(rows)} fund rows", file=sys.stderr)
with open(OUT, "w") as f:
    json.dump(rows, f, indent=1)
print(OUT)
