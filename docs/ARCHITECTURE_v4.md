# Investment Agent — Architecture v4.0 (ADAPTIVE)

> **Version:** 4.0 | **Date:** 2026-05-31 | **Repo:** `ksfraser/ksf_stockmarket`
> **Status:** Complete redesign after v3 autopsy revealed fundamental simulation flaws

---

## 1. Core Philosophy: Adaptive, Not Static

**v3 was broken.** It trained once on 2014-2018, tested once on 2019-2024, checked prices annually, and the stop-loss parameter was dead code. The GA learned to chase past winners (AMZN + AAPL = 42.5%) which happened to work only because 2019-2024 included their bull run. This is overfitting, not intelligence.

**v4 principle: The market regime changes. The AI must change with it.**

```
TODAY:   Download latest data → Retrain on rolling window → Generate today's signals
TOMORROW: Download latest data → Check if regime shifted → Retrain if needed → Rebalance
NEXT WEEK: Same cycle, different data, potentially different optimal strategy
```

The system doesn't find THE best strategy. It finds the best strategy **RIGHT NOW** and recognizes when that strategy is no longer working.

---

## 2. What Killed The Brick (And What We Must Learn)

The Brick (TBI.TO) case study:
- Income trust paying $0.10/month ($1.20/yr)
- Earnings dropped below dividend payout → 2 years of deterioration
- Dividend cut to $0.01/month → share price crashed to 8% of pre-cut value
- **Total loss >> all dividends ever collected**

**Pattern we must detect:**
1. Payout ratio > 100% (dividends > earnings) → WARNING
2. Payout ratio increasing for 2+ quarters → DANGER
3. Free cash flow negative while paying dividends → CRITICAL
4. Debt-to-equity rising + dividend maintained → BORROWING TO PAY DIVIDENDS

**This is why fundamentals matter.** Technical indicators alone cannot detect dividend sustainability. We need:
- Quarterly earnings vs dividend payout ratio
- Free cash flow coverage
- Debt-to-equity trajectory
- Same-store sales (retail) or occupancy rate (REITs)

---

## 3. Data Strategy: 30-Year Lookback on Blue Chips

### 3.1 Training Universe
Instead of 404 symbols with 5-10 years each, use **30-50 blue-chip symbols with 20-30 years of data**:

**US Blue Chips (20-30 years available):**
- MSFT, AAPL, AMZN, GOOGL, META, JNJ, PG, KO, PEP, WMT, HD, LOW, MCD, DIS, NFLX, V, MA, JPM, BAC, GS, XOM, CVX, PFE, MRK, ABT, DHR, CAT, BA, GE, MMM, INTC, AMD, NVDA, CRM, ORCL, CSCO, IBM, QCOM, TXN, UPS, FDX, LMT, RTX, GD, NOC, BMY, LLY, GILD, AMGN, BIIB, REGN, VRTX, ISRG, ZTS, ADBE, PYPL, SQ, SHOP, SNOW, PLTR, SQ, TWLO, DDOG, NET, CRWD, OKTA, CYBR, S, RPD, TENB, VRNS, QLYS, ALRM, BRZE, FRSH, BMBL, PINS, SNAP, RBLX, U, ROKU, TWTR, PTC, ANSS, CDNS, SNPS, ARM, AVGO, MRVL, NXPI, SWKS, QRVO, MU, WDC, STX, NTAP, HPQ, DELL, HPE, CSCO, JNPR, CIEN, UI, ARST, FFIV, AKAM, EQIX, DLR, AMT, SBAC, CCI, EXPE, BKNG, TRIP, TSN, BG, ADM, CTVA, MOS, CF, FMC, DE, AGCO, CAT, PCAR, GWW, FAST, MSFT, ADBE, ORCL, CRM, NOW, VEEV, WDAY, ZS, CRWD, FTNT, PANW, CHKP, CYBR, S, RPD, TENB, VRNS, QLYS, ALRM, BRZE, FRSH, BMBL, PINS, SNAP, RBLX, U, ROKU, TWTR, PTC, ANSS, CDNS, SNPS

