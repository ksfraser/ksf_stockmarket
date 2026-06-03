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
    # Normalize apostrophes and special chars
    text_clean = text_lower.replace('\u2019', "'").replace('\u2018', "'").replace('\u2013', '-')

    if "cibc" in text_clean:
        return "cibc"
    if "questrade" in text_clean:
        return "questrade"
    if "td direct investing" in text_clean or "td wealth" in text_clean:
        return "td"
    if "bmo" in text_clean and ("investorline" in text_clean or "investor line" in text_clean):
        return "bmo"
    if "scotiabank" in text_clean and "itrade" in text_clean:
        return "scotia"
    if "rbc" in text_clean and "direct investing" in text_clean:
        return "rbc"

    # Generic — has transaction-like patterns
    if re.search(r'(?:BUY|SELL|TRADE|PURCHASE)\s+\d+', text):
        return "generic"

    return "unknown"


def parse_cibc(text: str) -> list[dict]:
    """Parse CIBC Investor's Edge statements — handles multiple format eras (2014-2024+)."""
    transactions = []
    seen = set()
    lines = text.split('\n')

    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) < 20:
            continue

        # Skip header/footer lines
        if any(h in stripped.upper() for h in ['BALANCE FORWARD', 'PAGE', 'STATEMENT PERIOD',
            'OPENING BALANCE', 'CLOSING BALANCE', 'TOTAL', 'CIBC INVESTOR', 'TRADE DATE',
            'DESCRIPTION', 'DEBIT', 'CREDIT', '---']):
            continue

        # Pattern 1: TRADE lines with B,S prefix (Format B: ~2014-2018)
        # "15 Mar 2014 TRADE     B,RBC BANK COM NPV                         5,000.00    45,234.56"
        trade_match = re.match(
            r'(\d{1,2}\s+\w{3}\s+\d{4}|\d{4}-\d{2}-\d{2})\s+'
            r'(TRADE|DIV|BUY|SELL|PURCHASE|TRANSFER|FEE)\s+'
            r'(.+)',
            stripped
        )
        if trade_match:
            date_str = trade_match.group(1)
            activity = trade_match.group(2)
            remainder = trade_match.group(3).strip()

            # Extract all dollar amounts from the rest of the line
            amounts = re.findall(r'[\d,]+\.\d{2}', remainder)
            if len(amounts) < 1:
                continue

            # Remove amounts to get description
            desc = remainder
            for amt in amounts:
                desc = desc.replace(amt, '', 1)
            desc = desc.strip()

            # Determine buy/sell from B,S prefix in description
            action = 'OTHER'
            if activity == 'TRADE':
                bs_match = re.match(r'([BS]),\s*(.*)', desc)
                if bs_match:
                    action = 'BUY' if bs_match.group(1).upper() == 'B' else 'SELL'
                    desc = bs_match.group(2).strip()
                elif 'buy' in desc.lower() or 'purchase' in desc.lower():
                    action = 'BUY'
                elif 'sell' in desc.lower() or 'sale' in desc.lower():
                    action = 'SELL'
            elif activity in ('BUY', 'PURCHASE'):
                action = 'BUY'
            elif activity in ('SELL', 'SALE'):
                action = 'SELL'
            elif activity == 'DIV':
                action = 'DIVIDEND'

            # For CIBC format: amounts appear left to right as: Credit | Debit | Balance
            # For BUY:  Debit column has the transaction amount, Credit is empty
            # For SELL: Credit column has the transaction amount, Debit is empty
            # The last amount is always the running balance
            amounts_clean = [float(a.replace(',', '')) for a in amounts]
            if len(amounts_clean) >= 3:
                # 3+ amounts: first is credit, second is debit, last is balance
                if action == 'BUY':
                    total_amt = amounts_clean[1]  # debit
                elif action == 'SELL':
                    total_amt = amounts_clean[0]  # credit
                else:
                    total_amt = min(amounts_clean)  # dividend etc: smaller amount
            elif len(amounts_clean) == 2:
                # 2 amounts: one is transaction, one is balance (larger = balance)
                total_amt = min(amounts_clean)
            else:
                total_amt = amounts_clean[0] if amounts_clean else 0

            txn = {
                'trade_date': parse_date(date_str),
                'type': activity if activity in ('BUY', 'SELL', 'DIVIDEND', 'TRANSFER', 'FEE') else action,
                'symbol': extract_cibc_symbol(desc),
                'quantity': 0,
                'price': total_amt,
                'total': total_amt,
                'commission': 0,
                'account_type': extract_account_type(text),
                'currency': 'CAD' if 'CAD' in text[:5000] else 'USD',
                'description': desc[:250],
            }
            key = (txn['trade_date'], txn['type'], txn['description'][:60])
            if txn['trade_date'] and key not in seen:
                seen.add(key)
                transactions.append(txn)
            continue

        # Pattern 2: Generic date + amounts (no TRADE keyword)
        # "2024-03-15  PURCHASE RY.TO 100 @ $150.25          $15,025.00   $85,234.56"
        gen_match = re.match(
            r'(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w{3,9}\s+\d{4})\s+(.+)',
            stripped
        )
        if gen_match:
            date_str = gen_match.group(1)
            remainder = gen_match.group(2).strip()
            amounts = re.findall(r'\$?([\d,]+\.\d{2})', remainder)
            if len(amounts) < 1:
                continue

            desc = remainder
            for amt in amounts:
                desc = desc.replace(amt, '').replace('$', '', 1)
            desc = desc.strip()

            desc_lower = desc.lower()
            if any(h in desc.upper() for h in ['BALANCE', 'PAGE', 'STATEMENT', 'TOTAL', 'OPENING', 'CLOSING']):
                continue

            action = 'BUY' if any(kw in desc_lower for kw in ['buy', 'purchase', 'b,', 'b ,']) else \
                     'SELL' if any(kw in desc_lower for kw in ['sell', 'sale', 's,', 's ,']) else 'OTHER'

            amounts_clean = [float(a.replace(',', '')) for a in amounts]
            txn = {
                'trade_date': parse_date(date_str),
                'type': action,
                'symbol': extract_cibc_symbol(desc),
                'quantity': 0,
                'price': amounts_clean[0] if amounts_clean else 0,
                'total': amounts_clean[-1] if amounts_clean else 0,
                'commission': 0,
                'account_type': extract_account_type(text),
                'currency': 'CAD' if 'CAD' in text[:5000] else 'USD',
                'description': desc[:250],
            }
            key = (txn['trade_date'], txn['type'], txn['description'][:60])
            if txn['trade_date'] and key not in seen:
                seen.add(key)
                transactions.append(txn)

    return transactions


