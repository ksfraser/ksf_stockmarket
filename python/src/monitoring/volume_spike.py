#!/usr/bin/env python3
"""
Volume Spike Monitor — Modular Version
======================================
Uses shared modules from ksf_stockmarket/src/

Checks intraday volume for all symbols in the watchlist_symbols table.
Only outputs alerts when volume exceeds threshold (2× average).

Usage:
  python3 volume_spike.py                    # Check all monitored symbols
  python3 volume_spike.py --ticker RY.TO   # Check single ticker
  python3 volume_spike.py --json           # Output JSON for piping
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yfinance as yf
from database import get_connection, get_monitored_symbols, log_monitoring_run
from symbol_resolver import resolve_for_yfinance


def check_volume_spike(symbol: str, threshold: float = 2.0) -> Optional[Dict]:
    """Check if a symbol has a volume spike today."""
    resolved = resolve_for_yfinance(symbol)
    
    try:
        stock = yf.Ticker(resolved)
        hist = stock.history(period='5d', interval='1d')
        if hist.empty or len(hist) < 2:
            return None
        
        # Remove timezone for indexing
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        
        today_vol = hist['Volume'].iloc[-1]
        if today_vol < 10000:  # Min volume to avoid noise
            return None
        
        avg_vol = hist['Volume'].iloc[-5:-1].mean() if len(hist) >= 5 else hist['Volume'].iloc[:-1].mean()
        if avg_vol == 0:
            return None
        
        vol_ratio = today_vol / avg_vol
        
        price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) >= 2 else price
        price_change = ((price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
        
        return {
            'ticker': symbol,
            'resolved': resolved,
            'current_price': round(price, 2),
            'price_change_pct': round(price_change, 2),
            'today_volume': int(today_vol),
            'avg_volume': int(avg_vol),
            'volume_ratio': round(vol_ratio, 2),
            'threshold': threshold,
            'alert': vol_ratio >= threshold,
        }
    except Exception as e:
        return {
            'ticker': symbol,
            'error': str(e),
            'alert': False,
        }


def run_volume_check(symbols: Optional[List[str]] = None, output_json: bool = False,
                     threshold: Optional[float] = None) -> int:
    """Run volume spike check. Returns exit code (0=no alert, 1=alert, 2=error)."""
    
    configs = get_monitored_symbols() if symbols is None else [{'symbol': s} for s in symbols]
    
    if not configs:
        print("⚠️  No monitored symbols found in watchlist_symbols table.")
        return 2
    
    run_id = log_monitoring_run('volume_spike', 'running', symbol_count=len(configs))
    
    results = []
    spikes = []
    
    for config in configs:
        symbol = config['symbol']
        threshold_val = threshold or float(config.get('volume_spike_threshold', 2.0))
        result = check_volume_spike(symbol, threshold=threshold_val)
        if result:
            results.append(result)
            if result.get('alert'):
                spikes.append(result)
    
    # Log completion
    log_monitoring_run(run_id, 'success' if not spikes else 'alert', 
                       alert_count=len(spikes), details={'spikes': spikes})
    
    if output_json:
        print(json.dumps({
            'timestamp': str(datetime.now()),
            'n_checked': len(configs),
            'n_spikes': len(spikes),
            'spikes': spikes,
            'all_results': results,
        }, indent=2, default=str))
        return 1 if spikes else 0
    
    if spikes:
        print(f"🔴 VOLUME SPIKE ALERT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"   {len(spikes)} of {len(configs)} symbols exceeded threshold:")
        print()
        for s in spikes:
            direction = "📈" if s['price_change_pct'] > 0 else "📉"
            print(f"   {direction} {s['ticker']:8s}  Vol: {s['today_volume']:>12,}  "
                  f"(avg: {s['avg_volume']:>10,})  {s['volume_ratio']:.1f}×  "
                  f"Price: ${s['current_price']:.2f} ({s['price_change_pct']:+.1f}%)")
        print()
        return 1
    else:
        max_ratio = max((r.get('volume_ratio', 0) for r in results if 'volume_ratio' in r), default=0)
        print(f"✅ No volume spikes — {datetime.now().strftime('%H:%M')}  "
              f"({len(configs)} checked, max ratio: {max_ratio:.1f}×)")
        return 0


def main():
    parser = argparse.ArgumentParser(description='Volume Spike Monitor')
    parser.add_argument('--ticker', type=str, help='Check single ticker (overrides DB)')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--threshold', type=float, default=None,
                        help='Override spike threshold multiplier')
    args = parser.parse_args()
    
    symbols = [args.ticker] if args.ticker else None
    exit_code = run_volume_check(symbols, output_json=args.json, threshold=args.threshold)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()