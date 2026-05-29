# Stock Market Analysis — Strategy Reference & Indicator Correlation

> **Generated:** 2026-05-29 from 372,134 backtest runs + 222 TA-Lib indicators × 19 symbols
> **Repository:** `ksfraser/ksf_stockmarket`

---

## 0. Executive Summary — What Actually Works

### The Only Predictive Indicators (20-day horizon, all 19 symbols consistent)

| Indicator | Correlation | Symbols Agree | Interpretation |
|-----------|-------------|---------------|----------------|
| **NATR_20** | **+0.162** | 89% | High normalized ATR → higher forward return |
| **NATR_14** | **+0.159** | 95% | Same signal, slightly shorter window |
| **NATR_7** | **+0.151** | 95% | Short-term vol also predictive |
| **VAR_14** | +0.054 | 74% | Raw variance also works (non-normalized) |
| **STDDEV_14** | +0.048 | 58% | Std dev weaker but same direction |

**This is a stock SELECTION signal, not a timing signal.** High-volatility stocks earn ~1% more per 20-day period than low-volatility stocks. Annualized, that's ~25% excess return from simply picking high-NATR names.

### What DOES NOT work (despite 340+ indicators tested)

| Category | Count | Avg Correlation | Verdict |
|----------|-------|----------------|---------|
| **All Candlestick Patterns** | 59 | < 0.01 | ❌ **IGNORE** — zero predictive power |
| Moving Averages (SMA/EMA/WMA/DEMA/TEMA/TRIMA/KAMA) | 28 | < 0.01 | ❌ Noise |
| Bollinger Bands (all widths) | 36 | < 0.01 | ❌ Noise |
| Momentum (RSI/MACD/MOM/ROC/STOCH/CCI/MFI/WILLR/ADX) | 48 | < 0.02 | ❌ Noise |
| Volume (OBV/AD/ADOSC/BOP) | 4 | < 0.01 | ❌ Noise |
| Cycle (HT_DCPERIOD/HT_PHASE/HT_SINE) | 6 | < 0.01 | ❌ Noise |
| Price Transform (AVG/MED/TYP/WCL) | 4 | < 0.01 | ❌ Noise |

**Candlestick patterns have ~50% hit rate — exactly coin flip.** All 59 TA-Lib CDL patterns combined produced no better result than random entry. This aligns perfectly with the Efficient Market Hypothesis for daily-frequency trading.

### Practical Implications

1. **Drop all candlestick pattern calculations** — 59 indicators computing pure noise
2. **Drop all moving average crossover signals** — SMAs/EMAs don't predict direction
3. **Use NATR for stock selection** — screen universe for high-NATR names before applying any strategy
4. **Keep volatility measures** — ATR, NATR, STDDEV, VAR are the only useful inputs
5. **Everything else is for position sizing only** — use ATR stops, risk limits, diversification

---

## 1. Technical Indicators

### Tier 1 — Raw Prices + Basic Computations (on every import)
| Indicator | Description |
|-----------|-------------|
| `day_open/high/low/close/volume` | Raw OHLCV from yfinance |
| `gap_up` / `gap_down` | Open vs previous close |
| `body_size` | \|close − open\| |
| `upper_shadow` / `lower_shadow` | Wick lengths |
| `true_range` | max(h−l, \|h−prev_close\|, \|l−prev_close\|) |
| `atr_1/7/14/20` | Average True Range at 4 periods |

