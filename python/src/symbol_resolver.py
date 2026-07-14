#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Symbol resolution module for ksf_stockmarket.
Centralized logic for resolving tickers to yfinance-compatible format.
"""

import re
from typing import Optional, Tuple, Dict, Any

# Try to import database for exchange_mapping lookup
try:
    from database import get_connection
    _db_available = True
except ImportError:
    _db_available = False

# Short bare symbols that resolve correctly without .TO on yfinance.
# All other short, dot-free symbols default to .TO for TSX disambiguation.
US_SHORT_NO_SUFFIX = {
    'CEF', 'GLD', 'RGLD', 'SLV', 'USO', 'UNG', 'TLT', 'EEM', 'EFA', 'VWO', 'VEA',
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'IVV', 'AGG', 'BND', 'LQD', 'HYG',
    'JNK', 'XLF', 'XLE', 'XLI', 'XLV', 'XLP', 'XLY', 'XLB', 'XLRE', 'XLK', 'XLU',
    'XLC', 'XBI', 'IBB', 'SMH', 'SOXX', 'KRE', 'KBE', 'XOP', 'OIH', 'ITB', 'XHB',
    'XRT', 'XME', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'BRK-B',
    'JNJ', 'JPM', 'V', 'MA', 'PG', 'UNH', 'HD', 'KO', 'PEP', 'ABBV', 'MRK', 'XOM',
    'CVX', 'LLY', 'TMO', 'ABT', 'ORCL', 'COST', 'AVGO', 'QCOM', 'CSCO', 'ACN',
    'MCD', 'NKE', 'DHR', 'TXN', 'PM', 'LIN', 'UNP', 'LOW', 'BA', 'IBM', 'AMGN',
    'CAT', 'GS', 'BLK',
}


def resolve_for_yfinance(symbol: str, use_db_lookup: bool = True) -> str:
    """Resolve a ticker symbol for yfinance compatibility.

    Uses exchange_mapping table, symbol_master exchange hints, and as a last
    resort a dual yfinance fetch (symbol vs symbol.TO) to pick the richer result.
    Also converts TSX dot-notation to hyphen (e.g., AGF.B.TO → AGF-B.TO).

    Args:
        symbol: The symbol as stored in the database
        use_db_lookup: Whether to check exchange_mapping/symbol_master tables

    Returns:
        yfinance-compatible symbol string
    """
    if not symbol:
        return symbol

    # Normalize TSX formats first
    symbol = _convert_tsx_format(symbol)

    # Already has a known suffix → return as-is
    if re.search(r'\.(TO|V|X|O)$', symbol) or '-' in symbol:
        return symbol

    # Short symbols that are known US-only → no suffix
    if symbol in US_SHORT_NO_SUFFIX:
        return symbol

    # Check exchange_mapping table first (explicit yahoo_ticker)
    if use_db_lookup and _db_available:
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT yahoo_ticker FROM exchange_mapping
                    WHERE symbol = %s AND is_primary = 1 AND is_active = 1
                    LIMIT 1
                """, (symbol,))
                row = cur.fetchone()
                if row and row.get('yahoo_ticker'):
                    return str(row['yahoo_ticker']).upper()
        except Exception:
            pass

    # symbol_master exchange hint: if TSX/TSXV, append .TO
    if _db_available:
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT exchange FROM symbol_master WHERE symbol = %s LIMIT 1",
                    (symbol,)
                )
                row = cur.fetchone()
                if row and row.get('exchange'):
                    ex = str(row['exchange']).upper()
                    if 'TSX' in ex or 'TSXV' in ex:
                        return symbol + '.TO'
        except Exception:
            pass

    # Unknown short symbol: dual-fetch with yfinance
    if _db_available and not any(c in symbol for c in ['.']):
        try:
            bare_info = _safe_info(symbol)
            ca_info = _safe_info(symbol + '.TO')
            if ca_info and (bare_info is None or len(ca_info) > len(bare_info)):
                return symbol + '.TO'
        except Exception:
            pass

    return symbol


def _safe_info(ticker: str) -> Dict[str, Any] | None:
    """Fetch yfinance ticker.info with exception safety."""
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        return dict(info)
    except Exception:
        return None


def _get_symbol_exchange(symbol: str) -> str | None:
    """Return exchange hint for a symbol (TSX/TSXV/NYSE/etc. or None)."""
    if not _db_available:
        return None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # 1. exchange_mapping
            cur.execute(
                "SELECT yahoo_ticker FROM exchange_mapping WHERE symbol = %s "
                "AND is_primary = 1 AND is_active = 1 LIMIT 1",
                (symbol,),
            )
            row = cur.fetchone()
            if row and row.get('yahoo_ticker'):
                return 'TSX'  # mapped entry means CA listing
            # 2. portfolio price_symbol ending in .TO
            cur.execute(
                "SELECT price_symbol FROM portfolio WHERE symbol = %s "
                "AND price_symbol LIKE %s LIMIT 1",
                (symbol, '%.TO'),
            )
            row = cur.fetchone()
            if row:
                return 'TSX'
            # 3. symbol_master exchange = TSX
            cur.execute(
                "SELECT exchange FROM symbol_master WHERE symbol = %s LIMIT 1",
                (symbol,),
            )
            row = cur.fetchone()
            if row and row.get('exchange'):
                ex = str(row['exchange']).upper()
                return 'TSX' if 'TSX' in ex or 'TSXV' in ex else ex
    except Exception:
        pass
    return None


def _convert_tsx_format(symbol: str) -> str:
    """Convert TSX dot-notation to yfinance-compatible hyphen/trailing .TO notation.

    AGF.B.TO -> AGF-B.TO
    AW.UN.TO  -> AW-UN.TO
    SRV.UN    -> SRV-UN.TO   (bare .UN without .TO gets .TO appended)
    """
    if '.B.TO' in symbol:
        return symbol.replace('.B.TO', '-B.TO')
    if '.UN.TO' in symbol:
        return symbol.replace('.UN.TO', '-UN.TO')
    if '.U.TO' in symbol:
        return symbol.replace('.U.TO', '-U.TO')
    if symbol.endswith('.UN'):
        return symbol[:-3] + '-UN.TO'
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