**CA Blue Chips (15-25 years):**
- RY, TD, BMO, CM, BNS, ENB, TRP, SU, CNQ, CVE, MEG, ARLN, SJR.B, BCE, T, QSR, MFC, SLF, POW, GWO, IAG, FTS, AQN, BLX, CU, EMP.A, DOL, ATD, L, MRU, WCN, GIB.A, CSU, KXS, DSG, OTEX, SHOP, LSPD, NVEI, TOI, CKK, REAL, GFL, BIPC, BIP.UN, BEPC, NPI, RNW, INE, ACO.X, CIGI, MFI, TCL.A, KEY, CIX, CWB, LB, EQN, HBM, K, LIF, CHP.UN, HR.UN, REI.UN, SRU.UN, CAR.UN, MEQ, PRMW, ACB, TLRY, CRON, HEXO, EDGE, NUMI, CURE, CL, VEXT, GATO, KRR, CEF.U, CEF.A, BAM, BAM.A, TRP, ENB, PPL, CVE, SU, CNQ, MEG, ARLN, ARX, TOU, CPG, PMT, VET, BTE, KEL, POU, CRL, OBE, GTE, PIPE, CEU, EFR, PNE, ALO, TWM, SCL, AGI, KNT, CG, CXB, OGC, RNG, TXG, WDO, ELD, IAG, SFC, CCO, SLF, MFC, GWO, IAG, POW, MIC, XTD, CHP.UN, HR.UN, REI.UN, SRU.UN, CAR.UN, MEQ, PRMW, NWH.UN, CRR.UN, MRC, CJT, CJT.A, CEF.U, CEF.A, BAM, BAM.A

**ETFs for Monthly Rebalance Front-Running:**
- XIC (iShares Core S&P/TSX Capped Composite) — rebalances quarterly
- XSP (iShares Core S&P 500 CAD Hedged) — rebalances quarterly
- XEF (iShares Core MSCI EAFE IMI) — rebalances quarterly
- XUU (iShares Core S&P U.S. Total Market) — rebalances quarterly
- XBB (iShares Core Canadian Universe Bond) — rebalances monthly
- XSB (iShares Core Canadian Short Term Bond) — rebalances monthly
- CPD (iShares S&P/TSX Canadian Preferred Share) — rebalances monthly
- XEG (iShares S&P/TSX Capped Energy) — rebalances quarterly
- XIT (iShares S&P/TSX Capped Info Tech) — rebalances quarterly
- XFN (iShares S&P/TSX Capped Financial) — rebalances quarterly
- XMA (iShares S&P/TSX Capped Materials) — rebalances quarterly
- XUT (iShares S&P/TSX Capped Utilities) — rebalances quarterly
- XRE (iShares S&P/TSX Capped REIT) — rebalances quarterly

### 3.2 Training/Test Split Strategy
```
TRAIN:  Rolling 5-year window (e.g., 2015-2019)
TEST:   Next 1 year (e.g., 2020)
STEP:   Roll forward 6 months, retrain, retest

This gives us 20+ walk-forward cycles over 10 years
instead of a single train/test split.
```

### 3.3 Regime Detection
Before each retraining cycle, detect the current market regime:
- **Bull**: SPX > 200d MA, VIX < 20, credit spreads tightening
- **Bear**: SPX < 200d MA, VIX > 30, credit spreads widening
- **Transition**: Mixed signals, high uncertainty
- **Crisis**: VIX > 40, credit freeze, correlation → 1

Different strategies work in different regimes. The GA should evolve **regime-conditional** allocations.

---

## 4. Daily Operations Cycle

### 4.1 Every Day (Market Close)
```
1. Fetch OHLCV for all positions + watchlist (yfinance)
2. Update indicators (RSI, MACD, ATR, NATR, Bollinger, etc.)
3. Check ATR trailing stops — EXIT if triggered
4. Check dividend payout ratio warnings (quarterly earnings)
5. Log portfolio state to MySQL
```

### 4.2 Every Week
```
1. Recompute 20-day and 60-day volatility regime
2. Update correlation matrix (are correlations rising = risk-off signal?)
3. Check earnings calendar for upcoming reports (next 14 days)
4. Scan for dividend safety warnings (payout ratio, FCF)
5. Update NN predictions (20-day forward return distribution)
```

### 4.3 Every Month (1st Trading Day)
```
1. ETF rebalance front-run: Check announced index changes
2. Execute monthly rebalance per Blender recommendation
3. Tax-loss harvest scan (realize losses before year-end)
4. Update RL agent with latest month's reward signal
5. Generate new buy/sell/hold recommendations
```

### 4.4 Every Quarter
```
1. Full GA retrain on rolling 5-year window
2. Full NN retrain on latest indicator data
3. Full RL retrain on latest trading episodes
4. Blender re-weights GA/NN/RL ensemble
5. Generate quarterly report + rebalance recommendation
6. Check if regime has shifted → trigger emergency retrain if yes
```

