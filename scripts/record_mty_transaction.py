#!/usr/bin/env python3
"""
Portfolio transaction recorder — run once MariaDB is available.
Records: 25 MTY @ $39.47 RRSP, trailing stop $4 below high-water mark.
Also creates an alert for the trailing stop.
"""

TRANSACTION = {
    'symbol': 'MTY.TO',
    'action': 'BUY',
    'shares': 25,
    'price': 39.47,
    'commission': 9.95,
    'account_type': 'RRSP',
    'user_id': 2,  # kevin
    'notes': 'Trailing stop $4 below high-water mark',
}

TRAILING_STOP = {
    'symbol': 'MTY.TO',
    'type': 'TRAILING_STOP',
    'trail_amount': 4.00,  # $4 below highest price since entry
    'entry_price': 39.47,
    'reference_price': 39.47,  # Initial reference (high-water mark)
}

def record_transaction(conn):
    """Record the portfolio transaction in MariaDB."""
    from datetime import date

    total_cost = TRANSACTION['shares'] * TRANSACTION['price'] + TRANSACTION['commission']

    cursor = conn.cursor()

    # 1. Insert or update portfolio position
    cursor.execute("""
        INSERT INTO portfolio
            (user_id, symbol, shares, cost_basis, cost_total,
             account_type, acquisition_date, is_active, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)
        ON DUPLICATE KEY UPDATE
            shares = shares + VALUES(shares),
            cost_total = cost_total + VALUES(cost_total),
            cost_basis = cost_total / shares
    """, (
        TRANSACTION['user_id'],
        TRANSACTION['symbol'],
        TRANSACTION['shares'],
        TRANSACTION['price'],
        total_cost,
        TRANSACTION['account_type'],
        date.today(),
        TRANSACTION['notes'],
    ))

    # 2. Insert into user_trades
    cursor.execute("""
        INSERT INTO user_trades
            (user_id, symbol, action, shares, price, commission,
             total_amount, account_type, trade_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        TRANSACTION['user_id'],
        TRANSACTION['symbol'],
        TRANSACTION['action'],
        TRANSACTION['shares'],
        TRANSACTION['price'],
        TRANSACTION['commission'],
        total_cost,
        TRANSACTION['account_type'],
        date.today(),
        TRANSACTION['notes'],
    ))

    # 3. Create trailing stop alert
    # Alert triggers when price drops $4 below current (will update as price rises)
    trigger_price = TRAILING_STOP['entry_price'] - TRAILING_STOP['trail_amount']
    cursor.execute("""
        INSERT INTO alerts
            (symbol, alert_type, threshold_value, comparison,
             secondary_value, is_active)
        VALUES (%s, 'TRAILING_STOP', %s, 'LTE', %s, 1)
        ON DUPLICATE KEY UPDATE
            threshold_value = VALUES(threshold_value),
            secondary_value = VALUES(secondary_value),
            is_active = 1
    """, (
        TRAILING_STOP['symbol'],
        trigger_price,         # Current trigger price
        TRAILING_STOP['trail_amount'],  # Trail amount in secondary
    ))

    conn.commit()
    cursor.close()

    print(f"✅ Recorded: {TRANSACTION['action']} {TRANSACTION['shares']} "
          f"{TRANSACTION['symbol']} @ ${TRANSACTION['price']:.2f} "
          f"(total: ${total_cost:.2f}) [{TRANSACTION['account_type']}]")
    print(f"✅ Trailing stop alert: {TRAILING_STOP['symbol']} "
          f"triggers at ${trigger_price:.2f} "
          f"(${TRAILING_STOP['trail_amount']:.2f} below entry)")
    print()
    print("NOTE: Trailing stop reference price will be updated automatically")
    print("when the price rises. The alert firing resets the trigger upward.")


if __name__ == '__main__':
    import sys
    from python.db_connector import get_connection

    try:
        conn = get_connection()
        record_transaction(conn)
        conn.close()
    except Exception as e:
        print(f"ERROR: Could not connect to MariaDB: {e}")
        print("Transaction saved to this file — run again when DB is available.")
        sys.exit(1)
