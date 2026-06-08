# ICT-Style Trading Concepts
## Inner Circle Trader Framework Documentation

> **Source:** Michael J. Huddleston (ICT) / The Rumbers adaptations | **Category:** Institutional Order Flow

---

## Core Concepts

### Swing High/Low
**Definition:** A price level where the market made a significant high or low.

**Trading Significance:**
- Swing High: Higher than surrounding bars (resistance)
- Swing Low: Lower than surrounding bars (support)
- Used to define liquidity zones
- Extended swing levels (multi-day/week) are stronger than short-term

### Liquidity Sweep
**Definition:** A rapid price movement through a liquidity pool (stop loss zone) that triggers retail stops before reversing.

**Pattern:**
```
Price approaches Swing High/Low
↓
Wicks through (sweeps liquidity)
↓
Immediate reversal in opposite direction
```

**Detection:**
- Wick exceeds prior swing by 1-3 ticks
- Volume spike then immediate reversal
- Retests the swept level as support/resistance

### Break of Structure (BOS)
**Definition:** When price definitively moves past a prior swing point, indicating trend continuation.

**Confirmation:**
- Close above prior Swing High (bullish)
- OR close below prior Swing Low (bearish)
- Must hold for at least 2-3 bars
- Often precedes institutional accumulation/distribution

### Fair Value Gap (FVG)
**Definition:** A 3-candle pattern where price gaps and leaves an imbalance zone unfilled.

**Pattern:**
```
Candle 1: Low = 100, High = 105
Candle 2: Low = 110, High = 115 (gap up)
Candle 3: Low = 120, High = 125

FVG Zone: 105-110 (gap zone that should be filled)
```

**Trading Rules:**
- Enter on retrace to FVG zone
- FVG acts as support/resistance
- First touch often triggers reversal
- Can combine with Order Blocks

### Order Block (OB)
**Definition:** Institutional buying/selling zones where large orders were placed.

**Bullish Order Block:**
- Last red candle before up move
- Large volume (relative to recent)
- Price rejects below afterward

**Bearish Order Block:**
- Last green candle before down move
- Large volume
- Price rejects above afterward

**Key Insight:** OBs hold more profit potential than FVGs (per Revelio backtest)

### Equilibrium
**Definition:** Market balance zone between opposing forces (between dual order blocks).

**Characteristics:**
- Price oscillates within OB boundaries
- Mean reversion likely
- Breakouts often return to equilibrium

### Take Profit & Stop Loss Structure

| Level | R/R Ratio | Hit Rate |
|-------|-----------|----------|
| TP1 | 1R | 50% (most often hit) |
| TP2 | 2R | 25% |
| TP3 | 3R | 17% |

**Risk Sizing Rules:**
- Max win = 2R in practice
- Multiple TPs allow partial exits
- Risk per trade: 0.5-1% portfolio
- Stop beyond liquidity zone

---

## TJR Framework

### Components
**TJR = Sweep + Break of Structure + (FVG or Order Block)**

### Daily + Weekly Bias Filter
1. Determine daily bias (bullish/bearish/range)
2. Confirm with weekly trend
3. Only take trades in direction of bias
4. Avoid choppy/range days against bias

### Entry Process
```
1. Identify liquidity sweep on 15-min
2. Wait for BOS confirmation
3. Price retraces to FVG or Order Block
4. Check daily/weekly bias alignment
5. Enter in direction of bias
6. Set stop beyond sweep zone
7. Set TP1 at prior swing (1R)
```

### Revelio Backtest Results (10-year)
- ❌ TJR framework lost money
- ❌ More filters made results worse
- ✅ Order Blocks carried most profit
- ❌ Fair Value Gaps lost most
- ⚠️ Random forest model considered for prediction

---

## Moving Average Crossover (Baseline)

### Simple Implementation
```python
# 20/50 EMA crossover
if ema_20 > ema_50 and ema_20.shift(1) <= ema_50.shift(1):
    signal = "BUY"
elif ema_20 < ema_50 and ema_20.shift(1) >= ema_50.shift(1):
    signal = "SELL"
```

### Issues with Basic MAs
- Too many false signals
- Lag behind price
- Need confluence with order flow concepts

---

## TradingView Integration

### Pine Script Requirements
- 15-minute timeframe primary
- Previous day HLC for pivots
- Swing high/low detection (lookback: 20-50 bars)
- Volume analysis for sweeps
- Alert conditions for backtesting

### Key Indicators Needed
- [x] Swing High/Low
- [x] Volume profile / liquidity sweep detector
- [x] Order block zones
- [x] FVG zones
- [x] Bias filters (daily/weekly)

---

## Action Items

- [ ] Create intraday_15min table schema for MariaDB
- [ ] Backtest TJR with Order Block only (not FVG)
- [ ] Implement bias filter logic
- [ ] Create TradingView Pine Script for alerts
- [ ] Compare TP hit rates empirically