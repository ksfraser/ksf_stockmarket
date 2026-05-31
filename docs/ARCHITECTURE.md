# Investment Agent — Architecture & Specification

> **Version:** 3.0 | **Date:** 2026-05-30 | **Repo:** `ksfraser/ksf_stockmarket`
> **Status:** Phase 1 complete (data + tax + allocation). Phase 2 in progress (GA/NN/RL agents).

---

## 1. Problem Statement

**Objective:** Maximize after-tax portfolio value over a 10-year horizon, subject to annual December withdrawals for living expenses, to reach a retirement target of $250,000.

**Context:**
- Kevin Fraser, Airdrie Alberta, 3rd tax bracket ($111K-$173K taxable income)
- Accounts: TFSA ~$20K, RRSP ~$30K initial
- CIBC Investor's Edge brokerage (TSX free trades, US at $9.95/trade)
- Annual withdrawal: $12K in December
- TFSA room: $7K/yr, RRSP room: ~$6K/yr
- Transition income may decline (part-time) — creates RRSP deregistration opportunity

---

## 2. Design Principles

### 2.1 Sleeves Not Consensus
Strategies are **competing allocation buckets**, not voting signals. Each sleeve has:
- Its own entry/exit rules
- Its own time horizon
- Its own signal set
- Its own position sizing model

The Blender optimizes how much capital goes to each sleeve, not how signals are averaged.

### 2.2 Everything Is Configurable
Every numeric parameter lives in `config.yaml`. Defaults are research-backed but overridable. The GA/NN/RL agents optimize subsets of these parameters during walk-forward training.

### 2.3 Walk-Forward Only — No Future Peeking
All analysis uses strict `data[:current_date]` cut-off. Training window rolls forward annually.

### 2.4 Tax-Aware at Every Layer
Tax impact is computed at every decision point — entry, rebalance, exit, harvest. Account placement (which sleeve goes in which account) is part of the optimization.

### 2.5 Forex Matters
USD/CAD trends affect US vs CDN allocation. The GA includes forex as a feature signal. Forex shift is bounded ±5% per signal to avoid overreacting to noise.

### 2.6 Per-Indicator Horizon Selection
From the 222-indicator correlation study:
- **Short (1-5d):** Bollinger position, MA deviation → entry timing
- **Medium (10-20d):** RSI, MACD, ADX, NATR → direction, regime, sizing
- **Quarterly (90d):** Dividend calendar, FCF seasonality → cash flow planning
- Candlestick patterns: uniformly noise at all horizons → **dropped entirely**

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (weekly)                     │
│  Runs Layer 0, triggers Layer 1 daily, feeds GA/NN/RL       │
└──────────────────────────┬──────────────────────────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     ▼                     ▼                     ▼
┌─────────┐         ┌──────────┐         ┌──────────┐
│ Layer 0  │         │ Layer 1  │         │ Layer 2  │
│ Screener │────────▶│ Signals  │────────▶│ Money    │
│ (weekly) │         │ (daily)  │         │ Mgt      │
└─────────┘         └──────────┘         └──────────┘
     │                     │                     │
     ▼                     ▼                     ▼
┌─────────┐         ┌──────────┐         ┌──────────┐
│ Layer 3  │         │ Layer 4  │          │Agents    │
│ Portfolio│         │ Risk     │         │GA/NN/RL │
│ Construct│         │ Mgt      │         │(weekly)  │
└─────────┘         └──────────┘         └──────────┘
     │                     │                     │
     ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────┐
│              BLENDER (quarterly rebalance)                │
│  GA weight × static allocation                            │
│  NN weight × tactical timing                              │
│  RL weight × dynamic rebalancing                          │
│  → Final positions per sleeve                             │
└──────────────────────────────────────────────────────────┘
```

### 3.1 Layer 0 — Universe Screener (weekly, Sundays)
**Input:** 404 symbols from CurrentData/ + portfolio holdings
**Output:** Per-sleeve candidate list in MySQL `layer0_candidates`

```
For each symbol:
  1. Fetch price, volume, market cap
  2. Global hard filter: price > $5, volume > 100K/day, cap > $500M
  3. CIBC Investor's Edge eligibility check
  4. For each active sleeve:
     a. Fetch fundamentals from yfinance (ROE, D/E, FCF, margins, div)
     b. Buffett score (0-100)
     c. Apply sleeve-specific filters
     d. Tag symbol with sleeve(s) it qualifies for
  5. Save top N per sleeve to DB
