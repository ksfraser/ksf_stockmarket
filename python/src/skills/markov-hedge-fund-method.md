---
name: markov-hedge-fund-method
category: finance
description: |
  Markov regime detection framework for dynamic strategy weighting. Adapts strategy
  weights based on detected Bull/Bear/Sideways market regimes.
  
homepage: https://github.com/jackson-video-resources/markov-hedge-fund-method
tags: [markov, regime, transition-matrix, backtesting]
---

# Markov Hedge Fund Method

Dynamic strategy weighting based on market regime detection.

## How It Works

1. Labels each day as Bull/Bear/Sideways using 20-day rolling return (±5% threshold)
2. Builds 3×3 transition matrix from state sequence
3. Computes stationary distribution via power iteration
4. Adjusts strategy weights in Layer 3 portfolio construction

## Integration

**PHP (StockController.php)**: `getRegimeAnalysis()` - computes regime directly from MariaDB
**Python (trading_pipeline_v3.py)**: `REGIME_WEIGHTS` dict adjusts signal scoring

### Regime-Based Strategy Weights

| Regime | Strategies Boosted | Weight |
|--------|-------------------|--------|
| Bull | SMA cross, Turtle, 4week | 1.3-1.5 |
| Bear | Bollinger MR, RSI, Z-score | 1.3-1.5 |
| Sideways | Bollinger MR, Donchian, Sneaky Pivot | 1.4 |

## Displayed On Symbol Detail Page

- Current regime badge (color-coded)
- Stationary distribution (long-run regime mix)
- 3×3 transition matrix table

## Parameters

| Parameter | Default | Meaning |
|-----------|---------|---------|
| window | 20 | Rolling return window in days |
| threshold | 0.05 | ±5% for Bull/Bear classification |
| iterations | 50 | For stationary distribution convergence |

## Python Module (regime/markov_regime.py)

```python
from regime.markov_regime import label_regimes, build_transition_matrix

# Detect regimes: 0=Bear, 1=Sideways, 2=Bull
regimes = label_regimes(close_prices, window=20, threshold=0.05)

# Build transition probability matrix
P = build_transition_matrix(regimes)
```