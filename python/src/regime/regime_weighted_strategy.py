#!/usr/bin/env python3
"""
Regime-Weighted Signal Strategy
================================
Integrates Markov regime detection with trading_pipeline_v3.

Approach: Weight strategies based on current market regime:
- Bull market: Momentum strategies (CANSLIM, SMA cross, Breakouts)
- Bear market: Mean reversion (BB, RSI, Z-score)
- Sideways: Range-bound (Donchian, Turtle, Bollinger)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from regime.markov_regime import (
    label_regimes, build_transition_matrix, stationary_distribution
)


def get_regime_weights(current_regime: str) -> dict:
    """Return strategy weights based on market regime.
    
    Higher weight = more likely to generate valid signals.
    """
    weights = {
        # Momentum strategies
        'sma_10_50': 1.0,
        'sma_20_50': 1.0,
        'sma_50_200': 1.0,
        'turtle_20': 1.0,
        '4week': 1.0,
        
        # Mean reversion
        'bollinger_mr': 1.0,
        'macd_trend': 1.0,
        'stochastic': 1.0,
        'rsi_momentum': 1.0,
        'zscore_rev': 1.0,
        
        # Breakout
        'donchian_20': 1.0,
        'sneaky_pivot': 1.0,
    }
    
    if current_regime == 'Bull':
        # Trend-following gets higher weight
        weights.update({
            'sma_10_50': 1.5,
            'sma_20_50': 1.5,
            'sma_50_200': 1.2,
            'turtle_20': 1.3,
            '4week': 1.3,
            'sneaky_pivot': 0.8,  # Fade less in strong trends
        })
    elif current_regime == 'Bear':
        # Mean reversion gets higher weight
        weights.update({
            'bollinger_mr': 1.5,
            'rsi_momentum': 1.5,
            'zscore_rev': 1.3,
            'macd_trend': 1.2,
            'sma_50_200': 0.7,  # Death cross more relevant
        })
    elif current_regime == 'Sideways':
        # Range-bound strategies dominate
        weights.update({
            'bollinger_mr': 1.5,
            'donchian_20': 1.3,
            'sneaky_pivot': 1.4,  # Perfect for range trading
            'turtle_20': 1.2,
            'sma_10_50': 0.8,
        })
    
    return weights


def regime_aware_signal(df: pd.DataFrame, symbol: str = None) -> tuple:
    """
    Apply regime-based signal weighting.
    
    Returns: (signal array, strength array) weighted by regime
    Note: Requires SIGNAL_STRATEGIES to be passed in or imported separately.
    """
    # Import delayed to avoid circular dependency
    from trading_pipeline_v3 import SIGNAL_STRATEGIES, compute_all_indicators
    
    if len(df) < 252:
        # Not enough data for regime - use equal weights
        sig = np.zeros(len(df))
        strength = np.ones(len(df)) * 50
        return sig, strength
    
    try:
        df = compute_all_indicators(df)
    except Exception:
        pass
    
    # Get current regime
    closes = df['c'].values.astype(float)
    regimes = label_regimes(closes)
    current_regime = regimes[-1] if len(regimes) > 0 else 'Sideways'
    
    # Get base weights
    weights = get_regime_weights(current_regime)
    
    # Aggregate signals from all strategies
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    
    if 'SIGNAL_STRATEGIES' not in globals():
        return sig, strength
        
    for strat_name, strat_fn in SIGNAL_STRATEGIES.items():
        try:
            s, st = strat_fn(df)
            weight = weights.get(strat_name, 1.0)
            sig += s * weight
            strength += st * weight
        except Exception:
            continue
    
    # Normalize
    if len(sig) > 0:
        strength = np.clip(strength / len(SIGNAL_STRATEGIES), 0, 100)
        sig = np.clip(sig, -1, 1)
        sig = np.round(sig).astype(int)
    
    return sig, strength


if __name__ == '__main__':
    # Test regime detection on SPY
    print("Testing regime-aware strategy weighting...")
    
    from regime.markov_regime import fetch_ticker, analyze
    
    try:
        close = fetch_ticker('SPY', years=2)
        result = analyze(close)
        
        print(f"\nCurrent regime: {result['current_regime']}")
        print(f"Stationary distribution: {result['stationary_distribution']}")
        print(f"Transition matrix:\n{result['transition_matrix']}")
        print(f"\nWalk-forward Sharpe: {result['walk_forward']['sharpe']:.3f}")
        
        weights = get_regime_weights(result['current_regime'])
        print(f"\nStrategy weights for {result['current_regime']} regime:")
        for k, v in sorted(weights.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v:.1f}")
    except Exception as e:
        print(f"Error: {e}")