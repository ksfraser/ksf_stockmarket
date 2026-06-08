#!/usr/bin/env python3
"""
AI Rebalancing Strategy (adapted from DeFi Yield Optimizer)
===========================================================

Core insight from Lewis Jackson's DeFi agent: Only rebalance when the math
justifies transaction costs. For stablecoins: only rebalance when fee recovery
> gas costs. For stocks: only rebalance when allocation drift > implicit cost.

This strategy wraps portfolio construction (Layer 3) with cost-aware logic.
"""

import numpy as np
import pandas as pd


def ai_rebalance_score(
    current_positions: dict,
    target_positions: dict,
    current_prices: dict,
    portfolio_value: float,
    commission: float = 9.95
) -> dict:
    """
    Score whether rebalance is worth doing.
    
    Returns: {'should_rebalance': bool, 'cost_impact': float, 'drift_score': float}
    """
    drift_score = 0.0
    total_drift_value = 0.0
    
    for symbol, target_shares in target_positions.items():
        if symbol not in current_positions:
            # New position - full cost
            total_drift_value += abs(target_shares * current_prices.get(symbol, 0))
        else:
            current = current_positions[symbol]
            target = target_shares
            price = current_prices.get(symbol, 0)
            
            if price > 0:
                drift_pct = abs(current - target) / target if target > 0 else 0
                drift_score += drift_pct * (current * price) / portfolio_value
                total_drift_value += abs(current - target) * price
    
    # Cost impact: how much of drift is consumed by commissions
    n_trades = sum(1 for s in target_positions if s not in current_positions or 
                   current_positions.get(s, 0) != target_positions[s])
    cost_impact = n_trades * commission / portfolio_value
    
    # AI decision: rebalance only if drift impact > 2x transaction cost
    # This accounts for bid-ask spread and timing risk
    should_rebalance = drift_score > (cost_impact * 2) and drift_score > 0.02
    
    return {
        'should_rebalance': should_rebalance,
        'cost_impact': round(cost_impact, 4),
        'drift_score': round(drift_score, 4),
        'total_drift_value': round(total_drift_value, 2)
    }


def apply_ai_rebalance_layer(df: pd.DataFrame, cash: float, positions: dict, 
                            target_shares: dict, prices: dict, max_pct: float = 0.10,
                            commission: float = 9.95) -> tuple:
    """
    Apply AI-aware rebalancing to existing backtest logic.
    
    This replaces the standard Layer 3 rebalance with cost-aware version.
    
    Returns: (updated_cash, updated_positions, trades_made)
    """
    portfolio_value = cash + sum(positions.get(s, 0) * prices.get(s, 0) for s in positions)
    
    decision = ai_rebalance_score(positions, target_shares, prices, portfolio_value, commission)
    
    if not decision['should_rebalance']:
        return cash, positions.copy(), []  # No trades
    
    # Proceed with normal rebalance logic
    trades = []
    new_positions = positions.copy()
    
    for symbol, target in target_shares.items():
        price = prices.get(symbol, 0)
        if price <= 0:
            continue
            
        current = new_positions.get(symbol, 0)
        
        if target > current and cash > price:
            # Need to buy
            shares_to_buy = min(target - current, int(cash / price))
            if shares_to_buy > 0 and shares_to_buy * price + commission <= cash:
                cash -= shares_to_buy * price + commission
                new_positions[symbol] = target
                trades.append({'symbol': symbol, 'action': 'BUY', 'shares': shares_to_buy})
                
        elif target < current:
            # Need to sell
            shares_to_sell = current - target
            if shares_to_sell > 0:
                cash += shares_to_sell * price - commission
                new_positions[symbol] = target
                trades.append({'symbol': symbol, 'action': 'SELL', 'shares': shares_to_sell})
    
    return cash, new_positions, trades


if __name__ == '__main__':
    # Test the AI rebalance logic
    print("AI Rebalancing Strategy Test")
    print("=" * 50)
    
    # Scenario: portfolio has drifted from targets
    current = {'AAPL': 100, 'MSFT': 50, 'GOOGL': 0}
    targets = {'AAPL': 150, 'MSFT': 25, 'GOOGL': 75}
    prices = {'AAPL': 175.0, 'MSFT': 400.0, 'GOOGL': 140.0}
    pv = 100000
    
    result = ai_rebalance_score(current, targets, prices, pv)
    print(f"Current portfolio value: ${pv:,.0f}")
    print(f"Drift score: {result['drift_score']*100:.2f}%")
    print(f"Cost impact: {result['cost_impact']*100:.2f}%")
    print(f"Should rebalance: {result['should_rebalance']}")