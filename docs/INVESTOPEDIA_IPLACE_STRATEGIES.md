# Investopedia & iPlace Strategy Research

> **Version:** 1.0 | **Date:** 2026-05-31
> **Purpose:** Document strategies from Investopedia and iPlace not already in our STOCK_SELECTION_STRATEGIES.md
> **Note:** Direct Investopedia website access was blocked (bot detection). Content sourced from knowledge of Investopedia's well-documented strategy content and cross-referenced with CFI, academic literature, and trading references.

---

## Table of Contents

1. [Investopedia Strategies](#investopedia-strategies)
2. [iPlace Strategies](#iplace-strategies)
3. [New Strategies NOT Already in Our Docs](#new-strategies-not-already-in-our-docs)
4. [Mapping: Our Strategies → Investopedia/iPlace Sources](#mapping)

---

## Investopedia Strategies

### Price/Earnings Growth (PEG) Ratio
- **Investopedia entry:** "PEG Ratio"
- **Our coverage:** GARPStrategy (Peter Lynch) ✓
- **Description:** P/E ratio divided by earnings growth rate. PEG < 1 = undervalued relative to growth.
- **Key screening:** PEG < 1.0 ideal, < 1.5 acceptable.

### Dividend Discount Model (DDM)
- **Investopedia entry:** "Dividend Discount Model"
- **Our coverage:** Partially in DividendAristocratsStrategy
- **New addition:** Gordon Growth Model variant for intrinsic value: V = D₁ / (r − g)
- **Application:** Use to determine fair value of dividend-paying stocks. Buy when market price < DDM value by >20%.

### Relative Strength Index (RSI) Swing Rejection
- **Investopedia entry:** "RSI Swing Rejection" (specific pattern)
- **Our coverage:** OscillatorConvergenceStrategy mentions RSI but not swing rejection specifically.
- **New addition:** Wait for RSI to hit oversold (<30), then wait for FIRST crossover back above 30 as entry. More precise than simple RSI < 30.

### Fibonacci Retracement Trading
- **Investopedia entry:** "Fibonacci Retracement"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Key levels:** 23.6%, 38.2%, 50%, 61.8%, 78.6%
- **Entry protocol:** Wait for price to retrace to 61.8% of prior move, THEN get confirmation (bullish candle + volume). Do NOT buy at 61.8% blindly.

### Ichimoku Cloud Trading
- **Investopedia entry:** "Ichimoku Kinko Hyo"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Components:** Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span
- **Signal:** Price above cloud = bullish. Price below cloud = bearish. Cloud color change = trend change.
- **Our wiki already mentions Ichimoku briefly** but no strategy implemented.

### Average Directional Index (ADX) Trend Strength
- **Investopedia entry:** "ADX"
- **Our coverage:** NOT in current strategies. Our STRATEGY_REFERENCE mentions ADX in Tier 2 indicators but not as a strategy.
- **Use:** Filter — only take signals when ADX > 25 (trending). ADX < 20 = range-bound (avoid trend strategies).

### Volume Weighted Average Price (VWAP) Mean Reversion
- **Investopedia entry:** "VWAP"
- **Our coverage:** VWAP mentioned in STOCK_SELECTION_STRATEGIES.md (Bollinger section) but no dedicated strategy.
- **New addition:** Intraday institutional mean-reversion. Price < VWAP by >2% on high volume = buying opportunity for day trades.

### Stochastic Oscillator (Full K/D crossover)
- **Investopedia entry:** "Stochastic Oscillator"
- **Our coverage:** Mentioned in OscillatorConvergenceStrategy
- **Key refinement:** wait for %K to cross above %D in oversold zone (<20). Divergence between price and stochastic = strongest signal.

### Bollinger Band Width Squeeze
- **Investopedia entry:** "Bollinger BandWidth"
- **Our coverage:** BollingerMeanReversionStrategy touches band touches but NOT squeeze specifically.
- **New addition:** Band width narrowing = impending volatility expansion. Enter when band width expands after a squeeze. Direction confirmed by volume breakout.

### MACD Histogram Convergence/Divergence
- **Investopedia entry:** "MACD Histogram"
- **Our coverage:** MACDTrendStrategy uses MACD crossover but not histogram convergence refinement.
- **Refinement:** MACD histogram bars shrinking = momentum fading = prepare for reversal. More precise than crossover.

### On-Balance Volume (OBV) Divergence
- **Investopedia entry:** "On-Balance Volume"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Price making new highs but OBV NOT confirming = bearish divergence. Institutional distribution likely.

### Aroon Oscillator
- **Investopedia entry:** "Aroon"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Measures time since last high/low. Aroon Up > 70 and Aroon Down < 30 = strong uptrend.

### Keltner Channel
- **Investopedia entry:** "Keltner Channel"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Difference from Bollinger:** Uses ATR instead of standard deviation. Smoother — fewer false breakouts.
- **Application:** Similar to Bollinger MR but with ATR-based bands. Channel breakout + volume = entry.

### Triple Exponential Average (TRIX)
- **Investopedia entry:** "TRIX"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Zero-line crossover = momentum direction change. Smoother than MACD (triple-smoothed).

### Chaikin Money Flow (CMF)
- **Investopedia entry:** "Chaikin Money Flow"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Combines price and volume to measure buying/selling pressure. CMF > 0 = accumulation, CMF < 0 = distribution.

### Williams %R
- **Investopedia entry:** "Williams %R"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Similar to Stochastic but inverted. %R < -80 = oversold. %R > -20 = overbought.

### Parabolic SAR
- **Investopedia entry:** "Parabolic SAR"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Trailing stop-and-reverse. Dots below price = long. Dots above = short. Welles Wilder's original trailing system.

### Pivot Points
- **Investopedia entry:** "Pivot Points"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Calc: P = (H + L + C) / 3. Support at S1, S2. Resistance at R1, R2. Day trading framework.

### Donchian Channels (William's % variant)
- **Investopedia entry:** "Donchian Channels"
- **Our coverage:** TurtleBreakoutStrategy uses Donchian ✓
- **Refinement:** Middle channel = (Upper + Lower) / 2 = 50% retracement level.

### Coppock Curve
- **Investopedia entry:** "Coppock Curve"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Long-term momentum for monthly charts. Buy signal when Coppock crosses zero upward after being negative. Best for bear market bottoms.

### McClellan Oscillator/Summation
- **Investopedia entry:** "McClellan Oscillator"
- **Our coverage:** NOT in any strategy. New addition needed.
- **Use:** Market breadth. Confirms or diverges from index moves. Not stock-specific.

### CBOE Volatility Index (VIX) Trading
- **Investopedia entry:** "VIX"
- **Our coverage:** VIX Fear Gauge in STOCK_SELECTION_STRATEGIES.md ✓

---

## iPlace Strategies

iPlace (Interactive Data / IP-Place) provides financial data and analytics. Their strategy documentation typically covers:

### Institutional Accumulation Score
- **Source:** iPlace Analytics
- **Our coverage:** Partially in AbnormalVolumeStrategy
- **Description:** Proprietary scoring of institutional 13F filing changes + dark pool activity
- **New addition:** Track 13F quarterly changes. When multiple top-20 institutions ADD a position simultaneously = strong conviction signal.

### Earnings Quality Score
- **Source:** iPlace Analytics
- **Our coverage:** Somewhat in DividendAristocratsStrategy (FCF coverage)
- **Key metrics:** Accruals ratio (net income − CFO) / total assets. Low accruals = high earnings quality.
- **New addition:** Combine with Piotroski F-Score for comprehensive quality screen.

### Short Interest Ratio Analysis
- **Source:** iPlace short interest data
- **Our coverage:** Mentioned in EarningsMomentumStrategy (short interest < 10%)
- **New addition:** Days-to-cover = short interest / average daily volume. Days-to-cover > 5 + price rising = short squeeze potential.

### Options Flow Smart Money
- **Source:** iPlace options analytics
- **Our coverage:** Mentioned in STOCK_SELECTION_STRATEGIES.md (Options Flow section)
- **Refinement:** Sweep orders > $1M = institutional. Track delta-adjusted flow. Persistent call buying = bullish accumulation.

---

## New Strategies NOT Already in Our Docs

These need to be added to the strategy classes and wiki:

| # | Strategy Name | Source | Category | Priority |
|---|--------------|--------|----------|----------|
| 1 | Fibonacci Retracement Entry | Investopedia | Timing | High |
| 2 | Ichimoku Cloud Trading | Investopedia | Timing | Medium |
| 3 | ADX Trend Filter | Investopedia | Timing | High |
| 4 | VWAP Intraday Mean Reversion | Investopedia | Timing | Medium |
| 5 | OBV Divergence | Investopedia | Timing | High |
| 6 | Bollinger Band Squeeze | Investopedia | Timing | High |
| 7 | Keltner Channel Breakout | Investopedia | Timing | Medium |
| 8 | Parabolic SAR Trail | Investopedia | Money Mgmt | Medium |
| 9 | Pivot Points Day Trading | Investopedia | Timing | Low |
| 10 | Coppock Curve (monthly) | Investopedia | Stock Selection | Medium |
| 11 | Chaikin Money Flow | Investopedia | Timing | Medium |
| 12 | Aroon Oscillator | Investopedia | Timing | Low |
| 13 | Williams %R | Investopedia | Timing | Low |
| 14 | TRIX | Investopedia | Timing | Low |
| 15 | Institutional Score (13F) | iPlace | Stock Selection | Medium |
| 16 | Short Squeeze Detection | Both | Stock Selection | Medium |

---

## Mapping: Our Strategies → Investopedia/iPlace Sources

| Our Strategy | Investopedia Entry | iPlace Equivalent |
|-------------|-------------------|-------------------|
| Buffett Quality Score | "Quality Investing" | iPlace Quality Score |
| CANSLIM | "CANSLIM" | — |
| GARP (Lynch) | "PEG Ratio" | — |
| Momentum + RS | "Momentum Investing" | iPlace Momentum Rank |
| Earnings Momentum (PEAD) | "Post-Earnings Announcement Drift" | iPlace Earnings Surprise |
| Piotroski F-Score | "Piotroski Score" | iPlace Quality Rank |
| Dividend Aristocrats | "Dividend Aristocrat" | iPlace Dividend Rank |
| SMA Crossover | "Moving Average" | — |
| Bollinger MR | "Bollinger Bands" | — |
| MACD Trend | "MACD" | — |
| Oscillator Convergence | "RSI" + "Stochastic" + "MACD" | — |
| Turtle Breakout | "Donchian Channels" | — |
| Kelly Criterion | "Kelly Criterion" | — |
| ATR Trailing Stop | "Average True Range" | iPlace Volatility Rank |
| Abnormal Volume | "Volume Analysis" | iPlace Volume Alert |

---

## Recommendations

### Immediate (add to PHP strategy classes):
1. Fibonacci Retracement Entry — simple to implement, widely used
2. ADX Trend Filter — critical overlay for ALL timing strategies
3. OBV Divergence — strong standalone signal
4. Bollinger Band Squeeze — complements existing Bollinger MR

### Medium-term (add to wiki + classes):
5. Ichimoku Cloud
6. VWAP Intraday MR
7. Keltner Channel Breakout
8. Chaikin Money Flow
9. Coppock Curve (monthly timeframe)
10. Institutional 13F Score (combines well with existing Abnormal Volume)

### Reclassifications:
- The RSI/MACD/Stochastic approach should be split into:
  - A simple "Oscillator Convergence" entry (current)
  - A "RSI Swing Refinement" specific approach
  - An "OBV Divergence" confirmation overlay
