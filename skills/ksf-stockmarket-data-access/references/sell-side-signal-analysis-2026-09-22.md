# Sell-Side Signal Analysis — Worked Example (2026-09-22)

## What was analyzed

All `analyst_targets` rows with `recommendation IN ('strong_sell','sell')` (only `underperform` exists — 10 rows for phantom `BLX.TO`) PLUS `strong_buy` tickers whose numbers contradict their labels (29 tickers, 257 rows).

## Bugs found by comparing signal to reality

The analysis methodology: **compare the recommendation label against target price, latest close, price trend, sector context, and news.** When numbers disagree with labels, that's a bug — not a signal.

### Bug 1: `target_price == current_price` in 2,289/2,290 rows

**How found**: Compare the two columns against each other. If they're always equal, one is a duplicate.

**Impact**: Every row has 0.0% computed upside. The `recommendation` label is the only effective signal. When target = current, you can't compute real upside without comparing to an independent price source (`stockprices.close`).

### Bug 2: CNR currency confusion

**How found**: Compare target values against real close and across time.

| Period | Targets | Range | Likely Currency | vs Close $96.30 CAD |
|--------|---------|-------|----------------|---------------------|
| Jul 19 | $83.02 (×2) | $83 | CAD (CNR.TO) | −14% |
| Jul 20-22 | $178-$181 | $178-$181 | **USD (CNI on NYSE)** | +85% to +91% in CAD |
| Jul 23-Aug 4 | $78-$87 | $78-$87 | CAD | −20% to −9% |
| Aug 20-Sep 2 | $94-$102 | $94-$102 | CAD | −2% to +6% |
| Sep 3-22 | $165-$170 | $165-$170 | **USD** | +71% to +77% in CAD |

The scraper alternates between CNR.TO (TSX, CAD) and CNI (NYSE, USD) without distinguishing. Same company, different currency. The Sep 1→Sep 3 jump from $101.93 to $168.21 is a 65% one-day move — impossible unless the currency source switched.

**The label contradicted the numbers**: `strong_buy` (Jul-Aug, CAD targets ~$80-102) → `buy` (Sep, USD targets ~$165-170). A $165 target on $96 stock should be `strong_buy` if it's CAD. The label logic doesn't account for currency.

**Caught by**: Comparing the target against the real close, and noticing the one-day jump from $102 to $168 is absurd for a railway.

### Bug 3: TFII hidden sell signal

**How found**: Compare target trend over time against price.

6-week trend: $155.83 → $127.02 = **−18.5% decline**.

Latest close: **$131.78 CAD**. Latest target: **$127.02** (below price by 3.6%).

A target below the current price with a declining trend should be labeled `underperform` or `sell` — not `none`.

**Caught by**: Comparing the target trend (declining 18.5%) and the latest target vs the latest close (target below price).

### Bug 4: Phantom `BLX.TO` underperform

**How found**: Existence check — does the ticker exist in `symbol_master` and `stockprices`?

`BLX.TO`: 10 `underperform` rows, targets $37.00-$37.13, but:
- `symbol_master`: NOT FOUND — no company name, sector, or portfolio status
- `stockprices`: 0 rows — no price history
- `symbol_news`: 0 articles — no news

A sell signal on a ticker we don't track is meaningless.

**Caught by**: Checking whether the ticker exists in `symbol_master` and `stockprices`.

### Bug 5: Strong buy labels with negative real upside

**How found**: Compare each target against the actual close in `stockprices`.

12 of 29 `strong_buy` tickers have target below actual close:

| Ticker | Target | Close | Real Upside |
|--------|--------|-------|-------------|
| ALIZY | $49.99 | $51.36 | −2.7% |
| ATCH | $0.17 | $0.18 | −3.6% |
| BPF.UN | $19.94 | $20.71 | −3.7% |
| CAH | $230.03 | $234.89 | −2.1% |
| CLILF | $2.00 | $2.05 | −2.4% |
| **DIS** | $96.19 | $108.59 | **−11.4%** |
| **DVN** | $45.13 | $49.73 | **−9.2%** |
| **EDV.TO** | $66.34 | $83.92 | **−20.9%** |
| **EXK** | $7.52 | $9.72 | **−22.6%** |
| FURY | $0.54 | $0.56 | −5.2% |
| MA | $567.65 | $574.42 | −1.2% |
| NWC.TO | $51.09 | $52.22 | −2.2% |

These are labeled `strong_buy` with negative real upside — clearly broken labels.

**Caught by**: Comparing target vs actual close per ticker.

## No news for any signal

`symbol_news`: articles only for MX.TO, MEOH, MTY.TO, WJX.TO, RUS.TO. **Zero articles for any of the 29 strong_buy tickers, CNR, TFII, or BLX.TO.**

Without news, the "why" question is unanswerable from the database alone.

## Deliverable

- `/tmp/strong_buy_deep_analysis.md` — 202 lines, 29 tickers evaluated, bugs caught
- `/tmp/sell_side_analysis.md` — 174 lines, sell-side signals + hidden sells, bugs caught

## Lessons for signal analysis

1. **Always treat `analyst_targets` as suspect until verified** — the yfinance scraper has a documented bug (`target_price == current_price` in 99.96% of rows). It's not ground truth.
2. **Currency confusion is invisible unless you compare targets to real closes over time** — a one-day 65% jump is the tell.
3. **A declining target below current price = hidden sell** — the recommendation engine must flag this, not label it `none`.
4. **Phantom signals exist** — a ticker with ratings but no master record, price, or news is ghost data.
5. **Labels contradicting numbers = broken logic, not a signal** — when target < close and label is "strong_buy", the label is wrong.

## DB query patterns used

```sql
-- Count by recommendation, find duplicates
SELECT recommendation, COUNT(*) FROM analyst_targets GROUP BY recommendation;

-- Check target == current
SELECT COUNT(*) FROM analyst_targets WHERE target_price = current_price;

-- Latest close per symbol
SELECT symbol, MAX(price_date), close FROM stockprices GROUP BY symbol;

-- Ticker existence check
SELECT symbol, name, sector FROM symbol_master WHERE symbol = 'BLX.TO';
SELECT COUNT(*) FROM stockprices WHERE symbol = 'BLX.TO';
SELECT COUNT(*) FROM symbol_news WHERE symbol = 'BLX.TO';
```
