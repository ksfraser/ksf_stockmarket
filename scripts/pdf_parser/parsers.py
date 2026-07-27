"""
Shared PDF statement parser module.

Used by both:
  - parse_pdf_statement.py (web upload UI CLI wrapper)
  - extract_tfsa.py (email gateway pipeline)

Provides: extract_text(), detect_format(), parse_cibc(), parse_questrade(),
          parse_generic(), parse_statement(), and all helper functions.
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Optional

# Load project .env for OCR/config overrides
try:
    from dotenv import load_dotenv
    _here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_here, "..", "config", ".env"))
except Exception:
    pass


# ── Text extraction ──────────────────────────────────────────────────────

def extract_text(pdf_path: str, force_ocr: bool = False) -> tuple[str, int]:
    """Extract text from PDF using pymupdf (fitz), with optional OCR fallback."""
    import fitz
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    pages = len(doc)
    doc.close()

    if not text.strip() or force_ocr:
        text = ocr_pdf(pdf_path) or text

    return text, pages


def ocr_pdf(pdf_path: str) -> str:
    """OCR fallback via configured OCR API."""
    import os
    import requests
    host = os.getenv("OCR_HOST", "192.168.1.102")
    port = os.getenv("OCR_PORT", "8082")
    api_path = os.getenv("OCR_API_PATH", "/ocr")
    timeout = int(os.getenv("OCR_TIMEOUT", "60"))
    url = f"http://{host}:{port}{api_path}"
    try:
        with open(pdf_path, "rb") as fh:
            files = {"file": (os.path.basename(pdf_path), fh, "application/pdf")}
            resp = requests.post(url, files=files, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json() if "json" in resp.headers.get("content-type", "") else {}
            text = data.get("text") or data.get("data") or resp.text
            return text if isinstance(text, str) else ""
    except Exception:
        pass
    return ""


# ── Format detection ──────────────────────────────────────────────────────

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

    if re.search(r'(?:BUY|SELL|TRADE|PURCHASE)\s+\d+', text):
        return "generic"

    return "unknown"


# ── CIBC Investor's Edge parser ───────────────────────────────────────────

ACTIVITY_KEYWORDS = [
    'Dividend', 'Dividends', 'Transfer', 'Purchase', 'Sale', 'Trade',
    'Contribution', 'Withdrawal', 'Fee', 'Interest', 'Reinvestment',
]

ACTIVITY_MAP = {
    'Dividend': 'DIVIDEND', 'Dividends': 'DIVIDEND',
    'Transfer': 'TRANSFER', 'Contribution': 'TRANSFER',
    'Withdrawal': 'WITHDRAWAL', 'Purchase': 'BUY',
    'Sale': 'SELL', 'Trade': 'TRADE',
    'Fee': 'FEE', 'Interest': 'INTEREST',
    'Reinvestment': 'DIVIDEND_REINVEST',
}

# Maps description patterns to ticker symbols
CIBC_NAME_MAP = [
    (r'TRANSFORCE', 'TFI.TO'),
    (r'KEG\s+(ROYALTIES|UNITS|INCOME)', 'KEG.UN.TO'),
    (r'BPF\.?UN|BOSTON\s+PIZZA', 'BPF.UN.TO'),
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
    (r'TRANS\s+CANADA|TC\s+ENERGY', 'TRP.TO'),
    (r'IMPERIAL\s+OIL|IMO', 'IMO.TO'),
    (r'CANADIAN\s+UTILITIES', 'CU.TO'),
    (r'FORTIS', 'FTS.TO'),
    (r'HYDRO\s+ONE', 'H.TO'),
    (r'PIPESTONE\s+ENERGY', 'PIPE.TO'),
    (r'GIBSON\s+ENERGY', 'GEI.TO'),
    (r'ALTAGAS', 'ALA.TO'),
    (r'KEYERA', 'KEY.TO'),
    (r'PARK\s+LAND', 'PKI.TO'),
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
    (r'VDY|VANGUARD\s+SELECT\s+DIVIDEND', 'VDY.TO'),
    (r'ZDV|BNS\s+CANADIAN\s+DIVIDEND', 'ZDV.TO'),
]
CIBC_NON_SYMBOLS = {
    'COM', 'NPV', 'USD', 'CAD', 'THE', 'BANK', 'CORP', 'INC', 'CLASS',
    'SERIES', 'FUND', 'ETF', 'TRUST', 'LIMITED', 'LTD', 'AND', 'OF', 'TO',
    'FOR', 'ON', 'SHS', 'REC', 'PAY', 'DIV', 'CASH', 'TRUST', 'UNITS',
}


def extract_cibc_symbol(desc: str) -> str:
    """Extract ticker symbol from CIBC statement description."""
    desc_upper = desc.upper()
    for pattern, ticker in CIBC_NAME_MAP:
        if re.search(pattern, desc_upper):
            return ticker
    m = re.search(r'\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b', desc)
    if m:
        sym = m.group(1)
        if sym not in CIBC_NON_SYMBOLS:
            return sym
    return ''


def parse_cibc_multiline_date(date_str: str, text: str) -> str:
    """Parse date from multi-line CIBC format like 'Jan 15' using statement year."""
    year_match = re.search(
        r'(?:January|February|March|April|May|June|July|August|September|'
        r'October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|'
        r'Nov|Dec)\s+\d+\s*[-–]\s*(?:January|February|March|April|May|June|'
        r'July|August|September|October|November|December|Jan|Feb|Mar|Apr|'
        r'May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+,?\s+(\d{4})',
        text,
    )
    year = year_match.group(1) if year_match else None
    for fmt in ['%b %d', '%B %d']:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            yy = year if year else '2014'
            return "{}-{:02d}-{:02d}".format(yy, dt.month, dt.day)
        except ValueError:
            continue
    return date_str


def parse_cibc(text: str) -> list:
    """Parse CIBC Investor's Edge statements.

    Handles three format eras:
      A) Multi-line (2014-2016): Date on one line, activity on next, etc.
      B) Single-line TRADE (2014-2018): "15 Mar 2014 TRADE B,RBC BANK ..."
      C) Single-line generic (2018+): "2024-03-15 PURCHASE RY.TO ..."
    """
    transactions = []
    seen = set()
    lines = text.split('\n')

    # Detect format by counting standalone activity keywords
    multiline_count = sum(1 for line in lines if line.strip() in ACTIVITY_KEYWORDS)
    use_multiline = multiline_count >= 2

    if use_multiline:
        # ── Format A: Multi-line ──
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            date_match = re.match(r'^(\w{3,9}\s+\d{1,2})$', line)
            if not date_match:
                i += 1
                continue

            date_str = date_match.group(1)
            if i + 1 >= len(lines):
                i += 1
                continue

            activity_line = lines[i + 1].strip()
            activity = ACTIVITY_MAP.get(activity_line, 'OTHER')
            if activity == 'OTHER':
                i += 1
                continue

            desc_lines = []
            amount_val = 0
            j = i + 2

            # Collect description lines (company name etc.)
            while j < len(lines) and len(desc_lines) < 3:
                dl = lines[j].strip()
                if not dl or dl in ('\u2212', '\u2013', '-', '--'):
                    j += 1
                    break
                if re.match(r'^\w{3,9}\s+\d{1,2}$', dl):
                    break
                desc_lines.append(dl)
                j += 1

            # Skip separator line
            while j < len(lines) and lines[j].strip() in ('\u2212', '\u2013', '-', '--'):
                j += 1

            # Amount line
            if j < len(lines):
                amt_match = re.search(r'\$?([\d,]+\.?\d*)', lines[j].strip())
                if amt_match:
                    try:
                        amount_val = float(amt_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
                j += 1

            # Detail lines
            detail_lines = []
            while j < len(lines):
                dl = lines[j].strip()
                if not dl:
                    break
                if re.match(r'^\w{3,9}\s+\d{1,2}$', dl):
                    break
                if dl in ACTIVITY_KEYWORDS:
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
                'currency': 'CAD' if 'CAD' in text[:8000] else 'USD',
                'description': desc,
            }
            key = (full_date, activity, desc[:60])
            if full_date and key not in seen:
                seen.add(key)
                transactions.append(txn)
            i = j
        return transactions

    # ── Format B: Single-line TRADE ──
    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) < 20:
            continue
        if any(h in stripped.upper() for h in [
            'BALANCE FORWARD', 'PAGE', 'STATEMENT PERIOD', 'OPENING BALANCE',
            'CLOSING BALANCE', 'TOTAL', 'CIBC INVESTOR', 'TRADE DATE',
            'DESCRIPTION', 'DEBIT', 'CREDIT', '---',
        ]):
            continue

        trade_match = re.match(
            r'(\d{1,2}\s+\w{3}\s+\d{4}|\d{4}-\d{2}-\d{2})\s+'
            r'(TRADE|DIV|BUY|SELL|PURCHASE|TRANSFER|FEE)\s+(.+)',
            stripped,
        )
        if trade_match:
            date_str = trade_match.group(1)
            activity_raw = trade_match.group(2)
            remainder = trade_match.group(3).strip()

            amounts = re.findall(r'[\d,]+\.\d{2}', remainder)
            if not amounts:
                continue

            desc = remainder
            for amt in amounts:
                desc = desc.replace(amt, '', 1)
            desc = desc.strip()

            action = 'OTHER'
            if activity_raw == 'TRADE':
                bs = re.match(r'([BS]),\s*(.*)', desc)
                if bs:
                    action = 'BUY' if bs.group(1).upper() == 'B' else 'SELL'
                    desc = bs.group(2).strip()
                elif 'buy' in desc.lower() or 'purchase' in desc.lower():
                    action = 'BUY'
                elif 'sell' in desc.lower():
                    action = 'SELL'
            elif activity_raw in ('BUY', 'PURCHASE'):
                action = 'BUY'
            elif activity_raw in ('SELL',):
                action = 'SELL'
            elif activity_raw == 'DIV':
                action = 'DIVIDEND'

            amounts_clean = [float(a.replace(',', '')) for a in amounts]
            if len(amounts_clean) >= 3:
                if action == 'BUY':
                    total_amt = amounts_clean[1]  # debit column
                elif action == 'SELL':
                    total_amt = amounts_clean[0]  # credit column
                else:
                    total_amt = min(amounts_clean)
            elif len(amounts_clean) == 2:
                total_amt = min(amounts_clean)  # smaller = transaction
            else:
                total_amt = amounts_clean[0] if amounts_clean else 0

            activity_final = activity_raw if activity_raw in (
                'BUY', 'SELL', 'DIVIDEND', 'TRANSFER', 'FEE',
            ) else action

            txn = {
                'trade_date': parse_date(date_str),
                'type': activity_final,
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

        # ── Format C: Generic single-line ──
        gen_match = re.match(
            r'(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w{3,9}\s+\d{4})\s+(.+)',
            stripped,
        )
        if gen_match:
            date_str = gen_match.group(1)
            remainder = gen_match.group(2).strip()
            amounts = re.findall(r'\$?([\d,]+\.\d{2})', remainder)
            if not amounts:
                continue

            desc = remainder
            for amt in amounts:
                desc = desc.replace(amt, '').replace('$', '', 1)
            desc = desc.strip()

            dl_lower = desc.lower()
            if any(h in desc.upper() for h in [
                'BALANCE', 'PAGE', 'STATEMENT', 'TOTAL', 'OPENING', 'CLOSING',
            ]):
                continue

            action = 'BUY' if any(kw in dl_lower for kw in ['buy', 'purchase', 'b,']) else \
                     'SELL' if any(kw in dl_lower for kw in ['sell', 'sale', 's,']) else 'OTHER'

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


# ── Questrade parser ──────────────────────────────────────────────────────

def parse_questrade(text: str) -> list:
    """Parse Questrade statements."""
    transactions = []
    pattern = (
        r'(\d{4}-\d{2}-\d{2})\s+([A-Z0-9.]+)\s+(Buy|Sell)\s+'
        r'([\d,]+)\s+\$?([\d.]+)\s+\$?([\d.]+)\s+\$?([\d.]+)'
    )
    for m in re.finditer(pattern, text):
        qty = float(m.group(4).replace(',', ''))
        transactions.append({
            'trade_date': m.group(1),
            'symbol': m.group(2),
            'type': m.group(3).upper(),
            'quantity': qty,
            'price': float(m.group(5)),
            'commission': float(m.group(6)),
            'total': float(m.group(7)),
            'account_type': extract_account_type(text),
            'currency': 'CAD',
            'description': "{} {} {} @ ${}".format(m.group(3), qty, m.group(2), m.group(5)),
        })
    return transactions


# ── Generic parser ────────────────────────────────────────────────────────

def parse_generic(text: str) -> list:
    """Generic parser for unsupported formats."""
    transactions = []
    for line in text.split('\n'):
        m = re.search(
            r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\w{3}\s+\d{1,2},?\s+\d{4})\s+'
            r'(BUY|SELL|PURCHASE|SALE)\s+([\d,]+)\s+'
            r'([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\s+\$?([\d,.]+)',
            line, re.IGNORECASE,
        )
        if not m:
            continue
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


# ── Helpers ───────────────────────────────────────────────────────────────

def parse_date(date_str: str) -> str:
    """Parse various date formats to YYYY-MM-DD."""
    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%b %d, %Y',
                '%B %d, %Y', '%b %d %Y', '%Y/%m/%d', '%d-%b-%Y']:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str


def extract_account_type(text: str) -> str:
    """Detect account type from statement text."""
    upper = text.upper()
    for keyword, label in [('TFSA', 'TFSA'), ('RRSP', 'RRSP'), ('MARGIN', 'MARGIN'),
                            ('RESP', 'RESP'), ('JOINT', 'JOINT'), ('T.F.S.A.', 'TFSA'),
                            ('R.R.S.P.', 'RRSP')]:
        if keyword in upper:
            return label
    return 'UNKNOWN'


# ── Main dispatch ─────────────────────────────────────────────────────────

PARSERS = {
    'cibc': parse_cibc,
    'questrade': parse_questrade,
    'generic': parse_generic,
    'td': parse_cibc,       # TD uses similar format to CIBC
    'bmo': parse_generic,
    'scotia': parse_generic,
    'rbc': parse_generic,
}


def parse_statement(pdf_path: str, debug: bool = False, force_ocr: bool = False) -> dict:
    """
    Parse a brokerage PDF statement and return structured data.

    Returns:
        {
            'format': str,
            'account': str,
            'pages': int,
            'transactions': [...],
            'text_preview': str,       (only if debug or 0 transactions)
            'suspicious_lines': [...], (only if debug or 0 transactions)
        }
    """
    text, pages = extract_text(pdf_path, force_ocr=force_ocr)
    fmt = detect_format(text)
    account = extract_account_type(text)

    parser_fn = PARSERS.get(fmt, parse_generic)
    transactions = parser_fn(text)

    result = {
        'format': fmt,
        'account': account,
        'pages': pages,
        'transactions': transactions,
    }

    if debug or not transactions:
        result['text_preview'] = text[:3000]
        suspicious = []
        for line in text.split('\n'):
            s = line.strip()
            if len(s) > 15 and re.search(
                r'\d{1,2}\s+\w{3,9}\s+\d{4}|\d{4}-\d{2}-\d{2}', s
            ):
                if re.search(r'[\d,]+\.\d{2}', s):
                    suspicious.append(s[:200])
        result['suspicious_lines'] = suspicious[:20]

    return result