```

**Sleeve-specific screening criteria:**
| Criteria | Core (Buffett) | Tactical (Swing) | Income (Div) | Satellite (Spec) |
|---|---|---|---|---|
| ROE min | 15% | 10% | 10% | 5% |
| D/E max | 0.3 | 0.8 | 0.6 | — |
| FCF streak | 5yr | 2yr | — | — |
| Gross margin | 40% | 25% | — | — |
| Volatility | < 1.2 beta | 20-50% | — | > 30% |
| Div yield | — | — | > 2.5% | < 2% |
| Market cap | > $5B | > $1B | > $2B | > $500M |

### 3.2 Layer 1 — Signal Generation (daily, market close)
**Input:** Layer 0 candidates + 120 indicators from `indicators` table
**Output:** Per-symbol signals per sleeve in MySQL `signals_daily`

```
For each candidate in each sleeve:
  a. Short-horizon: BB position (3d), MA deviation, RSI
  b. Medium-horizon: RSI(14/21), MACD, ADX, NATR(7/14/20)
  c. Regime: ADX > 20 required for trend trades
  d. Volume: OBV > 50d average
  e. Conviction: count agreeing signals / total signals
  f. Output: signal_strength [-1, 1], conviction [0, 1]

  For Income sleeve additionally:
  g. Dividend calendar: days to ex-div, yield on cost
  h. Quality check: earnings trend, payout trajectory
```

### 3.3 Layer 2 — Money Management (on each signal + monthly)
**Input:** Signals from Layer 1 + current portfolio state
**Output:** Orders (buy quantity, DCA schedule, stop price)

```
For each BUY signal:
  1. Position sizing:
     - ATR risk model: shares = (portfolio × risk_pct) / (ATR × stop_mult)
     - Kelly (satellite only): f* = (bp - q) / b, quarter-Kelly
     - Yield-weighted (income): higher yield = larger allocation
  2. DCA schedule: 2-3 installments over 5-20 days
  3. Stop loss: entry - N×ATR (N varies by sleeve)
  4. Account placement: which account type for this symbol
  5. Trailing stop activation: triggered at +3% profit

For each position (monthly):
  6. Rebalance check: drift > 5% from target
  7. Stop check: price below ATR stop
  8. Conviction check: if signal strength < 0.3 → EXIT
  9. Time stop: if held beyond sleeve max days → EXIT
```

### 3.4 Layer 3 — Portfolio Construction (monthly)
**Input:** All orders from Layer 2 + tax-loss harvesting triggers + forex signal
**Output:** Executed portfolio state in MySQL `portfolio`

```
1. Process BUY orders (DCA on schedule)
2. Process SELL orders (exits, stops)
3. Tax-loss harvest: Dec only if unrealized loss > 5% and saves > $50 tax
4. Forex geo-shift: if USD/CAD 20d trend rising → +5% US, -5% CDN (bounded)
5. Diversification check:
   - Max 15 names total
   - Max 25% single sector
   - Geographic constraints per forex-aware config
6. Cash buffer: maintain 5%
7. Move to next sleeve if conviction deteriorates
```

### 3.5 Layer 4 — Risk Management (continuous)
**Input:** Portfolio state + market data + VIX + correlations
**Output:** Risk alerts + emergency actions

```
Continuous monitoring:
  1. Portfolio drawdown > 15% → reduce position sizes 50%
  2. Portfolio drawdown > 25% → shift 30% to cash
  3. VIX > 30 → halve new position sizes
  4. VIX > 40 → emergency cash shift
  5. Single position drops 3% in a day → review for exit
  6. Portfolio avg correlation > 0.75 → reduce concentration
  7. RRSP dereg check: if income forecast < $55K → model withdrawal sweep
