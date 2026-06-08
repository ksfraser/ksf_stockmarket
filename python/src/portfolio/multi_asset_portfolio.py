#!/usr/bin/env python3
"""
Multi-Asset Portfolio Constructor
==================================
Extends ksf_stockmarket to handle Stocks + Forex + Futures + Stablecoins.

This is a stub - not integrated into main pipeline yet.
"""

from typing import Dict, List
import pandas as pd
import numpy as np


def build_multi_asset_portfolio(
    stock_signals: Dict[str, float],
    forex_signals: Dict[str, float] = None,
    futures_signals: Dict[str, float] = None,
    stablecoin_positions: List[str] = None,
    max_stock_pct: float = 0.60,
    max_forex_pct: float = 0.20,
    max_futures_pct: float = 0.15,
    max_crypto_pct: float = 0.05
) -> Dict[str, float]:
    """
    Construct portfolio across asset classes with heat limits.
    
    Args:
        stock_signals: {symbol: score} for equities
        forex_signals: {pair: score} for FX
        futures_signals: {contract: score} for futures
        stablecoin_positions: list of stablecoin positions (cash equivalent)
        
    Returns:
        {symbol: target_allocation} with cross-asset limits
    """
    # Normalize each asset class
    sectors = {
        'stocks': stock_signals or {},
        'forex': forex_signals or {},
        'futures': futures_signals or {},
        'stablecoins': set(stablecoin_positions or [])
    }
    
    # Allocate within each class
    allocations = {}
    
    # Stocks: max 60% of portfolio
    stock_total = sum(max(0, s) for s in sectors['stocks'].values())
    if stock_total > 0:
        stock_alloc = min(max_stock_pct, stock_total)
        for sym, score in sectors['stocks'].items():
            if score > 0:
                allocations[sym] = stock_alloc * (score / stock_total)
    
    # Forex: max 20%
    forex_total = sum(abs(s) for s in sectors['forex'].values())
    if forex_total > 0:
        forex_alloc = min(max_forex_pct, forex_total)
        for sym, score in sectors['forex'].items():
            allocations[sym] = forex_alloc * (abs(score) / forex_total)
    
    # Futures: max 15%
    futures_total = sum(max(0, s) for s in sectors['futures'].values())
    if futures_total > 0:
        futures_alloc = min(max_futures_pct, futures_total)
        for sym, score in sectors['futures'].items():
            if score > 0:
                allocations[sym] = futures_alloc * (score / futures_total)
    
    return allocations


if __name__ == '__main__':
    print("Multi-Asset Portfolio Stub Test")
    print("=" * 50)
    
    # Test allocation
    stocks = {'AAPL': 80, 'MSFT': 60, 'SPY': 100}
    forex = {'EUR.CAD': 50, 'USD.CAD': 30}
    futures = {'ES': 70, 'NQ': 40}
    
    alloc = build_multi_asset_portfolio(
        stock_signals=stocks,
        forex_signals=forex,
        futures_signals=futures
    )
    
    print(f"Total allocated: {sum(alloc.values())*100:.1f}%")
    for sym, pct in sorted(alloc.items()):
        print(f"  {sym}: {pct*100:.2f}%")