#!/usr/bin/env python3
"""
TradingView MCP Client for ksf_stockmarket
Uses tradingview-mcp-server to fetch screener data and TA summaries.
"""

import subprocess
import json
import sys
from typing import Optional

def run_mcp_tool(tool: str, params: dict) -> dict:
    """Run a TradingView MCP tool and return parsed JSON response."""
    cmd = [
        'npx', '-y', 'tradingview-mcp-server',
        tool.replace('_', '-'),
        *sum([[f'--{k}', json.dumps(v) if isinstance(v, (dict, list)) else str(v)] for k, v in params.items()], [])
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        env={**subprocess.os.environ, 'CACHE_TTL_SECONDS': '300', 'RATE_LIMIT_RPM': '10'}
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"MCP error: {result.stderr}")
    
    # MCP returns JSON on stdout after startup banner
    for line in result.stdout.strip().split('\n'):
        if line.startswith('{'):
            return json.loads(line)
    
    return {}

def search_symbols(query: str, asset_type: str = 'stock', limit: int = 10) -> list:
    """Search for TradingView symbols."""
    return run_mcp_tool('search_symbols', {
        'query': query,
        'asset_type': asset_type,
        'limit': limit
    }).get('symbols', [])

def screen_stocks(filters: list, columns: list = None, limit: int = 20) -> list:
    """Screen stocks with filters."""
    if columns is None:
        columns = ['name', 'ticker', 'close', 'change', 'Perf.Y', 'RSI', 'return_on_equity', 'price_to_earnings']
    
    return run_mcp_tool('screen_stocks', {
        'filters': filters,
        'columns': columns,
        'limit': limit
    }).get('data', [])

def get_ta_summary(symbols: list, timeframes: list = None) -> dict:
    """Get technical analysis summary for symbols."""
    if timeframes is None:
        timeframes = ['60', '240', '1D', '1W']
    
    return run_mcp_tool('get_ta_summary', {
        'symbols': symbols,
        'timeframes': timeframes
    })

def get_preset(preset_name: str) -> dict:
    """Get a preset screening strategy."""
    return run_mcp_tool('get_preset', {'preset_name': preset_name})

def list_presets() -> list:
    """List available preset strategies."""
    return run_mcp_tool('list_presets', {}).get('presets', [])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: tv_mcp.py <command> [args...]")
        print("Commands: search, screen, ta, presets, preset")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'search' and len(sys.argv) > 2:
        results = search_symbols(sys.argv[2])
        print(json.dumps(results, indent=2))
    elif cmd == 'presets':
        presets = list_presets()
        for p in presets:
            print(f"- {p['key']}: {p['name']}")
    elif cmd == 'preset' and len(sys.argv) > 2:
        preset = get_preset(sys.argv[2])
        print(json.dumps(preset, indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)