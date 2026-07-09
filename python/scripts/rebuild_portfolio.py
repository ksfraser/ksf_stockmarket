#!/usr/bin/env python3
"""
Rebuild portfolio from the most recent holdings statement (May 15, 2026).
For any holding that cannot be explained by existing transactions, insert
a dummy BUY transaction dated 1997-01-01 so the transaction log balances.

Strategy:
  1. Parse holdings_may15_2026.csv (RRSP + Investment + TFSA)
  2. Compute expected shares from existing DB transactions (only BUY -> +shares,
     SELL -> -shares).
  3. Compare statement quantity vs transaction-derived quantity.
  4. For shortfalls, insert dummy BUY transactions (trade_date = 1997-01-01).
  5. Clear portfolio for user 2 and rebuild by replaying all transactions
     (including dummies) through BUY/SELL logic.
"""
import csv
import pymysql
import pymysql.cursors
from decimal import Decimal
from config_loader import Config
from datetime import date, datetime

USER_ID = 2
STATEMENT_PATH = '/root/.hermes/cache/holdings_may15_2026.csv'
DUMMY_DATE = '1997-01-01'

ACCOUNT_MAP = {
    '59154498 RRSP': 'RRSP',
    '57165131 Investment': 'MARGIN',
    '60146926 TFSA': 'TFSA',
}

def parse_statement(path):
    accounts = {}
    current_account = None
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)
    i = 0
    while i < len(rows):
        row = rows[i]
        if len(row) >= 1 and any(row[0].startswith(k) for k in ACCOUNT_MAP):
            for k, v in ACCOUNT_MAP.items():
                if row[0].startswith(k):
                    current_account = v
                    break
            i += 1
            continue
        if current_account and len(row) >= 13 and row[0] == 'Asset type':
            j = i + 1
            while j < len(rows) and rows[j][0] not in ('', '--') and len(rows[j]) >= 13:
                data = rows[j]
                if data[2]:
                    symbol = data[2].strip()
                    qty_raw = data[5].replace(',', '').strip()
                    avg_cost_raw = data[6].replace(',', '').strip()
                    try:
                        qty = Decimal(qty_raw)
                        avg_cost = Decimal(avg_cost_raw)
                        if qty > 0:
                            accounts.setdefault(current_account, {})[symbol] = {
                                'quantity': qty,
                                'cost_basis': avg_cost,
                                'cost_basis_total': (qty * avg_cost).quantize(Decimal('0.01')),
                            }
                    except Exception:
                        pass
                j += 1
            i = j
            continue
        i += 1
    return accounts