### 4.5 Regency Shift Detection (Continuous)
```
IF regime changes (Bull→Bear or Bear→Bull):
  → Emergency retrain of ALL agents
  → Reduce position sizes by 50% until new model converges
  → Switch to defensive allocation (bonds, gold, cash)
  → Alert user: "Regime shift detected — retraining"
```

---

## 5. Fundamental Screening Layer (NEW)

### 5.1 Dividend Safety Score (0-100)
```
payout_ratio = dividends_per_share / earnings_per_share
fcf_coverage = free_cash_flow / total_dividends_paid
debt_to_equity = total_debt / total_equity
revenue_growth = (revenue_t - revenue_t-4) / revenue_t-4  (YoY)

score = (
    30 * (1 - min(payout_ratio, 1.0)) +     # Lower payout = safer
    25 * min(fcf_coverage / 1.5, 1.0) +       # FCF > 1.5× dividends = safe
    20 * (1 - min(debt_to_equity / 2.0, 1.0)) + # D/E < 2 = safe
    25 * (1 if revenue_growth > 0 else 0)      # Growing revenue = safe
)

IF score < 40: CRITICAL — likely dividend cut coming
IF score < 60: WARNING — monitor closely
IF score >= 80: SAFE — sustainable dividend
```

### 5.2 Earnings Quality Score
```
accruals = net_income - operating_cash_flow
accrual_ratio = accruals / total_assets

IF accrual_ratio > 0.05:  # Earnings not backed by cash
    quality_penalty = -20
IF earnings_growth > 0 AND fcf_growth < 0:
    quality_penalty = -30  # Earnings growing but cash flow declining
```

### 5.3 The Brick Pattern Detector
```
FOR EACH dividend-paying holding:
    IF payout_ratio[t] > 1.0 AND payout_ratio[t-1] > 1.0:
        ALERT: "Dividends exceed earnings for 2+ quarters"
    IF fcf_coverage < 0.8 AND debt_to_equity rising for 2+ quarters:
        ALERT: "Borrowing to pay dividends — The Brick pattern"
    IF dividend_yield > 2× sector_median AND payout_ratio > 0.9:
        ALERT: "Yield trap — market pricing in dividend cut"
```

---

## 6. ETF Rebalance Front-Running Strategy (NEW)

### 6.1 How It Works
Index ETFs must rebalance on known dates. If you know what they'll buy, you buy first:
1. Index provider announces reconstitution (typically 5-10 days before effective date)
2. ETF must trade on effective date to match new index
3. Front-run: Buy announced additions 3-5 days before effective date
4. Sell into the ETF's buying pressure on effective date

### 6.2 Known Rebalance Calendar
```
S&P/TSX Composite:    March, June, September, December (3rd Friday)
S&P 500:              March, June, September, December (3rd Friday)
MSCI EAFE:            May, November
Russell 2000:         June (last Friday)
Various sector ETFs:  Quarterly, varies by provider
```

### 6.3 Implementation
```
1. Scrape index reconstitution announcements (S&P, MSCI, FTSE Russell)
2. Cross-reference with ETF holdings (XIC, XSP, XEF, etc.)
3. Identify forced buying: new additions to tracked index
4. Size positions: 0.5-1% of portfolio per front-run trade
5. Entry: 3-5 days before effective date
6. Exit: On effective date (sell into ETF buying) or +2 days max
7. Stop: -3% hard stop (front-running doesn't always work)
```

---

## 7. Revised Agent Architecture

### 7.1 GA Optimizer (Fixed)
```
GENES:
  - Per-symbol weights (sleeve-aware)
  - ATR stop multiplier (NOW ACTUALLY USED)
  - Rebalance frequency (weekly/monthly/quarterly)
  - Regime-conditional weights (bull vs bear vs transition)
  - Max position size
  - Min dividend safety score threshold

FITNESS:
  - Walk-forward over rolling windows (not single train/test)
  - After-tax terminal value
  - Minus λ × max_drawdown
  - Minus μ × number_of_trades (transaction costs)
  - Minus ν × dividend_cuts_suffered

KEY FIX: Simulator runs on DAILY data with REAL stop-loss checking
```