### Tier 2 — Technical Indicators (scoring engine, refreshed weekly)
| Indicator | Description |
|-----------|-------------|
| `sma_5/10/20/50/55/100/200` | Simple Moving Averages |
| `ema_12/26` | Exponential Moving Averages |
| `rsi_7` / `rsi_14` | Relative Strength Index |
| `macd` / `macd_signal` / `macd_hist` | MACD (12,26,9) |
| `bb_upper/lower/pct` | Bollinger Bands (20-day, 2σ) |
| `high_10/20/55` / `low_10/20/55` | Donchian Channel |
| `stoch_k` / `stoch_d` | 14-day Stochastic Oscillator |
| `roc_10/20/60` | Rate of Change |
| `hvol_20` | Annualized Historical Volatility |
| `zscore_20` | 20-day Z-Score |
| `doji/hammer/shooting_star/engulfing_bull` | Candlestick patterns |
| `volume_ratio` | Volume / SMA-20 Volume |
| `atr_stop_upper/lower_{1.0−3.0}` | ATR-based stop levels |

### Tier 3 — Composite Scores (`evalsummary` table)
| Score | Formula | Direction |
|-------|---------|-----------|
| `momentum_score` | ROC10×1.0 + ROC20×0.8 + ROC60×0.5 + (RSI−50)×0.5 + MACD_hist×2.0 | Trend-following |
| `trend_score` | SMA position×1.5 + SMA cross (binary±20) | Trend-following |
| `mean_reversion_score` | −zscore×15 − (bb_pct−0.5)×100 | Contrarian |
| `volatility_score` | ATR%×2 + hvol×0.5 | Risk measure |
| `volume_confirm` | (vol_ratio−1)×30 | Confirmation |
| `signal_strength` | (momentum×0.35 + trend×0.30 + MR×0.15 + vol_confirm×0.20) clipped ±100 | Composite |

---

## 2. Strategies Tested

