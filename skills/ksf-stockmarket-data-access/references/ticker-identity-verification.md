# Stock Identity Verification Before Analysis — 2026-09-18 Session

## The problem

A 14-stock ATR sweep analysis produced **six wrong ticker→company identities** (6/14 = 43% error rate). Each one was written up for the wrong company. Root cause: assumed the company from the ticker, searched for that wrong assumption, and trusted whatever came back instead of verifying identity from the DB price data first.

| Ticker | Written As (Wrong) | Actual Company | Price Sanity Check That Would Have Caught It |
|--------|---------------------|---------------|-----------------------------------------------|
| RUS | Royal Bank of Canada | Russel Metals (metals distribution) | RUS = $76 vs RY = $205 — price alone flags it |
| MX | Maxar Technologies (delisted 2023) | Methanex (methanol, reverse-split Jul 2026) | MX = $87 post-split, pre-split $3-4. Maxar delisted — no price |
| SRV.UN | Northland Power (offshore wind) | SIR Royalty Income Fund (restaurant royalty trust) | SRV.UN = $14.52 — Northland traded higher; SIR is smaller |
| PZA | Canadian Properties REIT | Pizza Pizza Royalty Corp. (Pizza Pizza + Pizza 73 brands) | PZA = $11.23 with high volume, dividend cut — REIT vs royalty check |
| MTY | Magna International (auto supplier) | MTY Food Group (multi-brand QSR franchisor) | MTY = $32 vs Magna/MGA = different price range |
| WJX | Waste Connections (waste mgmt) | Wajax Corp (industrial equipment, est. 1858) | WJX = $30-35 range, Waste Connections/WCN = different price |

## Correct workflow (the fix)

**Step 1 — Pull DB price data first.** Before writing anything about a stock, pull its last several price rows from the DB. This gives you a price level, volume, and recent trend to sanity-check against whatever identity you assume.

```
# Example: pull last 15 price rows for a symbol
DB_PASS="..." python3 -c "
import pymysql
conn = pymysql.connect(host='ksfraser.ca', port=3306,
    user='ksfraser_stockmarket', password='...',
    database='ksfraser_stock_market',
    cursorclass=pymysql.cursors.DictCursor, connect_timeout=10)
cur = conn.cursor(dictionary=True)
cur.execute('SELECT symbol, price_date, close, volume FROM stockprices WHERE symbol = %s ORDER BY price_date DESC LIMIT 15', (symbol,))
for r in cur.fetchall():
    print(f\"{r['price_date']} | close={r['close']} | vol={r['volume']}\")
conn.close()
"
```

**Step 2 — Verify identity from authoritative source.** Before writing any company analysis, confirm the identity from the company's own investor relations page, TMX Money (money.tmx.com/en/quote/<symbol>), or stockanalysis.com (stockanalysis.com/quote/tsx/<symbol>). These are the most reliable sources for what the company actually does.

**Step 3 — Check the price against your assumption.** If you assumed "RUS = Royal Bank" and the DB shows $76 while Royal Bank (RY) is $205, something is wrong. Stop and re-verify. The price discrepancy alone is enough to flag most identity errors.

**Step 4 — Search correctly.** When searching the web:
- Search for just the ticker + "TSX" or "stock" — not "TICKER CompanyName" (if your guessed company name is wrong, you get articles about the wrong company)
- Look at the official company description on the result (TMX Money, stockanalysis.com, company IR page)
- Cross-check the business description against what the DB price/volume suggests

**Rule: never search for "TICKER WrongCompanyName" and trust the results.** This is the direct cause of all six errors. If your company guess is wrong, you get articles about the wrong company, and you write the analysis for the wrong company.

## Price sanity checks by ticker (retrospective)

These are the specific checks that would have caught each error before any analysis was written:

| Ticker | DB Price | Assumed Company's Typical Price | Discrepancy |
|--------|----------|-------------------------------|-------------|
| RUS | C$76.21 | Royal Bank (RY) = C$205 | 2.7× off — immediate flag |
| MX | C$87.21 (post-split) / C$3-4 (pre-split) | Maxar delisted — no price data | No price = delisted; C$87 ≠ Maxar price range |
| SRV.UN | C$14.52, vol 800-6,000/day | Northland Power (SRP.UN or similar) = different price/volume | Volume 10-100× lower than typical mid-cap energy stock |
| PZA | C$11.23, vol 80-230K/day | Canadian Properties REIT = different price, no dividend cut | PZA price + dividend-cut news = royalty company, not generic REIT |
| MTY | C$32.45, vol 40-140K/day | Magna (MGA) = different ticker, different price | MTY ≠ MGA — different ticker entirely |
| WJX | C$30-35, vol 70-350K/day | Waste Connections (WCN) = different ticker, different business | WJX ≠ WCN — different ticker, different sector |

## The "price sanity check" heuristic

For any Canadian/TSX stock, a quick price-level check against what you assumed catches most identity errors:

- **Banks (RY, TD, BMO, CIBC, BNS, NA):** typically C$50-250 range, high volume (100K-1M+)
- **Mid-cap industrials/distributors (WJX, RUS, FTT, TIH):** typically C$20-100, moderate volume (50K-300K)
- **Royalty income funds (PZA, BPF.UN, SRV.UN):** typically C$10-30, moderate-to-low volume
- **ETFs (IEV, FEZ, GLD, PMDIY):** price varies by underlying, but volume is typically high
- **Energy producers (VET.TO, SU):** typically C$10-40

If the DB price is wildly outside the expected range for the company type you assumed, stop and re-verify.

## Why this matters for the ksf_stockmarket project

The ATR sweep and other stock analyses write conclusions about specific companies. A wrong identity means:
- The competitor/sector analysis is for the wrong industry
- The fundamental outlook is for the wrong business
- The sell/hold verdict is applied to the wrong company
- The user loses trust in the analysis

Six wrong identities in one session is severe enough that any stock analysis workflow should have identity verification as a mandatory checkpoint, not an afterthought.

## Checklist (copy into any stock analysis workflow)

- [ ] Pulled DB price data (last 10-15 rows) for the symbol
- [ ] Confirmed identity from company IR page or TMX/stockanalysis.com
- [ ] Checked price level against expected range for assumed company type
- [ ] Searched for ticker + "TSX" (not "TICKER WrongCompanyName")
- [ ] Cross-checked business description matches what price/volume suggests
- [ ] Verified volume level is consistent with company type (micro-cap vs large-cap)
