#!/usr/bin/env python3
"""
Balance dividend transactions against CASH holdings.

Rules:
  - Each DIVIDEND creates a matching DIV-RECV transaction in the same account,
    symbol = CASH-<currency>, same total amount.
  - For orphaned DIVIDENDs (empty account_type), infer account from other
    transactions with the same symbol; if still ambiguous, default to RRSP.
  - Compute running cash balance per account and update portfolio CASH-CAD rows.
"""
import pymysql, pymysql.cursors
from decimal import Decimal
from config_loader import Config
from collections import defaultdict

USER_ID = 2

def get_conn():
    cfg = Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')
    return pymysql.connect(
        host=cfg.data.db_host, user=cfg.data.db_user, password=cfg.db_password,
        database=cfg.data.db_name, port=int(getattr(cfg.data, 'db_port', 3306) or 3306),
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, autocommit=False,
    )

def infer_account(conn, symbol):
    """Find the most common account for a symbol from non-empty account transactions."""
    cur = conn.cursor()
    cur.execute("""
        SELECT account_type, COUNT(*) as n
        FROM transactions
        WHERE user_id = %s AND symbol = %s AND account_type != ''
        GROUP BY account_type ORDER BY n DESC LIMIT 1
    """, (USER_ID, symbol))
    row = cur.fetchone()
    return row['account_type'] if row else 'RRSP'

def main():
    conn = get_conn()
    cur = conn.cursor()
    
    # 1. Update orphaned DIVIDENDs to have accounts (batch)
    cur.execute("""
        SELECT id, symbol, price, total, currency, trade_date, exchange_rate
        FROM transactions
        WHERE user_id = %s AND account_type = '' AND type = 'DIVIDEND'
    """, (USER_ID,))
    orphans = cur.fetchall()
    updated_ids = []
    for t in orphans:
        acct = infer_account(conn, t['symbol'])
        cur.execute("UPDATE transactions SET account_type = %s WHERE id = %s", (acct, t['id']))
        updated_ids.append(t['id'])
    print(f"Updated {len(orphans)} orphaned DIVIDENDs with inferred accounts")
    conn.commit()
    
    # 2. Bulk fetch all DIVIDENDs + existing DIV-RECVs to avoid per-row check
    cur.execute("""
        SELECT id, symbol, account_type, price, total, currency, trade_date, exchange_rate
        FROM transactions
        WHERE user_id = %s AND type = 'DIVIDEND'
        ORDER BY trade_date ASC, id ASC
    """, (USER_ID,))
    dividends = cur.fetchall()
    print(f"Found {len(dividends)} DIVIDEND transactions")
    
    cur.execute("""
        SELECT trade_date, account_type, symbol, total FROM transactions
        WHERE user_id = %s AND type = 'DIV-RECV'
    """, (USER_ID,))
    existing_keys = set((r['trade_date'], r['account_type'], r['symbol'], r['total']) for r in cur.fetchall())
    
    to_insert = []
    for d in dividends:
        ccy = d['currency'] or 'CAD'
        cash_symbol = f"CASH-{ccy}"
        key = (d['trade_date'], d['account_type'], cash_symbol, d['total'])
        if key in existing_keys:
            continue
        to_insert.append((
            USER_ID, cash_symbol, d['trade_date'], 'DIV-RECV', 1,
            d['price'], d['total'], 0,
            d['account_type'], ccy,
            d.get('exchange_rate', 1.0) or 1.0,
            f"Balanced against DIVIDEND {d['symbol']} on {d['trade_date']}",
            'div_balance', 0,
        ))
    
    if to_insert:
        cur.executemany("""
            INSERT INTO transactions
                (user_id, symbol, trade_date, type, quantity, price, total, commission, account_type, currency, exchange_rate, notes, source_file, source_line)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, to_insert)
        conn.commit()
    print(f"Inserted {len(to_insert)} new DIV-RECV transactions")
    
    # 3. Compute cash balances per account/currency
    cur.execute("""
        SELECT account_type, currency,
               SUM(CASE WHEN type = 'BUY' THEN -total ELSE total END) as delta
        FROM transactions
        WHERE user_id = %s AND (type IN ('DIVIDEND','TRANSFER','FEE','BUY','SELL') OR type = '')
        GROUP BY account_type, currency
    """, (USER_ID,))
    balances = cur.fetchall()
    print(f"\nCash balances (by account, currency):")
    cash_updates = 0
    for b in balances:
        delta = float(b['delta'])
        acct = b['account_type']
        ccy = b['currency']
        print(f"  {acct} | {ccy} | {delta:,.2f}")
        if abs(delta) < 0.005:
            continue
        symbol = f"CASH-{ccy}"
        cur.execute("DELETE FROM portfolio WHERE user_id = %s AND account_type = %s AND symbol = %s",
                    (USER_ID, acct, symbol))
        cur.execute("""
            INSERT INTO portfolio (user_id, symbol, price_symbol, account_type, shares, cost_basis, cost_basis_total, currency, entry_date, strategy, notes, updated_at, stop_loss_pct, atr_multiplier)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '1997-01-01', 'CASH', 'Auto-balanced cash position', NOW(), 0.15, 2.0)
        """, (USER_ID, symbol, symbol, acct, round(abs(delta), 2), 1.0, round(abs(delta), 2), ccy))
        cash_updates += 1
    conn.commit()
    print(f"Updated {cash_updates} CASH portfolio entries")
    
    # 4. Verify
    cur.execute("""
        SELECT account_type, symbol, shares, cost_basis, cost_basis_total, currency
        FROM portfolio WHERE user_id = %s AND symbol LIKE 'CASH%%'
        ORDER BY account_type, symbol
    """, (USER_ID,))
    rows = cur.fetchall()
    print(f"\nFinal CASH portfolio entries: {len(rows)}")
    for r in rows:
        print(f"  {r['account_type']} | {r['symbol']} | {r['shares']} shares | {r['currency']}")
    conn.close()

if __name__ == '__main__':
    main()
