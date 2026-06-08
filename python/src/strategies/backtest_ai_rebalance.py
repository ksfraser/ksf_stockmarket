#!/usr/bin/env python3
"""
AI Rebalancing Backtest Wrapper
================================
Run the AI rebalancing strategy against existing backtest framework.

This adds cost-aware rebalancing to the existing Layer 3 portfolio construction.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import AI rebalance logic
from strategies.ai_rebalance import ai_rebalance_score, apply_ai_rebalance_layer


def run_ai_rebalance_backtest(
    symbol_list: list,
    start_date: str = '2020-01-01',
    end_date: str = '2024-12-31',
    initial_capital: float = 100000,
    commission: float = 9.95,
    rebalance_days: int = 30,
    target_allocations: dict = None  # e.g., {'AAPL': 0.15, 'MSFT': 0.15, ...}
):
    """
    Run backtest with AI-aware rebalancing.
    
    If target_allocations not provided, use equal weight.
    """
    # This would integrate with the main pipeline
    # For now, return the strategy configuration
    
    if target_allocations is None:
        target_allocations = {s: 1/len(symbol_list) for s in symbol_list}
    
    # Calculate expected drift threshold
    # AI rebalance triggers when allocation drift > 2x transaction cost
    # This effectively means we skip small rebalancing trades
    
    config = {
        'strategy': 'ai_rebalance',
        'symbol_list': symbol_list,
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital,
        'commission': commission,
        'rebalance_days': rebalance_days,
        'target_allocations': target_allocations,
        'ai_logic': {
            'drift_threshold': 0.02,  # 2% drift minimum
            'cost_multiplier': 2,      # Only rebalance if 2x cost justified
            'dollar_cost_avg_enabled': True
        }
    }
    
    return config


if __name__ == '__main__':
    # Test with available symbols
    symbols = ['CM', 'CNR', 'MTY', 'RY', 'SPY', 'XIC']
    
    config = run_ai_rebalance_backtest(
        symbol_list=symbols,
        start_date='2020-01-01',
        end_date='2024-12-31'
    )
    
    print("AI Rebalancing Strategy Configuration:")
    print(json.dumps(config, indent=2))
    print("\nKey Parameters:")
    print(f"  - Initial capital: ${config['initial_capital']:,.0f}")
    print(f"  - Commission per trade: ${config['commission']}")
    print(f"  - Rebalance interval: {config['rebalance_days']} days")
    print(f"  - Target allocations: {len(config['target_allocations'])} symbols")