def get_db_transactions(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, symbol, account_type, type, quantity, price, total, trade_date
        FROM transactions
        WHERE user_id = %s AND is_deleted = 0 AND trade_date != '0000-00-00'
        ORDER BY trade_date ASC, id ASC
    """, (USER_ID,))
    return cur.fetchall()


def compute_holdings(transactions):
    holdings = {}
    for t in transactions:
        sym = (t['symbol'] or '').strip().upper()
        acct = (t['account_type'] or '').strip().upper()
        typ = (t['type'] or '').strip().upper()
        qty = float(t['quantity'] or 0)
        if typ == 'BUY':
            holdings[(acct, sym)] = holdings.get((acct, sym), 0) + qty
        elif typ == 'SELL':
            holdings[(acct, sym)] = holdings.get((acct, sym), 0) - qty
    return holdings


def insert_dummy_transaction(cur, account, symbol, quantity, price):
    total = (Decimal(str(quantity)) * Decimal(str(price))).quantize(Decimal('0.01'))
    sql = """
        INSERT INTO transactions
            (user_id, symbol, trade_date, type, quantity, price, total, commission, account_type, currency, notes, source_file, source_line)
        VALUES
            (%s, %s, %s, 'BUY', %s, %s, %s, 0, %s, 'CAD', 'Dummy record to balance portfolio vs May 15 2026 statement', 'rebuild_1997', 0)
    """
    cur.execute(sql, (USER_ID, symbol, DUMMY_DATE, quantity, price, float(total), account))


def rebuild_portfolio(conn, transactions):
    cur = conn.cursor()
    cur.execute("DELETE FROM portfolio WHERE user_id = %s", (USER_ID,))
    positions = {}

    for t in transactions:
        acct = (t['account_type'] or '').strip().upper()
        sym = (t['symbol'] or '').strip().upper()
        typ = (t['type'] or '').strip().upper()
        if not sym:
            continue
        key = (acct, sym)

        if typ == 'BUY':
            qty = float(t['quantity'] or 0)
            price = float(t['price'] or 0)
            cost = qty * price
            if key not in positions:
                positions[key] = {
                    'shares': qty,
                    'cost_basis': price,
                    'cost_basis_total': cost,
                }
            else:
                old = positions[key]
                new_shares = old['shares'] + qty
                new_cb = ((old['shares'] * old['cost_basis']) + cost) / new_shares
                old['shares'] = new_shares
                old['cost_basis'] = new_cb
                old['cost_basis_total'] = new_shares * new_cb
        elif typ == 'SELL':
            qty = float(t['quantity'] or 0)
            if key in positions:
                old = positions[key]
                new_shares = old['shares'] - qty
                if new_shares <= 0.001:
                    del positions[key]
                else:
                    old['shares'] = new_shares
                    old['cost_basis_total'] = new_shares * old['cost_basis']

    ins_sql = """
        INSERT INTO portfolio
            (user_id, symbol, price_symbol, account_type, shares, cost_basis, cost_basis_total, entry_date, strategy, notes, updated_at, stop_loss_pct, atr_multiplier)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, 'Rebuilt', 'Rebuilt from transactions + dummies on 2026-06-28', NOW(), 0.15, 2.0)
    """
    ins = conn.cursor()
    for (acct, sym), pos in positions.items():
        price_sym = sym if not sym.endswith('.TO') else sym
        ins.execute(ins_sql, (
            USER_ID, sym, price_sym, acct,
            round(pos['shares'], 2), round(pos['cost_basis'], 4), round(pos['cost_basis_total'], 2),
            DUMMY_DATE,
        ))
    return len(positions)


def main():
    cfg = Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')
    conn = pymysql.connect(
        host=cfg.data.db_host,
        user=cfg.data.db_user,
        password=cfg.db_password,
        database=cfg.data.db_name,
        port=int(getattr(cfg.data, 'db_port', 3306) or 3306),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )

    print("Parsing May 15 2026 statement...")
    target = parse_statement(STATEMENT_PATH)
    for acct, holdings in target.items():
        print(f"\n{acct} target holdings: {len(holdings)} symbols")
        for sym, data in holdings.items():
            print(f"  {sym}: qty={data['quantity']} cb={data['cost_basis']}")

    transactions = get_db_transactions(conn)
    tx_holdings = compute_holdings(transactions)
    print(f"\nExisting DB transactions: {len(transactions)}")
    print(f"Transaction-derived holdings: {len(tx_holdings)} positions")

    with conn.cursor() as cur:
        dummy_count = 0
        for acct, holdings in target.items():
            for sym, data in holdings.items():
                key = (acct, sym.upper())
                tx_qty = tx_holdings.get(key, 0)
                stmt_qty = float(data['quantity'])
                if abs(stmt_qty - tx_qty) > 0.001:
                    shortfall = stmt_qty - tx_qty
                    if shortfall > 0:
                        print(f"\nDUMMY: {acct} {sym} +{shortfall} shares @ {data['cost_basis']}")
                        insert_dummy_transaction(cur, acct, sym, shortfall, data['cost_basis'])
                        dummy_count += 1
                    else:
                        print(f"\nWARNING: {acct} {sym} over-transacted by {-shortfall} shares (statement={stmt_qty}, tx={tx_qty})")
                else:
                    print(f"OK: {acct} {sym} qty={stmt_qty} matches tx qty={tx_qty}")

        conn.commit()
        print(f"\nInserted {dummy_count} dummy transactions dated {DUMMY_DATE}")

    transactions = get_db_transactions(conn)
    print("\nRebuilding portfolio...")
    inserted = rebuild_portfolio(conn, transactions)
    conn.commit()
    print(f"Portfolio rebuilt: {inserted} rows")

    cur = conn.cursor()
    cur.execute("SELECT account_type, symbol, shares, cost_basis, cost_basis_total FROM portfolio WHERE user_id = %s ORDER BY account_type, symbol", (USER_ID,))
    rows = cur.fetchall()
    print(f"\nFinal portfolio entries: {len(rows)}")
    for r in rows:
        print(f"  {r['account_type']} | {r['symbol']} | {r['shares']} shares | cb={r['cost_basis']} | cbt={r['cost_basis_total']}")
    conn.close()


if __name__ == '__main__':
    main()
