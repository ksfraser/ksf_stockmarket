#!/usr/bin/env python3
"""
Trade Journal - Log and analyze trades
Adapted from Jackson's skill but for ksf_stockmarket transactions.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional


def log_trade_to_journal(
    symbol: str,
    trade_type: str,
    entry_price: float,
    exit_price: float,
    quantity: float,
    stop_loss: float = 0,
    take_profit: float = 0,
    entry_reason: str = '',
    exit_reason: str = '',
    emotional_state: str = '',
    fees: float = 0,
    strategy: str = ''
) -> Dict:
    """
    Log a trade with full reasoning.
    
    Returns structured journal entry.
    """
    pnl = (exit_price - entry_price) * quantity
    net_pnl = pnl - fees
    rr_ratio = abs(exit_price - entry_price) / abs(entry_price - stop_loss) if stop_loss else 0
    
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'symbol': symbol,
        'direction': trade_type,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'quantity': quantity,
        'gross_pnl': round(pnl, 2),
        'net_pnl': round(net_pnl, 2),
        'fees': fees,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'rr_ratio': round(rr_ratio, 2),
        'entry_reason': entry_reason,
        'exit_reason': exit_reason,
        'emotional_state': emotional_state,
        'strategy': strategy,
        'followed_rules': None,  # User must confirm
        'lesson': None  # User must provide
    }


def analyze_patterns(trade_log: List[Dict]) -> Dict:
    """
    Analyze trade log for patterns.
    """
    if not trade_log:
        return {'error': 'No trades to analyze'}
    
    df = pd.DataFrame(trade_log)
    
    # Basic stats
    total_pnl = df['net_pnl'].sum()
    win_rate = (df['net_pnl'] > 0).sum() / len(df) * 100
    avg_win = df[df['net_pnl'] > 0]['net_pnl'].mean() if (df['net_pnl'] > 0).any() else 0
    avg_loss = df[df['net_pnl'] <= 0]['net_pnl'].mean() if (df['net_pnl'] <= 0).any() else 0
    
    # Emotional state correlation
    emotional = df.groupby('emotional_state')['net_pnl'].agg(['mean', 'count'])
    
    return {
        'total_pnl': round(total_pnl, 2),
        'win_rate': round(win_rate, 1),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'expectancy': round((win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss), 2),
        'emotional_correlation': emotional.to_dict()
    }


if __name__ == '__main__':
    print("Trade Journal Test")
    print("=" * 50)
    
    trade = log_trade_to_journal(
        symbol='AAPL',
        trade_type='BUY',
        entry_price=175.0,
        exit_price=180.0,
        quantity=100,
        stop_loss=170.0,
        take_profit=190.0,
        entry_reason='RSI below 30 + price above 200EMA',
        exit_reason='RSI crossed above 70',
        emotional_state='calm',
        fees=9.95,
        strategy='rsi_momentum'
    )
    
    print(f"Journal Entry: {trade['symbol']} {trade['direction']} @ ${trade['entry_price']}")
    print(f"P&L: ${trade['net_pnl']}")
    print(f"R:R: {trade['rr_ratio']}:1")