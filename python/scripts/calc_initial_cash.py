#!/usr/bin/env python3
"""
Calculate initial cash transfer-in values from November PDF statements.

Formula:
  initial_cash = November_opening_cash - sum(transaction_impacts_before_statement)

Where:
  - impact = -total for BUY (cash out), +total for all other types
  - excludes 1997-01-01 dummy BUYs and 0000-00-00 entries
  - uses only DIVIDEND (not DIV-RECV) to avoid double-counting dividends
  - requires a November statement in cache for the account
"""

import pymysql, pymysql.cursors
from decimal import Decimal
from config_loader import Config

USER_ID = 2

# November statement opening cash balances (CAD-only statements)
NOV_OPENING = {
    'RRSP': Decimal('18654.57'),   # rrsp_statements/2024_11_eStatements.txt
    'TFSA': Decimal('1698.91'),    # tfsa_statements/2025_11_eStatements.txt
    # MARGIN: no November statement found in cache
}

def get_conn():
    cfg = Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')
    return pymysql.connect(
        host=cfg.data.db_host, user=cfg.data.db_user, password=cfg.db_password,
        database=cfg.data.db_name, port=int(getattr(cfg.data, 'db_port', 3306) or 3306),
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
    )

def main():
    conn = get_conn()
    cur = conn.cursor()

    for acct, opening in NOV_OPENING.items():
        cutoff = '2024-11-01' if acct == 'RRSP' else '2025-11-01'

        cur.execute("""
            SELECT type, currency,
                   SUM(CASE WHEN type = 'BUY' THEN -total ELSE total END) as delta
            FROM transactions
            WHERE user_id = %s
              AND account_type = %s
              AND trade_date < %s
              AND trade_date NOT IN ('0000-00-00', '1997-01-01')
              AND type != 'DIV-RECV'
            GROUP BY type, currency
            ORDER BY type, currency
        """, (USER_ID, acct, cutoff))
        rows = cur.fetchall()

        print(f"\n{acct} transaction impacts before {cutoff}:")
        total_by_ccy = {}
        for r in rows:
            print(f"  {r['type']:12s} | {r['currency']} | {r['delta']:>12,.2f}")
            ccy = r['currency']
            total_by_ccy[ccy] = total_by_ccy.get(ccy, Decimal('0')) + r['delta']

        print(f"  Net impacts by currency: {total_by_ccy}")
        print(f"  November opening cash: {opening:,.2f}")

        for ccy, net in total_by_ccy.items():
            init = opening - net
            print(f"  Initial {acct} cash {ccy}: {init:>12,.2f}")
            symbol = f"CASH-{ccy}"
            shares = round(abs(init), 2)
            cur.execute(
                "DELETE FROM portfolio WHERE user_id=%s AND account_type=%s AND symbol=%s",
                (USER_ID, acct, symbol)
            )
            cur.execute("""
                INSERT INTO portfolio (user_id, symbol, price_symbol, account_type, shares,
                    cost_basis, cost_basis_total, currency, entry_date, strategy, notes,
                    updated_at, stop_loss_pct, atr_multiplier)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '1997-01-01', 'CASH',
                    'Initial cash xfer-in from November opening balance reconciliation', NOW(), 0.15, 2.0)
            """, (USER_ID, symbol, symbol, acct, shares, 1.0, shares, ccy))
            print(f"  -> Portfolio {acct} {symbol} set to {shares} shares")

    conn.commit()
    conn.close()
    print("\nDone.")

if __name__ == '__main__':
    main()
