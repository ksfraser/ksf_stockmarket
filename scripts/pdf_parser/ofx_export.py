"""
OFX/QFX Export Module — Convert database transactions to OFX 2.x format.

Produces valid OFX 2.2 files compatible with:
  - FrontAccounting (via ksf_qfxparser)
  - GnuCash, Quicken, Money, etc.

OFX 2.x uses XML-like tags. Investment statements use the INVSTMTMSGSRSV1 envelope.

Usage:
    from pdf_parser.ofx_export import OfxExporter

    exporter = OfxExporter(db_config)
    ofx_data = exporter.export_account(account_type='TFSA', start_date='2024-01-01')
    with open('tfsa.ofx', 'w') as f:
        f.write(ofx_data)

    # Or export all accounts:
    ofx_data = exporter.export_all_accounts()
"""

import hashlib
import random
import string
from datetime import datetime, date
from decimal import Decimal
from xml.sax.saxutils import escape


# ── OFX Constants ─────────────────────────────────────────────────────────

OFX_HEADER = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?OFX OFXHEADER="200" VERSION="220" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>
"""

# Map our transaction types to OFX investment transaction types
# OFX uses: BUY, SELL, INCOME, EXPENSE, TRANSFER, REINVEST, etc.
TXN_TYPE_MAP = {
    'BUY': 'BUY',
    'SELL': 'SELL',
    'DIVIDEND': 'INCOME',
    'DIVIDEND_REINVEST': 'REINVEST',
    'TRANSFER': 'TRANSFER',
    'FEE': 'EXPENSE',
    'INTEREST': 'INCOME',
    'SPLIT': 'SPLIT',
    'OTHER': 'OTHER',
}

# Map to OFX sub-types
TXN_SUBTYPE_MAP = {
    'BUY': 'BUY',
    'SELL': 'SELL',
    'DIVIDEND': 'DIV',       # Dividend
    'DIVIDEND_REINVEST': 'REINVEST',
    'TRANSFER': 'TRANSFER',
    'FEE': 'FEE',
    'INTEREST': 'INT',       # Interest
    'SPLIT': 'SPLIT',
    'OTHER': 'OTHER',
}


def _generate_fitid(txn: dict) -> str:
    """Generate a unique Financial Institution Transaction ID.

    OFX requires each transaction to have a unique FITID.
    We create one from the transaction data to ensure idempotency.
    """
    raw = "{}-{}-{}-{}-{}-{}-{}".format(
        txn.get('account_type', ''),
        txn.get('trade_date', ''),
        txn.get('type', ''),
        txn.get('symbol', ''),
        txn.get('quantity', ''),
        txn.get('total', ''),
        txn.get('id', random.randint(1, 999999)),
    )
    return hashlib.md5(raw.encode()).hexdigest()[:20].upper()


def _format_ofx_date(d) -> str:
    """Format a date as OFX date: YYYYMMDDHHMMSS or YYYYMMDD."""
    if d is None:
        return datetime.now().strftime('%Y%m%d')
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, '%Y-%m-%d')
        except ValueError:
            return d.replace('-', '')
    if isinstance(d, (datetime, date)):
        return d.strftime('%Y%m%d')
    return str(d)


def _format_amount(amount) -> str:
    """Format an amount for OFX (2 decimal places, no commas)."""
    if amount is None:
        return '0.00'
    try:
        return '{:.2f}'.format(float(amount))
    except (ValueError, TypeError):
        return '0.00'


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    if not text:
        return ''
    return escape(str(text))


def _txn_to_ofx(txn: dict) -> str:
    """Convert a single transaction dict to OFX INVTRAN XML."""
    fitid = _generate_fitid(txn)
    dttrade = _format_ofx_date(txn.get('trade_date'))
    txn_type = txn.get('type', 'OTHER')
    ofx_type = TXN_TYPE_MAP.get(txn_type, 'OTHER')
    subtype = TXN_SUBTYPE_MAP.get(txn_type, 'OTHER')
    symbol = txn.get('symbol', '') or ''
    memo = txn.get('notes', '') or txn.get('description', '') or ''

    # Determine amount sign
    # BUY = negative (money out), SELL = positive (money in)
    # DIVIDEND = positive (money in), FEE = negative (money out)
    total = txn.get('total', 0) or 0
    quantity = txn.get('quantity', 0) or 0
    price = txn.get('price', 0) or 0
    commission = txn.get('commission', 0) or 0

    if txn_type == 'BUY':
        amount = -abs(float(total))
    elif txn_type == 'SELL':
        amount = abs(float(total))
    elif txn_type in ('DIVIDEND', 'INTEREST'):
        amount = abs(float(total))
    elif txn_type == 'FEE':
        amount = -abs(float(total))
    else:
        amount = float(total)

    lines = ['    <INVTRAN>']
    lines.append('      <FITID>{}</FITID>'.format(fitid))
    lines.append('      <DTTRADE>{}</DTTRADE>'.format(dttrade))

    if txn_type in ('BUY', 'SELL'):
        # Investment buy/sell
        lines.append('      <BUYTYPE>{}</BUYTYPE>'.format(ofx_type))
        lines.append('      <UNITS>{:.4f}</UNITS>'.format(float(quantity)))
        lines.append('      <UNITPRICE>{:.4f}</UNITPRICE>'.format(float(price)))
        lines.append('      <TOTAL>{:.2f}</TOTAL>'.format(amount))
        if commission and float(commission) != 0:
            lines.append('      <COMMISSION>{:.2f}</COMMISSION>'.format(float(commission)))
        if symbol:
            lines.append('      <SECID>')
            lines.append('        <UNIQUEID>{}</UNIQUEID>'.format(_escape_xml(symbol)))
            lines.append('        <UNIQUEIDTYPE>TICKER</UNIQUEIDTYPE>')
            lines.append('      </SECID>')
        if memo:
            lines.append('      <MEMO>{}</MEMO>'.format(_escape_xml(memo[:255])))

    elif txn_type in ('DIVIDEND', 'DIVIDEND_REINVEST', 'INTEREST'):
        # Income (dividend, interest)
        lines.append('      <INCOMETYPE>{}</INCOMETYPE>'.format(subtype))
        lines.append('      <TOTAL>{:.2f}</TOTAL>'.format(amount))
        if symbol:
            lines.append('      <SECID>')
            lines.append('        <UNIQUEID>{}</UNIQUEID>'.format(_escape_xml(symbol)))
            lines.append('        <UNIQUEIDTYPE>TICKER</UNIQUEIDTYPE>')
            lines.append('      </SECID>')
        if memo:
            lines.append('      <MEMO>{}</MEMO>'.format(_escape_xml(memo[:255])))

    elif txn_type == 'FEE':
        lines.append('      <TOTAL>{:.2f}</TOTAL>'.format(amount))
        if memo:
            lines.append('      <MEMO>{}</MEMO>'.format(_escape_xml(memo[:255])))

    elif txn_type == 'TRANSFER':
        lines.append('      <TOTAL>{:.2f}</TOTAL>'.format(amount))
        if memo:
            lines.append('      <MEMO>{}</MEMO>'.format(_escape_xml(memo[:255])))

    else:
        # Generic
        lines.append('      <TOTAL>{:.2f}</TOTAL>'.format(amount))
        if symbol:
            lines.append('      <SECID>')
            lines.append('        <UNIQUEID>{}</UNIQUEID>'.format(_escape_xml(symbol)))
            lines.append('        <UNIQUEIDTYPE>TICKER</UNIQUEIDTYPE>')
            lines.append('      </SECID>')
        if memo:
            lines.append('      <MEMO>{}</MEMO>'.format(_escape_xml(memo[:255])))

    lines.append('    </INVTRAN>')
    return '\n'.join(lines)


# ── Main Exporter Class ───────────────────────────────────────────────────

class OfxExporter:
    """Export transactions from MySQL to OFX 2.x format."""

    def __init__(self, db_config: dict = None):
        """
        Initialize with database config.

        Args:
            db_config: dict with keys: host, database, user, password
                      If None, loads from Ansible Vault.
        """
        if db_config:
            self.db_config = db_config
        else:
            self.db_config = self._load_config()

    @staticmethod
    def _load_config() -> dict:
        """Load DB config from Ansible Vault."""
        import subprocess
        import yaml

        vault_path = '/home/ksf_stockmarket/ksf_stockmarket/group_vars/vault.yml'
        vault_pass = '/home/ksf_stockmarket/.vault_pass'

        try:
            result = subprocess.run(
                ['ansible-vault', 'view', vault_path,
                 '--vault-password-file', vault_pass],
                capture_output=True, text=True, timeout=15,
            )
            vault = yaml.safe_load(result.stdout)
            return {
                'host': 'ksfraser.ca',
                'database': 'ksfraser_stock_market',
                'user': 'ksfraser_stockmarket',
                'password': vault.get('db_password', ''),
            }
        except Exception:
            return {
                'host': 'ksfraser.ca',
                'database': 'ksfraser_stock_market',
                'user': 'ksfraser_stockmarket',
                'password': '',
            }

    def _get_connection(self):
        """Get a MySQL connection."""
        import mysql.connector
        return mysql.connector.connect(**self.db_config)

    def get_accounts(self) -> list:
        """Get list of distinct account types that have transactions."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT account_type, COUNT(*) as cnt,
                   MIN(trade_date) as earliest, MAX(trade_date) as latest
            FROM transactions
            WHERE account_type IS NOT NULL AND account_type != ''
            GROUP BY account_type
            ORDER BY account_type
        """)
        accounts = []
        for row in cur.fetchall():
            accounts.append({
                'account_type': row[0],
                'transaction_count': row[1],
                'earliest_date': str(row[2]) if row[2] else None,
                'latest_date': str(row[3]) if row[3] else None,
            })
        cur.close()
        conn.close()
        return accounts

    def get_transactions(self, account_type: str = None,
                         start_date: str = None, end_date: str = None,
                         symbol: str = None) -> list:
        """Fetch transactions from the database."""
        conn = self._get_connection()
        cur = conn.cursor(dictionary=True)

        conditions = []
        params = []

        if account_type:
            conditions.append('account_type = %s')
            params.append(account_type)
        if start_date:
            conditions.append('trade_date >= %s')
            params.append(start_date)
        if end_date:
            conditions.append('trade_date <= %s')
            params.append(end_date)
        if symbol:
            conditions.append('symbol = %s')
            params.append(symbol)

        where = ' AND '.join(conditions) if conditions else '1=1'

        sql = """
            SELECT id, symbol, trade_date, type, quantity, price, total,
                   commission, account_type, currency, notes, source_file
            FROM transactions
            WHERE {}
            ORDER BY trade_date ASC, id ASC
        """.format(where)

        cur.execute(sql, params)
        transactions = cur.fetchall()
        cur.close()
        conn.close()
        return transactions

    def export_account(self, account_type: str,
                       start_date: str = None, end_date: str = None) -> str:
        """
        Export a single account's transactions to OFX.

        Args:
            account_type: RRSP, TFSA, MARGIN, etc.
            start_date: Optional filter (YYYY-MM-DD)
            end_date: Optional filter (YYYY-MM-DD)

        Returns:
            Complete OFX 2.2 document as a string.
        """
        transactions = self.get_transactions(
            account_type=account_type,
            start_date=start_date,
            end_date=end_date,
        )
        return self._build_ofx(transactions, account_type)

    def export_all_accounts(self, start_date: str = None,
                            end_date: str = None) -> str:
        """
        Export all accounts into a single OFX file.

        Each account becomes a separate INVSTMTMSGSRSV1 section
        with its own account ID.
        """
        accounts = self.get_accounts()
        all_sections = []

        for acct in accounts:
            acct_type = acct['account_type']
            transactions = self.get_transactions(
                account_type=acct_type,
                start_date=start_date,
                end_date=end_date,
            )
            if transactions:
                section = self._build_statement_section(transactions, acct_type)
                all_sections.append(section)

        # Wrap in OFX envelope
        ofx = OFX_HEADER
        ofx += '<OFX>\n'
        ofx += '  <INVSTMTMSGSRSV1>\n'
        for section in all_sections:
            ofx += section
        ofx += '  </INVSTMTMSGSRSV1>\n'
        ofx += '</OFX>\n'
        return ofx

    def export_to_file(self, filepath: str, account_type: str = None,
                       start_date: str = None, end_date: str = None):
        """
        Export transactions directly to a file.

        Args:
            filepath: Output file path (.ofx or .qfx)
            account_type: Specific account, or None for all
            start_date: Optional filter
            end_date: Optional filter
        """
        if account_type:
            ofx_data = self.export_account(account_type, start_date, end_date)
        else:
            ofx_data = self.export_all_accounts(start_date, end_date)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ofx_data)

        return len(ofx_data)

    def _build_ofx(self, transactions: list, account_type: str) -> str:
        """Build a complete OFX document for a set of transactions."""
        section = self._build_statement_section(transactions, account_type)

        ofx = OFX_HEADER
        ofx += '<OFX>\n'
        ofx += '  <INVSTMTMSGSRSV1>\n'
        ofx += section
        ofx += '  </INVSTMTMSGSRSV1>\n'
        ofx += '</OFX>\n'
        return ofx

    def _build_statement_section(self, transactions: list,
                                  account_type: str) -> str:
        """Build the INVSTMTRS section for one account."""
        if not transactions:
            return ''

        # Date range
        dates = [t['trade_date'] for t in transactions if t.get('trade_date')]
        dtstart = _format_ofx_date(min(dates)) if dates else _format_ofx_date(None)
        dtend = _format_ofx_date(max(dates)) if dates else _format_ofx_date(None)
        dtnow = datetime.now().strftime('%Y%m%d%H%M%S')

        # Account ID — use account type as identifier
        acctid = '{}-INVESTMENT'.format(account_type)

        lines = []
        lines.append('    <INVSTMTRS>')
        lines.append('      <DTASOF>{}</DTASOF>'.format(dtnow))
        lines.append('      <CURDEF>CAD</CURDEF>')
        lines.append('      <INVACCTFROM>')
        lines.append('        <BROKERID>CIBCIE</BROKERID>')
        lines.append('        <ACCTID>{}</ACCTID>'.format(_escape_xml(acctid)))
        lines.append('      </INVACCTFROM>')

        # Transaction list
        lines.append('      <INVTRANLIST>')
        lines.append('        <DTSTART>{}</DTSTART>'.format(dtstart))
        lines.append('        <DTEND>{}</DTEND>'.format(dtend))
        for txn in transactions:
            lines.append(_txn_to_ofx(txn))
        lines.append('      </INVTRANLIST>')

        # Position list (current holdings from latest data)
        positions = self._build_positions(transactions)
        if positions:
            lines.append('      <INVPOSLIST>')
            for pos in positions:
                lines.append(pos)
            lines.append('      </INVPOSLIST>')

        lines.append('    </INVSTMTRS>')
        return '\n'.join(lines) + '\n'

    def _build_positions(self, transactions: list) -> list:
        """Build INVPOS entries from the most recent transactions per symbol.

        This computes current holdings by netting BUY/SELL quantities.
        """
        holdings = {}  # symbol -> {quantity, total_cost, latest_date}

        for txn in transactions:
            symbol = txn.get('symbol', '') or ''
            if not symbol:
                continue

            qty = float(txn.get('quantity', 0) or 0)
            total = float(txn.get('total', 0) or 0)
            txn_type = txn.get('type', '')
            trade_date = txn.get('trade_date')

            if symbol not in holdings:
                holdings[symbol] = {
                    'quantity': 0.0,
                    'total_cost': 0.0,
                    'latest_date': trade_date,
                }

            h = holdings[symbol]

            if txn_type == 'BUY':
                h['quantity'] += qty
                h['total_cost'] += abs(total)
            elif txn_type == 'SELL':
                h['quantity'] -= qty
                h['total_cost'] -= abs(total)
            elif txn_type == 'DIVIDEND_REINVEST':
                h['quantity'] += qty

            if trade_date and (h['latest_date'] is None or trade_date > h['latest_date']):
                h['latest_date'] = trade_date

        positions = []
        for symbol, h in sorted(holdings.items()):
            if h['quantity'] <= 0.001:
                continue

            avg_cost = h['total_cost'] / h['quantity'] if h['quantity'] > 0 else 0

            pos = '        <POSSTOCK>'
            pos += '\n          <SECID>'
            pos += '\n            <UNIQUEID>{}</UNIQUEID>'.format(_escape_xml(symbol))
            pos += '\n            <UNIQUEIDTYPE>TICKER</UNIQUEIDTYPE>'
            pos += '\n          </SECID>'
            pos += '\n          <HELDINACCT>CASH</HELDINACCT>'
            pos += '\n          <POSTYPE>LONG</POSTYPE>'
            pos += '\n          <UNITS>{:.4f}</UNITS>'.format(h['quantity'])
            pos += '\n          <UNITPRICE>{:.4f}</UNITPRICE>'.format(avg_cost)
            pos += '\n          <MKTVAL>{:.2f}</MKTVAL>'.format(h['total_cost'])
            pos += '\n          <DTPRICEASOF>{}</DTPRICEASOF>'.format(
                _format_ofx_date(h['latest_date']))
            pos += '\n        </POSSTOCK>'
            positions.append(pos)

        return positions


# ── CLI ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Export transactions to OFX')
    parser.add_argument('--account', '-a', help='Account type (RRSP, TFSA, MARGIN)')
    parser.add_argument('--start', '-s', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', '-e', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--list', '-l', action='store_true', help='List accounts')
    args = parser.parse_args()

    exporter = OfxExporter()

    if args.list:
        accounts = exporter.get_accounts()
        print('Accounts:')
        for a in accounts:
            print('  {}: {} transactions ({} to {})'.format(
                a['account_type'], a['transaction_count'],
                a['earliest_date'], a['latest_date']))
    elif args.output:
        size = exporter.export_to_file(
            args.output,
            account_type=args.account,
            start_date=args.start,
            end_date=args.end,
        )
        print('Exported {} bytes to {}'.format(size, args.output))
    else:
        # Print to stdout
        if args.account:
            print(exporter.export_account(args.account, args.start, args.end))
        else:
            print(exporter.export_all_accounts(args.start, args.end))