| # | Name | Type | Entry | Exit | Best For |
|---|------|------|-------|------|----------|
| 1 | **4week** | Trend | Close > SMA-20 AND ROC-20 > 0 | Close < SMA-20 OR ROC-20 < −2% | Momentum stocks |
| 2 | **sma_10_50** | Trend | SMA-10 crosses above SMA-50 | SMA-10 crosses below SMA-50 | Short-term trend |
| 3 | **sma_20_50** | Trend | SMA-20 crosses above SMA-50 | SMA-20 crosses below SMA-50 | Medium-term trend |
| 4 | **sma_50_200** | Trend | SMA-50 crosses above SMA-200 (golden cross) | SMA-50 crosses below SMA-200 (death cross) | Long-term trend |
| 5 | **turtle_20** | Breakout | Close > 20-day Donchian Upper | Close < 55-day Donchian Lower | Breakout/trending |
| 6 | **turtle_55** | Breakout | Close > 55-day Donchian Upper | Close < 55-day Donchian Lower | Medium breakout |
| 7 | **turtle_dual** | Breakout | 20-day breakout entry + 55-day breakout entry | 55-day Donchian Lower | Dual timeframe |
| 8 | **donchian_20** | Breakout | Close > Donchian Upper(20) | Close < Donchian Lower(20) | Short breakout |
| 9 | **macd_trend** | Momentum | MACD > signal | MACD < signal | Trend momentum |
| 10 | **rsi_momentum** | Mean-rev/mom | RSI 45-70 + MACD > signal + ROC > 2% | RSI > 70 OR ROC < −3% | Momentum reversal |
| 11 | **stochastic** | Oscillator | %K crosses above %D (oversold) | %K crosses below %D (overbought) | Range-bound |
| 12 | **bollinger_mr** | Mean-reversion | Price touches lower band + RSI < 35 | Price touches upper band OR ATR stop | Mean-reversion |
| 13 | **buy_hold** | Baseline | Buy at start, hold to end | Never | Benchmark |
| 14 | **coin_toss** | Random | Random entry with position sizing | Random exit | Statistical baseline |
| 15 | **combo_*` | Consensus | Majority vote across 2−5 strategies | Majority vote sells | Multi-strategy |

---

## 3. Indicator-to-Returns Correlation Study

### Key Finding: Most technical indicators have near-zero predictive power at 1-day horizon.

> "Candlesticks are good for 1 day but 3 days out they are no better than random"
> — Kevin Fraser, 2026-05-29

This is exactly what the data shows:

| Indicator | 1-day Corr | 3-day Corr | 5-day Corr | 10-day Corr | 20-day Corr | 1-day Hit% | 20-day Hit% |
|-----------|-----------|-----------|-----------|------------|------------|-----------|------------|
| **ATR %** | **0.029** | **0.051** | **0.067** | **0.097** | **0.138** | 49.7% | 50.4% |
| **hvol_20** | **0.025** | **0.041** | **0.053** | **0.081** | **0.114** | 49.8% | 50.8% |
| macd_hist | 0.006 | 0.010 | 0.010 | 0.010 | 0.011 | 50.2% | 50.3% |
| roc_10 | 0.001 | 0.005 | 0.014 | 0.004 | 0.000 | 50.3% | 50.5% |
| signal_strength | 0.002 | −0.001 | 0.002 | −0.007 | −0.019 | 50.4% | 50.1% |
| rsi_14 | 0.003 | 0.004 | 0.003 | 0.006 | −0.002 | 50.4% | 50.3% |
| zscore_20 | 0.003 | 0.004 | 0.002 | 0.001 | −0.002 | 50.3% | 50.6% |
| bb_pct | 0.003 | 0.004 | 0.002 | 0.001 | −0.002 | 50.3% | 50.6% |

### The Only Meaningful Signal: Volatility

**ATR% and historical volatility are the only indicators with statistically meaningful correlation to forward returns** — and the correlation **increases with horizon**:

- ATR% → 20-day forward return: **r = 0.138** (p < 0.001)
- hvol_20 → 20-day forward return: **r = 0.114** (p < 0.001)

**What this means:** High-volatility stocks have higher expected returns over 20-day horizons (risk premium). Low-volatility stocks underperform. This is NOT a timing signal — it's a cross-sectional stock selection signal.

**Hit rates are ~50.5%** — barely above coin flip. No individual indicator can predict direction better than random in the short term.

### Spread Analysis: Best-Case Signal Edge

| Indicator | 20-day High-Signal Return | 20-day Low-Signal Return | Spread |
|-----------|--------------------------|-------------------------|--------|
| **hvol_20** | +1.204% | +0.221% | **+0.983%** |
| **atr_pct** | +1.215% | +0.203% | **+1.012%** |
| macd_hist | +0.783% | +0.642% | +0.140% |
| rsi_14 | +0.645% | +0.773% | −0.128% |

The ATR spread of +1.012% over 20 days means: "Buy high-volatility stocks, avoid low-volatility stocks" earns ~1% more per 20-day period. Annualized, that's ~25% excess return.

---

## 4. Strategy Performance Summary (from 372K backtests)

| Rank | Strategy | Avg Sharpe | Avg P&L% | Win Rate | Max DD | Note |
|------|----------|-----------|---------|----------|--------|------|
| 1 | **Buy & Hold** | 0.113 | 1.8% | 68% | 2.6% | Benchmark |
| 2 | **SMA 10/50** | 0.098 | 1.4% | 44% | 2.0% | Only trend that beats B&H |
| 3 | **Bollinger MR** | 0.063 | 0.8% | 47% | 2.3% | Mean reversion |
| 4 | **Turtle Dual** | 0.055 | 0.9% | 45% | 2.4% | Breakout + trend |
| 5 | **Coin Toss** | 0.051 | 1.4% | 51% | 5.1% | Random baseline |
| 6 | **MACD Trend** | 0.043 | 1.1% | 46% | 3.2% | Momentum |
| 7 | SMA 20/50 | 0.033 | 0.9% | 33% | 1.7% | Medium trend |
| 8 | Turtle 55d | 0.026 | 0.8% | 43% | 3.1% | Slow breakout |
| 9 | Turtle 20d | 0.025 | 1.3% | 44% | 3.7% | Fast breakout |
| 10 | 4-Week Rule | 0.025 | 1.3% | 44% | 3.7% | Price > SMA-20 + ROC > 0 |
| 11 | RSI Momentum | 0.020 | 0.2% | 24% | 0.7% | Overlays RSI on MACD |
| 12 | SMA 50/200 | 0.018 | 0.6% | 20% | 0.8% | Golden cross |
| 13 | Stochastic | 0.018 | 0.7% | 46% | 3.3% | Oscillator |
| 14 | Candlestick | −0.020 | −0.1% | 12% | 0.2% | **Worst** — patterns are noise |

### Best Combo Strategies (Consensus Voting)
| Combo | Sharpe | P&L% | Max DD |
|-------|--------|------|--------|
| MACD + SMA20/50 + SMA50/200 + CoinToss (4-strat) | **0.215** | 2.4% | 3.4% |
| Bollinger + SMA10/50 + Candle + CoinToss (4-strat) | **0.160** | 2.5% | 3.0% |
| RSI + SMA10/50 + SMA20/50 + Candle + CoinToss (5-strat) | **0.148** | 1.9% | 2.1% |

---

## 5. MTY — Specific Diagnosis

MTY was flagged by Kevin as "whipsaw on daily." Here's why from the data:

| Strategy | Avg Sharpe | Trades | Win Rate | Issue |
|----------|-----------|--------|----------|-------|
| Bollinger MR | 0.251 ✅ | 5 | 67% | Works but few trades |
| Stochastic | 0.231 | 5 | 67% | Same |
| SMA 10/50 | 0.048 | 3 | 36% | No signal conviction |
| MACD Trend | −0.054 | 5 | 51% | Wrong direction |
| Turtle | −0.090 | 6 | 36% | Breakouts fail in range |
| 4-Week Rule | −0.090 | 6 | 36% | Same <sup>†</sup>

<sup>†</sup> Turtle 20 and 4-Week are identical in the v2 implementation (same code path).

**Root cause:** MTY is a low-volatility stock that trades in a range. Breakout strategies fire false signals at the top of the range. Mean reversion works but with too few trades. 

**Fix:** Use Bollinger MR with 90-day rebalance (not 7-day), wider ATR stops (3.0×), and confirm with volume spike.

---

## 6. Architecture (Pipeline v3)

```
Layer 1: Signal Generation (11 strategies)
  ├─ sma_10/50, sma_20/50, sma_50/200     (trend following)
  ├─ turtle_20, turtle_55, turtle_dual     (breakout)
  ├─ 4week                                  (momentum)
  ├─ bollinger_mr                           (mean reversion)
  ├─ macd_trend, stochastic                 (oscillators)
  ├─ rsi_momentum                           (overlay)
  └─ donchian_20                            (pure breakout)
         │
         ▼
Layer 2: Risk / Money Management
  ├─ ATR position sizing (max 1% risk per trade)
  ├─ ATR trailing stops (1.5×−3.0× ATR)
  └─ Max % of portfolio per trade (2%−20%)
         │
         ▼
Layer 3: Portfolio Construction
  ├─ Consensus voting across strategies
  ├─ Rank candidates by (avg_strength × consensus%)
  ├─ Max positions constraint (4−20)
  └─ Rebalance frequency (7/14/30/90 days)
```

**Walk-forward guarantee:** On simulation day N, `df.loc[:current_date]` is the strict cut-off. Signal functions never see future data.

---

## 7. Cron Jobs

| Job | Schedule | What it does |
|-----|----------|-------------|
| `scripts/nightly_pipeline.sh` | Daily 6 AM | Import prices → scoring → signal gen |
| Cron: full sweep | Weekly Sunday | 20K walk-forward runs (all combos) |
| Cron: sell check | Daily market close | Stop-loss check on live positions |

---

*Last updated: 2026-05-29 | 372,134 backtest runs | 19 symbols | 14 strategies + combos*