def extract_cibc_symbol(desc: str) -> str:
    """Extract symbol from CIBC statement description.
    
    CIBC statements often use full names like 'RBC BANK COM NPV' or 'BNS COM NPV'
    instead of ticker symbols. This maps common CIBC descriptions to tickers.
    """
    # Direct ticker pattern: 1-5 uppercase letters, optionally .TO/.NY/.etc
    m = re.search(r'\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b', desc)
    if m:
        sym = m.group(1)
        # Filter out common words that look like tickers
        non_symbols = {'COM', 'NPV', 'USD', 'CAD', 'THE', 'BANK', 'CORP', 'INC', 'CLASS', 'SERIES', 'FUND', 'ETF', 'TRUST', 'LIMITED', 'LTD'}
        if sym not in non_symbols:
            return sym

    # Map common CIBC description patterns to tickers
    # These are common in older CIBC statements
    cibc_name_map = [
        (r'RBC\s+BANK', 'RY.TO'),
        (r'BMO\s+BANK', 'BMO.TO'),
        (r'BNS|BANK\s+OF\s+NOVA\s+SCOTIA', 'BNS.TO'),
        (r'TD\s+BANK|TORONTO\s+DOMINION', 'TD.TO'),
        (r'CIBC|CANADIAN\s+IMPERIAL', 'CM.TO'),
        (r'SUN\s+LIFE', 'SLF.TO'),
        (r'MANULIFE', 'MFC.TO'),
        (r'POWER\s+CORP', 'POW.TO'),
        (r'NATIONAL\s+BANK', 'NA.TO'),
        (r'ENBRIDGE', 'ENB.TO'),
        (r'CANADIAN\s+NATURAL', 'CNQ.TO'),
        (r'SUNCOR', 'SU.TO'),
        (r'CANADIAN\s+OIL\s+SANDS', 'COS.TO'),  # not real but common name
        (r'TRANS\s+CANADA|TC\s+ENERGY', 'TRP.TO'),
        (r'IMPERIAL\s+OIL|IMPERIAL', 'IMO.TO'),
        (r'CANADIAN\s+UTILITIES', 'CU.TO'),
        (r'FORTIS', 'FTS.TO'),
        (r'HYDRO\s+ONE', 'H.TO'),
        (r'PIPESTONE\s+ENERGY', 'PIPE.TO'),
        (r'GIBSON\s+ENERGY', 'GEI.TO'),
        (r'VERITONE\s+ENERGY', 'VET.TO'),
        (r'ALTAGAS', 'ALA.TO'),
        (r'KEYERA', 'KEY.TO'),
        (r'PARK\s+LAND\s+CORP', 'PKI.TO'),
        (r'INTER\s+PIPELINE', 'IPL.TO'),
        (r'PEMBINA\s+PIPELINE', 'PPL.TO'),
        (r'CENOVUS', 'CVE.TO'),
        (r'ARC\s+RESOURCES', 'ARX.TO'),
        (r'BIRCHCLIFF\s+ENERGY', 'BIR.TO'),
        (r'BONAVISTA\s+ENERGY', 'BNP.TO'),
        (r'KELT\s+EXPLORATION', 'KEL.TO'),
        (r'MULLEN\s+GROUP', 'MTL.TO'),
        (r'TIDAL\s+ROYALTY', 'TAL.TO'),
        (r'C\s+PLUS', 'CPX.TO'),
        (r'ATCO\s+CLASS', 'ACO-X.TO'),
    ]
    
    desc_upper = desc.upper()
    for pattern, ticker in cibc_name_map:
        if re.search(pattern, desc_upper):
            return ticker

    return ''


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
