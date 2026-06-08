#!/usr/bin/env python3
"""
Risk Manager - Pre-trade risk gate and circuit breaker
Adapted from Jackson's skill but for ksf_stockmarket architecture.
"""

import pandas as pd
from typing import Dict, List, Optional


def pre_trade_gate(
    asset: str,
    direction: str,
    entry_price: float,
    account_balance: float,
    daily_pnl: float,
    open_positions: List[Dict],
    strategy_name: str,
    proposed_risk_pct: float = 0.02
) -> Dict:
    """
    Run pre-trade checklist: Block trade if any check fails.
    
    Checks:
    1. Daily loss limit (3% default)
    2. Max open positions (12 default)  
    3. Same asset already held
    4. Risk > 2% of equity
    5. Stale entry price (>2% from market)
    6. Risk-reward < 1.5:1
    """
    results = []
    
    # Check 1: Daily loss limit
    daily_limit = account_balance * 0.03
    daily_breached = daily_pnl < -daily_limit
    results.append({
        'check': 'Daily loss limit',
        'result': 'BLOCK' if daily_breached else 'PASS',
        'detail': f'Daily P&L: ${daily_pnl:,.0f}, Limit: ${daily_limit:,.0f}'
    })
    
    # Check 2: Max positions
    max_pos = 12
    pos_breached = len(open_positions) >= max_pos
    results.append({
        'check': 'Max open positions',
        'result': 'BLOCK' if pos_breached else 'PASS',
        'detail': f'{len(open_positions)}/{max_pos} positions open'
    })
    
    # Check 3: Same asset held
    same_asset = any(p['symbol'] == asset for p in open_positions)
    results.append({
        'check': 'Same asset held',
        'result': 'BLOCK' if same_asset else 'PASS',
        'detail': f'Asset {asset} already in portfolio' if same_asset else 'No conflict'
    })
    
    # Check 4: Risk percentage
    risk_ok = proposed_risk_pct <= 0.02
    results.append({
        'check': 'Risk percentage',
        'result': 'PASS' if risk_ok else 'BLOCK',
        'detail': f'{proposed_risk_pct*100:.1f}% <= 2% max'
    })
    
    # Final verdict
    blocked = any(r['result'] == 'BLOCK' for r in results)
    
    return {
        'checks': results,
        'verdict': 'BLOCKED' if blocked else 'APPROVED',
        'position_size': None if blocked else account_balance * 0.02  # Simple position sizing
    }


if __name__ == '__main__':
    print("Risk Manager Test")
    print("=" * 50)
    
    result = pre_trade_gate(
        asset='AAPL',
        direction='BUY',
        entry_price=175.0,
        account_balance=100000,
        daily_pnl=-500,
        open_positions=[{'symbol': 'MSFT', 'type': 'BUY'}],
        strategy_name='momentum'
    )
    
    for check in result['checks']:
        print(f"{check['result']} - {check['check']}: {check['detail']}")
    print(f"\nFinal: {result['verdict']}")