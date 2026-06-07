#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Symbol resolution module for ksf_stockmarket.
Centralized logic for resolving tickers to yfinance-compatible format.
"""

import re
import os
from typing import Optional

# Try to import database for exchange_mapping lookup
try:
    from database import get_connection
    _db_available = True
except ImportError:
    _db_available = False


def resolve_for_yfinance(symbol: str, use_db_lookup: bool = True) -> str:
    """Resolve a ticker symbol for yfinance compatibility.
    
    Uses exchange_mapping table for proper ticker resolution.
    
    Args:
        symbol: The symbol as stored in the database
        use_db_lookup: Whether to check exchange_mapping table (default True)
        
    Returns:
        yfinance-compatible symbol string
    """
    if not symbol:
        return symbol
    
    # Check exchange_mapping table first
    if use_db_lookup and _db_available:
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT yahoo_ticker FROM exchange_mapping 
                    WHERE symbol = %s AND is_primary = 1 AND is_active = 1
                """, (symbol,))
                row = cur.fetchone()
                if row and row.get('yahoo_ticker'):
                    return row['yahoo_ticker']
        except Exception:
            pass
    
    # Legacy conversions
    if symbol.endswith('.UN') and '.TO' not in symbol:
        return symbol.replace('.UN', '-UN.TO')
    
    # TSX symbols already have .TO suffix - leave as-is
    if '.TO' in symbol:
        return symbol
    
    # US symbols - no suffix needed
    if '.' in symbol and '.TO' not in symbol and '-UN.TO' not in symbol:
        return symbol
    
    return symbol


def detect_ticker_type(symbol: str) -> str:
    """
    Detect the type of ticker symbol.
    
    Returns: 'tsx', 'tsx_venture', 'us', 'etf_ca', 'etf_us', 'unknown'
    """
    symbol_upper = symbol.upper()
    
    # TSX primary (e.g., RY.TO, CM)
    if symbol.endswith('.TO') or (not '.' in symbol and len(symbol) <= 6):
        # Check if in known TSX patterns
        if symbol.isupper() or ('.' not in symbol and '-' not in symbol):
            return 'tsx'
    
    # TSX Venture (e.g., .V)
    if '.V' in symbol:
        return 'tsx_venture'
    
    # Canadian ETFs
    ca_etf_patterns = ['XIC', 'XSP', 'XEF', 'XUU', 'XBB', 'XSB', 'CPD', 'XEG', 
                      'XIT', 'XFN', 'XMA', 'XUT', 'XRE', 'ZCN', 'VCN', 'VCE',
                      'VFV', 'VEA', 'VXC', 'VAB', 'VBU', 'VCB', 'VEE', 'VEF']
    if symbol.upper() in ca_etf_patterns:
        return 'etf_ca'
    
    # US ETFs
    us_etf_patterns = ['SPY', 'VOO', 'IVV', 'VTI', 'QQQ', 'VEA', 'VWO', 'AGG',
                      'BND', 'GLD', 'SLV', 'USMV', 'MTUM', 'VLUE', 'QUAL', 'SIZE']
    if symbol.upper() in us_etf_patterns:
        return 'etf_us'
    
    # US stocks (typically 1-4 letters)
    if symbol.isupper() and len(symbol) <= 5 and '.' not in symbol:
        return 'us'
    
    return 'unknown'


if __name__ == '__main__':
    # Test cases
    tests = [
        ('RY.TO', 'RY.TO'),
        ('KEG.UN', 'KEG-UN.TO'),
        ('RY', 'RY.TO'),  # Would need DB lookup
        ('SPY', 'SPY'),
        ('XIC', 'XIC'),
    ]
    
    for input_sym, expected in tests:
        result = resolve_for_yfinance(input_sym)
        status = '✓' if result == expected else '✗'
        print(f"{status} {input_sym} → {result} (expected: {expected})")