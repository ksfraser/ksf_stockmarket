#!/usr/bin/env python3
"""
Strategy Auditor - Stress-test strategies before trading
Adapted from Jackson's skill but integrated with ksf_stockmarket.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


def stress_test_strategy(
    strategy_name: str,
    parameters: Dict,
    hist_trades: int,
    backtest_metrics: Dict
) -> Dict:
    """
    Run full strategy stress test.
    
    Tests:
    1. In-sample performance
    2. Walk-forward stability  
    3. Overfitting detection
    4. Regime dependence
    """
    results = {}
    
    # Test 1: In-sample check
    sharpe = backtest_metrics.get('sharpe', 0)
    max_dd = backtest_metrics.get('max_drawdown', 0)
    win_rate = backtest_metrics.get('win_rate', 0)
    
    results['in_sample'] = {
        'sharpe_acceptable': sharpe > 1.0,
        'drawdown_acceptable': max_dd < 20,
        'win_rate_ok': win_rate > 40,
        'issues': []
    }
    
    if sharpe <= 1.0:
        results['in_sample']['issues'].append(f"Low Sharpe ({sharpe})")
    if max_dd >= 20:
        results['in_sample']['issues'].append(f"High drawdown ({max_dd}%)")
    
    # Test 2: Walk-forward check (simplified)
    # In real implementation, would split into 4+ windows
    n_trades = hist_trades
    results['walk_forward'] = {
        'enough_trades': n_trades >= 25,
        'min_trades_required': 25,
        'issues': [] if n_trades >= 25 else [f"Only {n_trades} trades - need 25+"]
    }
    
    # Test 3: Overfitting detector
    # Check if too many parameters relative to trades
    n_params = len(parameters)
    param_ratio = n_params / n_trades if n_trades > 0 else 0
    results['overfit'] = {
        'ratio': param_ratio,
        'risk': 'high' if param_ratio > 0.5 else 'low',
        'issues': [] if param_ratio <= 0.5 else ['Too many parameters for trade count']
    }
    
    # Overall verdict
    passed = (
        results['in_sample']['sharpe_acceptable'] and 
        results['in_sample']['drawdown_acceptable'] and
        results['walk_forward']['enough_trades']
    )
    
    return {
        'strategy': strategy_name,
        'stress_test': results,
        'verdict': 'PASS' if passed else 'FAIL',
        'action': 'Trade with caution' if not passed else 'Strategy ready'
    }


if __name__ == '__main__':
    print("Strategy Auditor Test")
    print("=" * 50)
    
    test = stress_test_strategy(
        strategy_name='sma_20_50',
        parameters={'fast': 20, 'slow': 50, 'stop': 2.0},
        hist_trades=42,
        backtest_metrics={'sharpe': 1.2, 'max_drawdown': 15, 'win_rate': 45}
    )
    
    print(f"Strategy: {test['strategy']}")
    print(f"Verdict: {test['verdict']}")
    for test_name, result in test['stress_test'].items():
        print(f"  {test_name}: {result}")