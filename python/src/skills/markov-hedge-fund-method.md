---
name: markov-hedge-fund-method
category: finance
description: |
  Markov regime detection framework for dynamic strategy weighting. Adapts strategy
  weights based on detected Bull/Bear/Sideways market regimes.
  
homepage: https://github.com/jackson-video-resources/markov-hedge-fund-method
tags: [markov, regime, transition-matrix, hmm, backtesting]
---

# Markov Hedge Fund Method

Dynamic strategy weighting based on market regime detection.

## Core Functions

```python
from regime.markov_regime import label_regimes, build_transition_matrix, stationary_distribution

# Detect current regime: Bear(0) / Sideways(1) / Bull(2)
regimes = label_regimes(price_series, window=20, threshold=0.05)

# Build transition matrix
P = build_transition_matrix(regimes)

# Forecast n-steps ahead
P_n = nstep_forecast(P, n=5)

# Get long-run distribution
stationary = stationary_distribution(P)
```

## Integration with trading_pipeline_v3

The `regime_weighted_strategy.py` module reads the current market regime and
adjusts strategy weights dynamically:

- **Bull market**: Momentum strategies (SMA cross, Turtle) get weight 1.5
- **Bear market**: Mean reversion (BB, RSI) gets weight 1.5
- **Sideways market**: Range-bound strategies (Donchian, Sneaky Pivot) get weight 1.4

## Regime Detection Parameters

| Parameter | Default | Meaning |
|-----------|---------|---------|
| window | 20 | Rolling return window in days |
| threshold | 0.05 | ±5% cutoff for Bull/Bear classification |
| min_train | 252 | Min training rows before walk-forward |

## CLI Usage

```bash
python regime/markov_regime.py --ticker SPY --years 10
python regime/regime_weighted_strategy.py  # Test regime-aware weighting
```

## Data Sources

- Yahoo Finance via yfinance (no API key required)
- Custom CSV with date/close columns

## Dependencies

numpy, pandas, yfinance, hmmlearn, scipy (optional: hmmlearn)