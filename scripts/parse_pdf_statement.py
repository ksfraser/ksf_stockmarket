#!/usr/bin/env python3
"""
parse_pdf_statement.py — Parse brokerage PDF statements and extract transactions.

Supports: CIBC Investor's Edge, Questrade, TD Direct Investing, BMO InvestorLine,
Scotiabank iTrade, RBC Direct Investing, and generic formats.

Usage: python3 parse_pdf_statement.py <pdf_path>

Output: JSON to stdout with structure:
{
  "format": "cibc|questrade|td|bmo|scotia|rbc|generic",
  "account": "account number or type",
  "pages": N,
  "transactions": [
    {
      "trade_date": "YYYY-MM-DD",
      "type": "BUY|SELL|DIVIDEND|...",
      "symbol": "RY.TO",
      "quantity": 100.0,
      "price": 150.25,
      "total": 15025.00,
      "commission": 9.95,
      "account_type": "RRSP|TFSA|MARGIN",
      "currency": "CAD",
      "description": "..."
    }
  ]
}
"""

import sys
import json
import re
from datetime import datetime


def extract_text(pdf_path: str) -> tuple[str, int]:
    """Extract text from PDF using pymupdf."""
    import fitz
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    pages = len(doc)
    doc.close()
    return text, pages


def detect_format(text: str) -> str:
    """Detect brokerage format from PDF text."""
    text_lower = text.lower()

    if "cibc" in text_lower and "investor's edge" in text_lower:
        return "cibc"
    if "questrade" in text_lower:
        return "questrade"
    if "td direct investing" in text_lower or "td wealth" in text_lower:
        return "td"
    if "bmo investorline" in text_lower or "bmo.com/investorline" in text_lower:
        return "bmo"
    if "scotiabank" in text_lower and "itrade" in text_lower:
        return "scotia"
    if "rbc direct investing" in text_lower:
        return "rbc"

    # Generic — has transaction-like patterns
    if re.search(r'(?:BUY|SELL|TRADE|PURCHASE)\s+\d+', text):
        return "generic"

    return "unknown"


def parse_cibc(text: str) -> list[dict]:
    """Parse CIBC Investor's Edge statements."""
    transactions = []

    # CIBC Activity/Transaction table patterns
    # Date, Description, Debit, Credit, Balance
    # Or: Date, Activity, Quantity, Description, Price, Amount

    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
        r'(\w{3}\s+\d{1,2},?\s+\d{4})\s+(.+?)\s+\$?([\d,]+\.\d{2})',
    ]

    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            date_str = match.group(1)
            desc = match.group(2).strip()
            amount = match.group(3).replace(',', '')

            txn = {
                'trade_date': parse_date(date_str),
                'type': 'BUY' if 'buy' in desc.lower() or 'purchase' in desc.lower() else
                       'SELL' if 'sell' in desc.lower() else 'OTHER',
                'symbol': extract_symbol(desc),
                'quantity': 0,
                'price': float(amount) if amount else 0,
                'total': float(amount) if amount else 0,
                'commission': 0,
                'account_type': extract_account_type(desc),
                'currency': 'CAD' if 'CAD' in text[:5000] else 'USD',
                'description': desc[:200],
            }
            if txn['trade_date'] and txn['symbol']:
                transactions.append(txn)

    return transactions


def parse_questrade(text: str) -> list[dict]:
    """Parse Questrade statements."""
    transactions = []

    # Questrade: Trade Date, Symbol, Quantity, Price, Commission, Net Amount, Type
    pattern = r'(\d{4}-\d{2}-\d{2})\s+([A-Z0-9.]+)\s+(Buy|Sell)\s+([\d,]+)\s+\$?([\d.]+)\s+\$?([\d.]+)\s+\$?([\d.]+)'

    for match in re.finditer(pattern, text):
        qty = float(match.group(4).replace(',', ''))
        price = float(match.group(5))
        commission = float(match.group(6))
        total = float(match.group(7))

        txn = {
            'trade_date': match.group(1),
            'symbol': match.group(2),
            'type': match.group(3).upper(),
            'quantity': qty,
            'price': price,
            'commission': commission,
            'total': total,
            'account_type': extract_account_type(text),
            'currency': 'CAD',
            'description': f"{match.group(3)} {qty} {match.group(2)} @ ${price}",
        }
        transactions.append(txn)

    return transactions


def parse_generic(text: str) -> list[dict]:
    """Generic parser — tries to find transaction-like patterns."""
    transactions = []

    # Look for lines with: Date + Symbol + BUY/SELL + Amount
    lines = text.split('\n')
    for line in lines:
        # Match: 2024-01-15  BUY  100 RY.TO  $150.25  $15,025.00
        m = re.search(
            r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\w{3}\s+\d{1,2},?\s+\d{4})\s+'
            r'(BUY|SELL|PURCHASE|SALE)\s+'
            r'([\d,]+)\s+'
            r'([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\s+'
            r'\$?([\d,.]+)',
            line, re.IGNORECASE
        )
        if m:
            txn = {
                'trade_date': parse_date(m.group(1)),
                'type': 'BUY' if m.group(2).upper() in ('BUY', 'PURCHASE') else 'SELL',
                'quantity': float(m.group(3).replace(',', '')),
                'symbol': m.group(4).upper(),
                'price': float(m.group(5).replace(',', '').replace('$', '')),
                'total': 0,
                'commission': 0,
                'account_type': 'UNKNOWN',
                'currency': 'CAD',
                'description': line.strip()[:200],
            }
            if txn['trade_date'] and txn['symbol']:
                transactions.append(txn)

    return transactions


def parse_date(date_str: str) -> str:
    """Parse various date formats to YYYY-MM-DD."""
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%b %d, %Y', '%B %d, %Y',
               '%b %d %Y', '%Y/%m/%d', '%d-%b-%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str


def extract_symbol(text: str) -> str:
    """Extract stock symbol from text."""
    m = re.search(r'\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b', text)
    return m.group(1) if m else ''


def extract_account_type(text: str) -> str:
    """Detect account type from statement text."""
    text_upper = text.upper()
    if 'RRSP' in text_upper or 'R.R.S.P.' in text_upper:
        return 'RRSP'
    if 'TFSA' in text_upper or 'T.F.S.A.' in text_upper:
        return 'TFSA'
    if 'MARGIN' in text_upper:
        return 'MARGIN'
    if 'RESP' in text_upper:
        return 'RESP'
    if 'JOINT' in text_upper:
        return 'JOINT'
    return 'UNKNOWN'


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: parse_pdf_statement.py <pdf_path>"}))
        sys.exit(1)

    pdf_path = sys.argv[1]

    try:
        text, pages = extract_text(pdf_path)
    except Exception as e:
        print(json.dumps({"error": f"Failed to extract text: {e}"}))
        sys.exit(1)

    fmt = detect_format(text)
    account = extract_account_type(text)

    # Dispatch to appropriate parser
    parsers = {
        'cibc': parse_cibc,
        'questrade': parse_questrade,
        'generic': parse_generic,
    }

    parser = parsers.get(fmt, parse_generic)
    transactions = parser(text)

    result = {
        'format': fmt,
        'account': account,
        'pages': pages,
        'transactions': transactions,
    }

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
