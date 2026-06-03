#!/usr/bin/env python3
"""
parse_pdf_statement.py — Parse brokerage PDF statements and extract transactions.

Supports: CIBC Investor's Edge, Questrade, TD Direct Investing, BMO InvestorLine,
Scotiabank iTrade, RBC Direct Investing, and generic formats.

Usage: python3 parse_pdf_statement.py <pdf_path> [--debug]

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
import os
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


def parse_cibc_multiline_date(date_str: str, text: str) -> str:
    """Parse date from multi-line CIBC format like 'Jan 15' using statement period for year."""
    # Try to find year from statement period
    year_match = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+\s*[-–]\s*(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+,?\s+(\d{4})', text)
    year = year_match.group(1) if year_match else None

    # Try to parse the date with various formats
    for fmt in ['%b %d', '%B %d']:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if year:
                return f"{year}-{dt.month:02d}-{dt.day:02d}"
            else:
                return f"2014-{dt.month:02d}-{dt.day:02d}"  # fallback
        except ValueError:
            continue

    return date_str


def parse_cibc(text: str) -> list[dict]:
    """Parse CIBC Investor's Edge statements — handles multiple format eras (2014-2024+).

    Supports three distinct formats:
    A) Multi-line (2014-2016): Each transaction spans multiple lines:
       Jan 15
       Dividend
       TRANSFORCE INC
       −
       $40.89
       CASH DIV ON 282 SHS ...

    B) Single-line TRADE (2014-2018): "15 Mar 2014 TRADE  B,RBC BANK COM NPV  5,000.00  45,234.56"

    C) Single-line generic (2018+): "2024-03-15  PURCHASE RY.TO 100 @ $150.25  $15,025.00"
    """
    transactions = []
    seen = set()
    lines = text.split('\n')

    # ── Detect which format we're dealing with ──
    activity_keywords = ['Dividend', 'Dividends', 'Transfer', 'Purchase', 'Sale', 'Trade',
                         'Contribution', 'Withdrawal', 'Fee', 'Interest', 'Reinvestment']
    multiline_count = 0
    for line in lines:
        s = line.strip()
        if s in activity_keywords:
            multiline_count += 1

    use_multiline = multiline_count >= 2

    if use_multiline:
        # ── Format A: Multi-line parser ──
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for a date-like line: "Jan 15", "Feb 1", "Mar 31", etc.
            date_match = re.match(r'^(\w{3,9}\s+\d{1,2})$', line)
            if not date_match:
                i += 1
                continue

            date_str = date_match.group(1)

            # Next line should be the activity type
            if i + 1 >= len(lines):
                i += 1
                continue
            activity_line = lines[i + 1].strip()
            activity_map = {
                'Dividend': 'DIVIDEND', 'Dividends': 'DIVIDEND',
                'Transfer': 'TRANSFER', 'Contribution': 'TRANSFER',
                'Withdrawal': 'WITHDRAWAL', 'Purchase': 'BUY',
                'Sale': 'SELL', 'Trade': 'TRADE',
                'Fee': 'FEE', 'Interest': 'INTEREST',
                'Reinvestment': 'DIVIDEND_REINVEST',
            }
            activity = activity_map.get(activity_line, 'OTHER')

            if activity == 'OTHER':
                i += 1
                continue

            # Collect remaining lines
            desc_lines = []
            amount_val = 0
            j = i + 2

            # Description (company name, possibly multi-line)
            while j < len(lines) and len(desc_lines) < 3:
                dl = lines[j].strip()
                if not dl or dl in ('−', '-', '--'):
                    j += 1
                    break
                if re.match(r'^\w{3,9}\s+\d{1,2}$', dl):
                    break
                desc_lines.append(dl)
                j += 1

            # Skip separator line
            while j < len(lines):
                dl = lines[j].strip()
                if dl in ('−', '-', '--'):
                    j += 1
                    continue
                break

            # Amount line
            if j < len(lines):
                amt_line = lines[j].strip()
                amt_match = re.search(r'\$?([\d,]+\.?\d*)', amt_line)
                if amt_match:
                    try:
                        amount_val = float(amt_match.group(1).replace(',', ''))
                    except ValueError:
                        amount_val = 0
                j += 1

            # Remaining detail lines
            detail_lines = []
            while j < len(lines):
                dl = lines[j].strip()
                if not dl:
                    break
                if re.match(r'^\w{3,9}\s+\d{1,2}$', dl):
                    break
                if dl in activity_keywords:
                    break
                detail_lines.append(dl)
                j += 1

            desc = ' '.join(desc_lines + detail_lines)[:250]
            full_date = parse_cibc_multiline_date(date_str, text)

            txn = {
                'trade_date': full_date,
                'type': activity,
                'symbol': extract_cibc_symbol(desc),
                'quantity': 0,
                'price': amount_val,
                'total': amount_val,
                'commission': 0,
                'account_type': extract_account_type(text),
                'currency': 'CAD' if 'Canadian Dollars' in text[:8000] or 'CAD' in text[:8000] else 'USD',
                'description': desc,
            }
            key = (txn['trade_date'], txn['type'], txn['description'][:60])
            if txn['trade_date'] and key not in seen:
                seen.add(key)
                transactions.append(txn)

            i = j
        return transactions

    # ── Format B: Single-line TRADE parser ──
    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) < 20:
            continue

        # Skip header/footer lines
        if any(h in stripped.upper() for h in ['BALANCE FORWARD', 'PAGE', 'STATEMENT PERIOD',
            'OPENING BALANCE', 'CLOSING BALANCE', 'TOTAL', 'CIBC INVESTOR', 'TRADE DATE',
            'DESCRIPTION', 'DEBIT', 'CREDIT', '---']):
            continue

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

            amounts = re.findall(r'[\d,]+\.\d{2}', remainder)
            if len(amounts) < 1:
                continue

            desc = remainder
            for amt in amounts:
                desc = desc.replace(amt, '', 1)
            desc = desc.strip()

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

            amounts_clean = [float(a.replace(',', '')) for a in amounts]
            if len(amounts_clean) >= 3:
                if action == 'BUY':
                    total_amt = amounts_clean[1]
                elif action == 'SELL':
                    total_amt = amounts_clean[0]
                else:
                    total_amt = min(amounts_clean)
            elif len(amounts_clean) == 2:
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

        # ── Format C: Generic single-line parser ──
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
    """Extract symbol from CIBC statement description."""
    desc_upper = desc.upper()

    cibc_name_map = [
        (r'R\s*B\s*C\s+BANK', 'RY.TO'),
        (r'B\s*M\s*O\s+BANK', 'BMO.TO'),
        (r'B\s*N\s*S|BANK\s+OF\s+NOVA\s+SCOTIA', 'BNS.TO'),
        (r'T\s*D\s+BANK|TORONTO\s+DOMINION', 'TD.TO'),
        (r'C\s*I\s*B\s*C|CANADIAN\s+IMPERIAL', 'CM.TO'),
        (r'SUN\s+LIFE', 'SLF.TO'),
        (r'MANULIFE', 'MFC.TO'),
        (r'POWER\s+CORP', 'POW.TO'),
        (r'NATIONAL\s+BANK', 'NA.TO'),
        (r'ENBRIDGE', 'ENB.TO'),
        (r'CANADIAN\s+NATURAL|CNRL', 'CNQ.TO'),
        (r'SUNCOR', 'SU.TO'),
        (r'TRANS\s+CANADA|TC\s+ENERGY|TC\s+P\s*E', 'TRP.TO'),
        (r'IMPERIAL\s+OIL|IMO', 'IMO.TO'),
        (r'CANADIAN\s+UTILITIES', 'CU.TO'),
        (r'FORTIS', 'FTS.TO'),
        (r'HYDRO\s+ONE', 'H.TO'),
        (r'PIPESTONE\s+ENERGY', 'PIPE.TO'),
        (r'GIBSON\s+ENERGY', 'GEI.TO'),
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
        (r'C\s+PLUS', 'CPX.TO'),
        (r'ATCO\s+CLASS', 'ACO-X.TO'),
        (r'TRANSFORCE', 'TFI.TO'),
        (r'KEG\s+ROYALTIES', 'KEG.UN.TO'),
    ]

    for pattern, ticker in cibc_name_map:
        if re.search(pattern, desc_upper):
            return ticker

    # Direct ticker pattern
    m = re.search(r'\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b', desc)
    if m:
        sym = m.group(1)
        non_symbols = {'COM', 'NPV', 'USD', 'CAD', 'THE', 'BANK', 'CORP', 'INC', 'CLASS', 'SERIES', 'FUND', 'ETF', 'TRUST', 'LIMITED', 'LTD', 'AND', 'OF', 'TO', 'FOR', 'ON', 'SHS', 'REC', 'PAY', 'DIV', 'CASH'}
        if sym not in non_symbols:
            return sym

    return ''


def parse_questrade(text: str) -> list[dict]:
    """Parse Questrade statements."""
    transactions = []
    pattern = r'(\d{4}-\d{2}-\d{2})\s+([A-Z0-9.]+)\s+(Buy|Sell)\s+([[\d,]+)\s+\$?([\d.]+)\s+\$?([\d.]+)\s+\$?([\d.]+)'

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
    lines = text.split('\n')
    for line in lines:
        m = re.search(
            r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\w{3}\s+\d{1,2},?\s+\d{4})\s+'
            r'(BUY|SELL|PURCHASE|SALE)\s+'
            r'([[\d,]+)\s+'
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
        print(json.dumps({"error": "Usage: parse_pdf_statement.py <pdf_path> [--debug]"}))
        sys.exit(1)

    pdf_path = sys.argv[1]
    debug_mode = '--debug' in sys.argv

    try:
        text, pages = extract_text(pdf_path)
    except Exception as e:
        print(json.dumps({"error": f"Failed to extract text: {e}"}))
        sys.exit(1)

    fmt = detect_format(text)
    account = extract_account_type(text)

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

    # Debug output
    if debug_mode or len(transactions) == 0:
        result['text_preview'] = text[:3000]
        suspicious_lines = []
        for line in text.split('\n'):
            s = line.strip()
            if len(s) > 15 and re.search(r'\d{1,2}\s+\w{3,9}\s+\d{4}|\d{4}-\d{2}-\d{2}', s):
                if re.search(r'[\d,]+\.\d{2}', s):
                    suspicious_lines.append(s[:200])
        result['suspicious_lines'] = suspicious_lines[:20]

        # Write debug file
        try:
            debug_dir = '/var/www/stockmarket-app/uploads/debug/'
            os.makedirs(debug_dir, exist_ok=True)
            debug_file = debug_dir + os.path.basename(pdf_path) + '.debug.txt'
            with open(debug_file, 'w') as f:
                f.write(f"Format: {fmt}\n")
                f.write(f"Account: {account}\n")
                f.write(f"Pages: {pages}\n")
                f.write(f"Transactions found: {len(transactions)}\n\n")
                f.write("=== FULL EXTRACTED TEXT ===\n")
                f.write(text)
                f.write("\n=== SUSPICIOUS LINES ===\n")
                for sl in result.get('suspicious_lines', []):
                    f.write(sl + "\n")
        except Exception:
            pass

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