```

---

## 4. Agent Ensemble

### 4.1 GA (DEAP) — Strategic Allocation Optimizer
**Purpose:** Find the optimal static allocation across sleeves and symbols within each sleeve.

**Input:** Historical returns (after-tax), indicator correlations, forex trends, tax rates
**Output:** Optimal sleeve weights + symbol weights within each sleeve

**Fitness function:**
```
fitness = after_tax_terminal_value - λ_dd × max_drawdown - λ_cash_depletion × I(portfolio_hits_0)
```

**GA optimizes:**
- Sleeve allocation percentages (within global constraints)
- Symbol weights within each sleeve (within sleeve constraints)
- DCA installments and stop multipliers (continuous parameters)
- Forex shift sensitivity (how aggressively to rebalance on USD/CAD signal)

**Training:** Walk-forward 2014-2018, test 2019-2024. Population 200, generations 100.

### 4.2 NN (PyTorch LSTM) — Tactical Return Predictor
**Purpose:** Predict 20-day forward return distribution for each candidate symbol.

**Input:** 60-day sequence of 120 indicators per symbol
**Output:** Mean and variance of expected 20-day return

**Architecture:** 2-layer LSTM (128 hidden, dropout 0.2), linear output head with uncertainty.

**Training:** Walk-forward on Layer 0 candidate symbols. Train on 5 years, validate on 1 year.

**Use:** Feed expected returns into the GA as prior estimates. NN confidence (inverse variance) weights GA evaluation.

### 4.3 RL (SB3 PPO) — Dynamic Rebalancing Agent
**Purpose:** Learn when to deviate from GA static allocation based on market conditions.

**State:** Portfolio composition + signal consensus + market regime (ADX, VIX) + time since last rebalance
**Action:** For each position: [-1 sell half, -0.5 trim, 0 hold, +0.5 add, +1 double] + account transfer decisions
**Reward:** Daily after-tax P&L − transaction_cost − risk_penalty

**Training:** 100K timesteps per walk-forward step, rolling annually.

### 4.4 Blender
**Purpose:** Combine the three agents' outputs into final portfolio decisions.

```
final_weight(symbol) = 
  GA_weight × GA_static_weight(symbol) +
  NN_weight × NN_tactical_adjustment(symbol) +
  RL_weight × RL_dynamic_adjustment(symbol)

where GA_weight + NN_weight + RL_weight = 1.0
```

**Rebalancing:** Every 90 days, re-blend based on trailing 90-day Sharpe ratio of each agent.

---

## 5. Key Research Findings (From 222-Indicator Study)

### Indicator Horizons
| Horizon | Avg |corr| | Max |corr| | Best For |
|---|---|---|---|---|
| 1d | 0.016 | 0.047 | NATR only |
| 3d | 0.027 | 0.096 | Bollinger, MA deviation |
| 5d | 0.035 | 0.096 | Entry timing |
| 10d | 0.052 | 0.127 | Direction, regime |
| 20d | 0.066 | **0.162** | NATR, position sizing, worst-case planning |

### Indicator Groups by Use
| Use | Indicators | Horizon |
|---|---|---|
| **Stock selection** | NATR_7/14/20, STDDEV_14, VAR_14 | 20d |
| **Entry timing** | BB position, MA deviation, short NATR | 3-5d |
| **Direction** | RSI, MACD(12,26,9), ADX | 20d (regime filters) |
| **Position sizing** | NATR (inverse relationship) | 20d |
| **Confirmation** | OBV rising, volume > 50d avg | 20d |
| **Candlestick patterns** | ALL 59: noise | ALL: ignore |

---

## 6. Database (MySQL at ksfraser.ca)

| Table | Purpose | Key Columns |
|---|---|---|
| `stockprices` | OHLCV daily prices | symbol, price_date, close, volume — partitioned by YEAR |
| `indicators` | 120 TA-Lib indicators | symbol, price_date, natr_7.., rsi_14.., macd_.. — partitioned |
| `indicator_correlation` | Cached correlation study | indicator, horizon, avg_corr, verdict |
| `symbol_master` | 404-symbol universe | symbol, geography, sector, is_portfolio |
| `layer0_candidates` | Weekly screener output | symbol, sleeve, buffet_score, div_yield |
| `signals_daily` | Layer 1 signals | symbol, sleeve, signal_strength, conviction |
| `portfolio` | Current positions | symbol, acct_type, shares, cost_basis, entry_date |
| `evalsummary` | Scoring engine output | symbol, date, consensus_signal, position_size |
| `tax_parameters` | CDN tax data | bracket, rates, DTC, gross_up |
| `allocation_strategies` | Strategy definitions | name, type, geo_weights |
| `after_tax_returns` | Results storage | date, strategy, pre_tax, tax, after_tax |
