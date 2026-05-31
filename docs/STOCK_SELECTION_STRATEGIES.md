# Stock Selection Strategies Reference

> **Version:** 1.0 | **Date:** 2026-05-31
> **Purpose:** Document every known stock selection strategy with screening criteria, expected performance, and known weaknesses.
> **Sources:** Motley Fool newsletters, academic research, CANSLIM, value investing, momentum literature.

---

## Table of Contents

1. [Strategy Categories](#strategy-categories)
2. [Long-Term Buy & Hold Strategies](#long-term-buy--hold-strategies)
3. [Momentum & Growth Strategies](#momentum--growth-strategies)
4. [Value & Contrarian Strategies](#value--contrarian-strategies)
5. [Dividend & Income Strategies](#dividend--income-strategies)
6. [Short-Term / Swing Strategies](#short-term--swing-strategies)
7. [Options-Based Strategies](#options-based-strategies)
8. [Quantitative / Statistical Strategies](#quantitative--statistical-strategies)
9. [Motley Fool Specific Strategies](#motley-fool-specific-strategies)
10. [Implementation: Stage Pipeline](#implementation-stage-pipeline)

---

## Strategy Categories

| Category | Time Horizon | Typical Hold | Risk Level | Expected Alpha |
|----------|-------------|-------------|------------|----------------|
| Buy & Hold (Quality) | 5+ years | 5-20 years | Low | Market + 2-4% |
| Growth/Momentum | 3-12 months | 6-18 months | Medium-High | Market + 3-8% |
| Value/Contrarian | 1-5 years | 2-5 years | Medium | Market + 2-5% |
| Dividend/Income | 3+ years | 3-10 years | Low-Market | Market + 1-3% |
| Swing/Short-term | 1-4 weeks | 1-30 days | High | +5-15% (if skilled) |
| Options-based | 1-3 months | 2-8 weeks | Very High | +10-30% or -100% |
| Quant/Stat Arb | 1-6 months | 1-6 months | Medium | +3-7% |

---

## Long-Term Buy & Hold Strategies

### 1. Warren Buffett "Wonderful Company at Fair Price"

**Philosophy:** Buy wonderful companies at fair prices and hold forever.

**Screening Criteria:**
```
ROE > 15% (5-year average)
Debt/Equity < 0.5
Gross Margin > 40%
Operating Margin > 15%
Free Cash Flow positive 5+ years
Revenue growth > 10% (5-year CAGR)
PEG Ratio < 1.5 (P/E ÷ earnings growth rate)
Management ownership > 1%
No earnings decline in last 5 years
```

**Motley Fool Equivalent:** Stock Advisor "Wide Moat" picks
**Documented Performance:** Stock Advisor returned +978% vs S&P +212% (2002-2026)
**Strengths:** Works across market cycles, low turnover, tax efficient
**Weaknesses:** Underperforms in momentum-driven bull markets, requires patience
**Best For:** Core sleeve (40% of portfolio)

### 2. Philip Fisher "Scuttlebutt" Quality Growth

**Philosophy:** Invest in companies with superior business models, honest management, and long-term growth runways. Talk to customers, suppliers, competitors.

**Screening Criteria:**
```
R&D spending > 5% of revenue (innovation commitment)
Revenue growth > 15% for 5+ years
Market leader in growing industry
Management communicates honestly (read annual reports)
Product/service has pricing power
Low customer concentration (< 20% from any single customer)
Employee satisfaction high (Glassdoor > 3.5)
```

**Strengths:** Identifies compounders before they're obvious
**Weaknesses:** Qualitative, hard to screen programmatically, survivorship bias in backtests
**Best For:** Satellite sleeve candidates

### 3. Peter Lynch "Growth at Reasonable Price" (GARP)

**Philosophy:** Buy companies growing earnings at 15-25% whose P/E is below their growth rate.

**Screening Criteria:**
```
PEG Ratio < 1.0 (ideal), < 1.5 (acceptable)
EPS growth 15-25% (too fast is unsustainable)
Institutional ownership < 50% (not yet discovered)
Insider buying in last 6 months
Debt/Equity < industry average
Cash from operations > net income (quality of earnings)
```

**Motley Fool Equivalent:** "Rule Breakers" newsletter strategy
**Documented Performance:** Lynch's Magellan Fund returned 29.2% annually (1977-1990)
**Strengths:** Simple, intuitive, works well in growth markets
**Weaknesses:** Misses deep value, struggles when growth is scarce

---

## Momentum & Growth Strategies

### 4. William O'Neil CANSLIM

**Philosophy:** Buy leading stocks in strong sectors just before breakouts from sound bases.

**Screening Criteria (each letter):**
```
C = Current quarterly EPS up ≥ 25% vs same quarter last year
A = Annual EPS growth ≥ 20% for 5 years (or 3 years for newer companies)
N = New products/services, new highs, new management (catalyst)
S = Supply/demand — small float, high relative strength
L = Leader vs laggard — #1 in sector by RS Rating ≥ 80
I = Institutional sponsorship — 3-10 mutual funds own it (not too crowded)
M = Market direction — only buy in confirmed uptrend (S&P > 200d MA)
```

**Documented Performance:** CANSLIM investors report 18-25% annual returns vs 10% market
**Motley Fool Equivalent:** "Stock Advisor" momentum component
**Strengths:** Systematic, clear entry/exit rules, works in bull markets
**Weaknesses:** Whipsaws in choppy markets, stop losses essential (-7% rule), underperforms in bear markets
**Best For:** Tactical sleeve (30%)

### 5. Momentum + Relative Strength

**Philosophy:** Stocks that outperformed over the past 6-12 months tend to continue outperforming for 3-6 more months (momentum anomaly).

**Screening Criteria:**
```
6-month price return > 80th percentile (relative to universe)
12-month price return > 70th percentile
Relative Strength (RS) rating ≥ 80
Price > 200-day MA
Volume increasing on up days
Sector RS > 60 (sector also outperforming)
```

**Academic Backing:** Jegadeesh & Titman (1993): momentum generates 1% monthly alpha
**Documentary:** AQR Momentum index has outperformed S&P by 3-5% annually since 1980
**Strengths:** Strong academic backing, works across markets and decades
**Weaknesses:** Momentum crashes (2009, 2020), concentration risk, tax inefficient
**Best For:** Tactical sleeve overlay

### 6. Earnings Momentum (Post-Earnings Announcement Drift)

**Philosophy:** Stocks that beat earnings expectations continue to drift upward for 60-90 days after the announcement.

**Screening Criteria:**
```
Earnings surprise > 5% (actual vs consensus)
Revenue surprise > 3%
Forward guidance raised
Institutional buying after announcement
Stock gap up on earnings > 3%
Short interest < 10% (not crowded short)
Estimate revisions: ↑ for next quarter
```

**Academic Backing:** Bernard & Thomas (1989): PEAD generates 6-9% annualized excess return
**Strengths:** Well-documented anomaly, relatively low risk
**Requires:** Real-time earnings data, consensus estimate feeds
**Best For:** Tactical sleeve — quarterly rebalance around earnings

### 7. Analyst Revision Momentum

**Philosophy:** When analysts raise estimates for a stock, it tends to outperform as other analysts follow.

**Screening Criteria:**
```
3+ analysts raised estimates in last 30 days
Consensus estimate for current quarter raised > 5%
Price target raised by Median analyst
Buy rating increasing (% Buy > 70%)
Estimate dispersion declining (analysts converging)
```

**Best For:** Tactical / swing sleeve

---

## Value & Contrarian Strategies

### 8. Benjamin Graham Net-Net (Deep Value)

**Philosophy:** Buy stocks trading below their net current assets (current assets - total liabilities).

**Screening Criteria:**
```
Market Cap < (Current Assets - Total Liabilities) × 0.67
Positive earnings in most recent year
Debt/Equity < 1.0
Current ratio > 1.5
No losses in 3 of last 5 years
```

**Documented Performance:** Graham's strategies returned 15-20% annually (1930s-1970s)
**Strengths:** Extremely conservative, margin of safety
**Weaknesses:** Few candidates exist in bull markets, many are value traps
**Best For:** Satellite sleeve — small positions

### 9. "Fallen Angels" (Quality Companies on Sale)

**Philosophy:** High-quality companies that are temporarily out of favor due to a single negative event, not a broken business.

**Screening Criteria:**
```
Former 5-star Morningstar rating, now 2-3 stars
ROE historically > 15%, recent quarter dipped
Stock down > 30% from 52-week high
Insider buying after decline
Sector is temporarily out of favor
Balance sheet still strong (Debt/Equity < 1.0)
Management remains intact (not a shakeup)
```

**Examples:** Amazon 2001, Apple 1997, Microsoft 2014, Meta 2022
**Best For:** Tactical sleeve entries during bear markets

### 10. Piotroski F-Score (Value + Quality)

**Philosophy:** Among cheap stocks (low P/B), pick the financially healthy ones using 9 binary criteria. Score 8-9 = strong, 0-2 = weak.

**Screening Criteria:**
```
P/B < 1.5 (value universe)
F-Score 8 or 9:
  +1 ROA > 0
  +1 CFO > 0
  +1 ΔROA increasing
  +1 CFO > ROA (accruals)
  +1 ΔLeverage decreasing
  +1 ΔCurrent Ratio increasing
  +1 No new shares issued
  +1 ΔGross Margin increasing
  +1 ΔAsset Turnover increasing
```

**Academic Backing:** Piotroski (2000): F-Score 8-9 stocks outperformed by 7.5% annually
**Strengths:** Systematic, removes value trap risk
**Best For:** Income sleeve screening

---

## Dividend & Income Strategies

### 11. Dogs of the Dow

**Philosophy:** Each January, buy the 10 highest-yielding Dow 30 stocks. Hold one year. Rebalance.

**Screening Criteria:**
```
Select from Dow 30 universe
Rank by dividend yield (highest to lowest)
Buy equal weight of top 10
Hold 1 year, rebalance in January
```

**Documented Performance:** Outperformed Dow by 2-3% annually (1957-2003), but underperformed in recent decades
**Strengths:** Simple, low turnover, contrarian
**Weaknesses:** Yield traps (high yield = market expects cut), concentrated in aging companies
**Best For:** Income sleeve — but with dividend safety filter applied

### 12. Dividend Aristocrats & Kings

**Philosophy:** Buy companies with 25+ years (Aristocrats) or 50+ years (Kings) of consecutive dividend increases.

**Screening Criteria:**
```
25+ consecutive years of dividend increases (Aristocrats)
OR 50+ consecutive years (Kings)
Payout ratio < 60% (sustainable)
Revenue growth > 0 (not shrinking)
Credit rating BBB+ or higher
```

**Documented Performance:** S&P Dividend Aristocrats index returned 10.5% annually (2008-2023) with lower volatility
**Strengths:** Quality filter, dividend growth compounds, defensive
**Weaknesses:** Low growth in some names, yield compression in low-rate environments
**Best For:** Income sleeve (20%)

### 13. The Brick Avoidance: Dividend Safety Screen

**Philosophy:** Detect and avoid companies heading for a dividend cut before it happens. (Based on The Brick/TBI.TO case study.)

**Screening Criteria — AVOID if:**
```
Payout ratio > 100% (dividends exceed earnings) for 2+ quarters
Free cash flow coverage < 0.8× (FCF < 80% of dividends paid)
Debt-to-equity rising for 2+ consecutive quarters
Dividend yield > 2× sector median (yield trap signal)
Borrowing to pay dividends (dividend paid from debt proceeds)
Same-store sales declining (retail REITs)
Occupancy rates declining (REITs)
```

**Best For:** ALL dividend-paying holdings — run this screen weekly

### 14. Monthly Dividend Capture Calendar

**Philosophy:** Build a calendar of when each holding pays dividends and reinvest strategically.

**Implementation:**
```
Track ex-dividend date for all dividend payers
Reinvest dividends on ex-date (not payment date)
Target companies paying monthly (REITs, BDCs, SPLFs)
Build ladder: 10+ positions paying in different months for cash flow
Screen for special dividends (one-time windfalls)
```

**Best For:** Income sleeve cash flow management

---

## Short-Term / Swing Strategies

### 15. Bollinger Band Mean Reversion

**Philosophy:** When a stock drops below its lower Bollinger Band in an uptrend, it tends to snap back up.

**Screening Criteria:**
```
Price touches or crosses below BB lower band (20d, 2σ)
RSI(14) < 30 (oversold confirmation)
Overall trend is up (price > 200d MA)
Volume spike on the sell-off (capitulation)
Sector is NOT in downtrend
Entry: When price crosses back above lower band
Exit: Middle band (20d MA) or upper band
```

**Best For:** Swing sleeve entries (1-4 week holds)
**Risk:** -3% hard stop from entry

### 16. VWAP Reversion

**Philosophy:** Institutional algorithms mean-revert to VWAP. When price deviates significantly from VWAP, it tends to return.

**Screening Criteria:**
```
Price < VWAP by > 2% (intraday)
High relative volume (> 1.5× average)
No major news/catalyst driving the move
Bid/ask spread tight (liquid)
Short-term mean reversion signal
```

**Best For:** Day trading / 1-3 day holds
**Requires:** Intraday data

### 17. Gap and Go / Gap Fill

**Philosophy:** Stocks that gap up on high volume tend to continue 60% of the time. Stocks that gap down tend to fill the gap 70% of the time.

**Screening Criteria:**
```
Gap up: Open > 2% above previous close on 2× average volume
Gap and Go: Buy at open if holds above VWAP in first 15 min
Gap Down: Wait for gap fill to previous close before buying
Short gap fills: Sell into gap fills on declining volume
```

**Best For:** Swing sleeve — daily scanning

### 18. Abnormal Volume Detection

**Philosophy:** Unusual volume (3× average or higher) often precedes significant price moves. Institutions are accumulating or distributing.

**Screening Criteria:**
```
Volume > 3× 20-day average volume
Price change > ±2% on the high-volume day
Not an earnings day (earnings volume is noise)
Insider filing in last 30 days (Form 4)
Sector also showing abnormal volume
Options volume also elevated (if applicable)
```

**Best For:** All sleeves — leading indicator for position entry/exit

### 19. Options Flow / Unusual Options Activity

**Philosophy:** Smart money trades options to express leveraged positions. Unusual call volume often precedes price increases.

**Screening Criteria:**
```
Call/Put volume ratio > 3:1 (bullish) or < 1:3 (bearish)
Options volume > 200% of average
Sweep orders detected (institutional-sized trades)
Implied volatility rank < 50 (not expensive)
Near-term expiry (0-30 DTE) — conviction signal
Open interest increasing (new positions, not closing)
```

**Best For:** Satellite sleeve — low capital, high conviction
**Requires:** Options data feed (paid, not free)

### 20. VIX Fear Gauge (Contrarian)

**Philosophy:** When VIX spikes above 30, the market is oversold. When VIX drops below 15, complacency is high.

**Screening Criteria:**
```
BUY signal: VIX > 30 AND VIX curve in backwardation (front month > back month)
REDUCE signal: VIX < 15 AND put/call ratio < 0.7
HEDGE signal: VIX term structure flips to extreme backwardation
SELL signal: VIX spikes > 40 (buy SPY calls as hedge)
```

**Best For:** Portfolio-level risk management, not stock selection

---

## Options-Based Strategies

### 21. Covered Call Writing (Income)

**Philosophy:** Own the stock, sell covered calls for income. Sacrifice upside for premium.

**Screening Criteria:**
```
Own 100+ shares of underlying
Implied Volatility Rank > 50 (expensive options)
Sell 30-45 DTE, 15-20% OTM calls
Target 1-2% monthly premium
Avoid earnings period (IV crush risk)
Roll early if ITM before expiry
```

**Expected Return:** 1-4% per month in premium + dividends - opportunity cost
**Best For:** Income sleeve on TFSA-eligible positions
**Max Portfolio Allocation:** 2% (as you specified)

### 22. Cash-Secured Puts (Entry Strategy)

**Philosophy:** Sell puts on stocks you want to own at a lower price. Get paid to wait.

**Screening Criteria:**
```
Stock you'd buy at current price if it dropped 10-15%
Sell 30 DTE puts at 70-75 delta
Target 1-2% premium on cash secured
Only sell if you have cash to cover assignment
Dividend date NOT before expiry (assignment risk)
```

**Best For:** Tactical sleeve entries at better prices

### 23. Put Spreads (Bearish Hedge)

**Philosophy:** Buy protection on positions you own through put spreads.

**Screening Criteria:**
```
Own the underlying stock
Buy ATM or 5% OTM put
Sell 15-20% OTM put to finance
30-45 DTE
Max loss = width of spread × 100
```

**Best For:** Hedging Core sleeve positions in bear market regimes

---

## Quantitative / Statistical Strategies

### 24. Statistical Volatility Arbitrage

**Philosophy:** When implied volatility exceeds realized volatility by a wide margin, options are overpriced.

**Screening Criteria:**
```
IV Rank > 70 (IV expensive)
IV > 1.5× HV(20) (implied overpricing historical)
Sell strangles/straddles
Delta-neutral entry
Manage at 25% of max profit or 50% width
```

**Requires:** Options data, Greeks calculation
**Best For:** Satellite sleeve (2% allocation)

### 25. Pairs Trading (Market Neutral)

**Philosophy:** Find two highly correlated stocks. When correlation diverges, buy the laggard, short the leader.

**Screening Criteria:**
```
Correlation > 0.85 over 60 days
Z-score of price ratio > 2 (divergence)
Both stocks liquid (avg volume > 1M/day)
Same sector
Cointegration test passed (Engle-Granger)
```

**Academic Backing:** Gatev, Goetzmann & Rouwenhorst (2006): 11% annualized excess return
**Strengths:** Market neutral, works in bear markets
**Weaknesses:** Correlation breakdown risk, requires shorting, margin intensive
**Best For:** Satellite sleeve — if shorting available

### 26. Mean Reversion Pairs (Sector)

**Philosophy:** Within a sector, rotate from outperformer to underperformer when spread is wide.

**Screening Criteria:**
```
Sector benchmark ETF (XEG, XFN, XIT, etc.)
Identify top 5 and bottom 5 in sector by 60-day return
Long bottom 3, short top 3 (or just rotate capital)
Rebalance monthly
Z-score trigger: rotate when spread > 1.5σ
```

**Best For:** Tactical sleeve — sector rotation

---

## Motley Fool Specific Strategies

### 27. Stock Advisor "Rule Breakers"

**Philosophy:** Find companies with massive total addressable market, superior technology, aggressive management, and network effects — BEFORE they're obvious.

**Screening Criteria:**
```
Market opportunity > $100B TAM
Platform/network effect business model
Insider ownership (> 5% by founder/CEO)
Revenue growth > 30% annually
Path to profitability visible (even if not yet profitable)
Wide economic moat forming
Valuation: Price/Sales < 20 for hypergrowth, < 10 for established
```

**Documented Performance:** Stock Advisor: +978% vs S&P +212% (inception 2002-2026)
**Best For:** Satellite sleeve — high conviction growth

### 28. Stock Advisor "Everlasting Stocks"

**Philosophy:** High-quality compounders you can own for 5-10+ years. Lower volatility than Rule Breakers.

**Screening Criteria:**
```
Dividend yield > 1.5% AND dividend growth > 10% for 5+ years
ROIC > 15%
Revenue growth > 10% (consistent, not lumpy)
Gross margin expanding
Insider buying
Institutional ownership stable (not increasing too fast)
Current pullback > 15% from highs (entry timing)
```

**Best For:** Core sleeve quality filter

### 29. Motley Fool "Millionacres" (Real Estate)

**Philosophy:** Invest in high-quality REITs and real estate platforms during periods of mispricing.

**Screening Criteria:**
```
FFO payout ratio < 70%
Debt/EBITDA < 5.0
Occupancy rate > 90%
Same-store NOI growth > 2%
Management track record
Sector tailwind (data centers, logistics, healthcare)
```

**Best For:** Income sleeve — REIT allocation

### 30. Motley Fool "The Ascent" Small-Cap Screen

**Philosophy:** Find small, overlooked gems before institutional investors discover them.

**Screening Criteria:**
```
Market cap $300M - $5B
Revenue growth > 20%
Gross margin > 50%
Debt/Equity < 1.0
Institutional ownership < 30%
Insider ownership > 5%
Positive earnings or clear path to profitability in 12 months
```

**Best For:** Satellite sleeve — small-cap moonshots

---

## Implementation: Stage Pipeline

### The screening pipeline flows through configurable stages:

```
STAGE 1: Universe Filter (Hard Rules)
├── Min market cap ($500M default)
├── Min daily volume (100K shares default)
├── Min price ($5 default — avoid penny stocks)
├── Exchange: TSX, NYSE, NASDAQ only
└── Max spread: 0.5% bid-ask
     ↓
STAGE 2: Quality Filter (Configurable Cutoffs)
├── Payout ratio < [config: max_payout_ratio] (default 80%)
├── Debt/Equity < [config: max_debt_equity] (default 1.5)
├── ROE > [config: min_roe] (default 10%)
├── Earnings positive last 4 quarters
├── Institutional ownership [config: min/max range]
└── Pass Piotroski F-Score ≥ [config: min_fscore] (default 5)
     ↓
STAGE 3: Strategy-Specific Scoring
├── Each strategy scores all passed candidates
├── Score = weighted sum of normalized factors
├── Top [config: top_n_per_strategy] advance
└── Track which strategy generated each pick
     ↓
STAGE 4: Risk Management & Allocation
├── Position sizing: Kelly % or fixed fraction
├── Max position size: [config: max_position_pct] (default 10%)
├── Max sector exposure: [config: max_sector_pct] (default 25%)
├── Correlation filter: no two positions with corr > 0.80
├── ATR stop set at [config: atr_stop_mult] × ATR(14)
└── Final allocation per sleeve
```

### Configurable Parameters (from config.yaml):
```yaml
screening:
  stages:
    stage1_universe:
      min_market_cap: 500_000_000
      min_daily_volume: 100_000
      min_price: 5.00
      allowed_exchanges: ['TSX', 'NYSE', 'NASDAQ']
      max_bid_ask_spread_pct: 0.005

    stage2_quality:
      max_payout_ratio: 0.80
      max_debt_equity: 1.5
      min_roe: 0.10
      min_quarters_profitable: 4
      min_institutional_pct: 0.10
      max_institutional_pct: 0.80
      min_fscore: 5

    stage3_strategies:
      strategies:
        - name: buffett_quality
          weight: 0.25
          top_n: 10
        - name: canslim_momentum
          weight: 0.20
          top_n: 8
        - name: dividend_safety
          weight: 0.20
          top_n: 8
        - name: earnings_momentum
          weight: 0.15
          top_n: 6
        - name: abnormal_volume
          weight: 0.10
          top_n: 5
        - name: options_flow
          weight: 0.10
          top_n: 3
      min_score_to_advance: 0.60

    stage4_allocation:
      max_position_pct: 0.10
      max_sector_pct: 0.25
      max_correlation: 0.80
      kelly_fraction: 0.25  # Quarter-Kelly for safety
      atr_stop_mult: 2.0
```

---

## Summary: Which Strategies for Which Sleeve

| Sleeve | Primary Strategies | Secondary | Allocation |
|--------|-------------------|-----------|------------|
| Core (40%) | #1 Buffett Quality, #28 Everlasting, #12 Aristocrats | #9 Fallen Angels | Buy & hold 5+ years |
| Tactical (30%) | #4 CANSLIM, #5 Momentum, #6 Earnings Momentum | #15 BB Mean Rev, #17 Gap & Go | Hold 1-6 months |
| Income (20%) | #12 Aristocrats, #13 Div Safety, #14 Monthly Calendar | #21 Covered Calls | Hold 1-3 years |
| Satellite (10%) | #7 Graham Deep, #19 Options Flow, #27 Rule Breakers | #25 Pairs, #24 Vol Arb | Hold 3-12 months |

---

## Key Warnings (From Motley Fool's Own Analysis)

1. **Stock Advisor works because of concentration**: Their 20-25 stock portfolio concentration means a few big winners (NVDA, TSLA) drive returns. A diversified 200-stock portfolio would not show the same results.

2. **Momentum strategies crash**: CANSLIM underperforms in bear markets. You NEED a market direction filter (S&P > 200d MA).

3. **Dividend-focused strategies underperform in tech bull markets**: High-yield stocks are often value traps or low-growth. Dividend growth (not high yield) is the key.

4. **Options strategies have asymmetric risk**: Covered calls cap your upside. Put spreads decay in flat markets. These are supplements, not core strategies.

5. **The "best" strategy changes with market conditions**: No single strategy wins forever. The ensemble approach (multiple competing strategies) is more robust than any single screen.

6. **Backtest overfitting is real**: A strategy that perfectly fits 2010-2020 data may fail miserably in 2021-2030. Walk-forward testing is essential.
