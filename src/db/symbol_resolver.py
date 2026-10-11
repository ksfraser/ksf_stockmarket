#!/usr/bin/env python3
"""Symbol resolution module for ksf_stockmarket.

Minimal stub providing resolve_for_yfinance and decompose_ticker for legacy imports.
"""

import re
from typing import Optional, Tuple, Dict, Any

# Exchange suffixes that must stay dotted (do not convert '.' -> '-').
_PRESERVE_SUFFIX_RE = re.compile(
    r'\.(TO|V|X|O|UN\.TO|B\.TO|U\.TO|NE|L|PA|DE|HK|T|SS|SW|MI|AX|HE|SG|SI|AS|JP|CN|SA|MX|VI|BA|F)$',
    re.IGNORECASE,
)

def normalize_symbol(symbol: str) -> str:
    """Normalize a stored ticker to a yfinance/Stooq-resolvable form."""
    if not symbol:
        return symbol
    s = symbol.strip()
    if ':' in s:
        s = s.split(':', 1)[1]
    s = s.replace('/', '-')
    if '.' in s and not _PRESERVE_SUFFIX_RE.search(s):
        head, _, tail = s.rpartition('.')
        if len(tail) == 1 and tail.isalpha() and tail.isupper():
            s = head + '-' + tail
    return s

def decompose_ticker(symbol: str) -> Dict[str, str]:
    """Stub decompose_ticker for legacy imports."""
    return {"base_symbol": symbol, "exchange": "TO", "unit_class": ""}

def resolve_for_yfinance(symbol: str, use_db_lookup: bool = True) -> str:
    """Resolve symbol to yfinance-compatible format."""
    return normalize_symbol(symbol)

def is_synthetic(symbol: str) -> bool:
    return False

US_SHORT_NO_SUFFIX = {
    'CEF', 'GLD', 'RGLD', 'SLV', 'USO', 'UNG', 'TLT', 'EEM', 'EFA', 'VWO', 'VEA',
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'IVV', 'AGG', 'BND', 'LQD', 'HYG',
    'JNK', 'XLF', 'XLE', 'XLI', 'XLV', 'XLP', 'XLY', 'XLB', 'XLRE', 'XLK', 'XLU',
    'XLC', 'XBI', 'IBB', 'SMH', 'SOXX', 'KRE', 'KBE', 'XOP', 'OIH', 'ITB', 'XHB',
    'XRT', 'XME', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'BRK-B',
    'JNJ', 'JPM', 'V', 'MA', 'PG', 'UNH', 'HD', 'KO', 'PEP', 'ABBV', 'MRK', 'XOM',
}

def detect_ticker_type(symbol: str) -> str:
    return "equity"

if __name__ == '__main__':
    print("symbol_resolver stub loaded")