### 7.2 NN Predictor (Enhanced)
```
INPUT:
  - 120 technical indicators (60-day sequences)
  - Fundamental scores (dividend safety, earnings quality)
  - Regime features (VIX, credit spreads, yield curve)
  - Macro features (USD/CAD, oil price, BoC rate)

OUTPUT:
  - 20-day return distribution (mean + variance)
  - Directional probability (up/down)
  - Dividend cut probability

TRAINING:
  - Retrain quarterly on rolling 5-year window
  - Walk-forward validation (no future peeking)
  - Early stopping on validation loss
```

### 7.3 RL Agent (Enhanced)
```
STATE:
  - Current portfolio weights
  - Regime classification
  - Days since last rebalance
  - Unrealized P&L per position
  - Cash balance
  - VIX level

ACTIONS:
  - HOLD: Do nothing
  - ADD: Increase position by 5%
  - REDUCE: Decrease position by 5%
  - EXIT: Close position entirely
  - ROTATE: Sell position A, buy position B

REWARD:
  - After-tax return per step
  - Minus transaction costs
  - Minus drawdown penalty
  - Bonus for dividend safety maintenance

TRAINING:
  - Retrain quarterly on latest episodes
  - Experience buffer: last 2 years of daily episodes
```

### 7.4 Blender (NEW)
```
COMBINES:
  - GA: Strategic allocation weights (quarterly)
  - NN: Tactical timing signals (weekly)
  - RL: Dynamic position management (daily)
  - Fundamental: Dividend safety gate (continuous)
  - Regime: Strategy selector (continuous)

DECISION FLOW:
  1. Regime detector → Select strategy profile
  2. Fundamental screen → Eliminate unsafe positions
  3. GA weights → Strategic allocation
  4. NN signals → Tactical overweight/underweight
  5. RL agent → Daily position management
  6. ATR stops → Hard exit rules (override everything)
```

---

## 8. PHP Web Dashboard (Built on Correct Data)

### 8.1 Pages
```
/dashboard          — Portfolio overview, P&L, allocation pie chart
/symbols            — All 404+ symbols with indicators, sortable
/ga-results         — GA optimization results, weight evolution over time
/nn-predictions     — NN predictions vs actual, error bars, confusion matrix
/rl-activity        — RL agent actions, reward curve, trade log
/fundamentals       — Dividend safety scores, payout ratios, The Brick detector
/regime             — Current regime, VIX, credit spreads, yield curve
/rebalance          — ETF front-running calendar, upcoming rebalance dates
/backtest           — Walk-forward results, rolling Sharpe, max drawdown
/settings           — Config editor, parameter tuning
```

### 8.2 Charts (using Chart.js)
```
- Portfolio value over time (with drawdown shading)
- GA weight evolution (stacked area chart)
- NN prediction vs actual (scatter plot with error bars)
- Indicator correlation heatmap (prove TA is noise)
- Dividend safety score distribution
- Regime timeline (color-coded bull/bear/transition)
- ETF rebalance calendar (with front-run trade markers)
- Rolling Sharpe ratio (1-year window)
```

---

## 9. Implementation Order

### Phase 1: Fix the Foundation
1. Rewrite simulator for DAILY operation with REAL stop-losses
2. Add fundamental data layer (earnings, FCF, payout ratios)
3. Add regime detection module
4. Build ETF rebalance calendar scraper

### Phase 2: Retrain Agents
1. GA: Walk-forward optimization with daily simulation
2. NN: Add fundamental + macro features
3. RL: Daily action space with transaction costs
4. Blender: Combine all signals

### Phase 3: PHP Dashboard
1. PHP 7.4 framework setup (PSR-4, Ksf\StockMarket\)
2. MySQL read layer + API endpoints
3. Dashboard pages with Chart.js visualizations
4. Real-time portfolio monitoring

### Phase 4: Automation
1. Daily cron: fetch data, update indicators, check stops
2. Weekly cron: NN predictions, dividend safety scan
3. Monthly cron: rebalance, ETF front-running
4. Quarterly cron: full retrain, Blender update
5. Regime shift: emergency retrain trigger

---

## 10. Key Metrics to Track

| Metric | Target | Why |
|--------|--------|-----|
| Max Drawdown | < 20% | Preserve capital in crashes |
| Sharpe Ratio | > 1.0 | Risk-adjusted returns |
| Dividend Cut Rate | < 5% | Avoid The Brick scenario |
| Turnover | < 200%/yr | Control transaction costs |
| Regime Detection Accuracy | > 60% | Timely strategy switching |
| Walk-Forward Consistency | > 70% positive periods | Not just one lucky stretch |
