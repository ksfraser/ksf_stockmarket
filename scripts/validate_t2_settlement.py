#!/usr/bin/env python3
"""
T+2 settlement validation.

Inserts 4 synthetic transactions for a test user and walks day-by-day
through the settlement window to assert cash balances.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('PYTHONPATH', '.:python:python/src')

from python.db_connector import get_connection

logger = logging.getLogger('validate_t2')


def _next_business_day(start: date, days: int) -> date:
    cur = start
    added = 0
    while added < days:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            added += 1
    return cur


def _cash_balance(conn, user_id: int, as_of: date) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(total), 0)
            FROM transactions
            WHERE user_id = %s
              AND symbol = 'CASH'
              AND account_type = 'portfolio'
              AND trade_date <= %s
            """,
            (user_id, as_of.isoformat()),
        )
        row = cur.fetchone()
        return float(row[0] if row and row[0] is not None else 0)


def _insert(conn, user_id: int, trade_date: date, typ: str, symbol: str, quantity: int, price: float, total: float, account_type: str, notes: str = '') -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO transactions
                (user_id, symbol, trade_date, type, quantity, price, total, commission, account_type, notes, source_file, settlement_date, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s, 't2_validation', %s, NOW())
            """,
            (user_id, symbol, trade_date.isoformat(), typ, quantity, price, total, account_type, notes, trade_date.isoformat()),
        )


def main() -> int:
    uid = 9998
    trade_date = date(2026, 7, 27)  # Monday
    price = 10.0
    shares = 10
    commission = 9.99
    cost = shares * price + commission
    settlement = _next_business_day(trade_date, 2)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    conn = get_connection()
    if not conn:
        print('NO_DB')
        return 1

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM transactions WHERE user_id = %s AND symbol IN ('CASH','TEST2')", (uid,))
            cur.execute("DELETE FROM advisor_recommendations WHERE user_id = %s", (uid,))
            conn.commit()

        start = _cash_balance(conn, uid, trade_date - timedelta(days=1))
        logger.info('Start cash T-1: $%.2f', start)

        # BUY 10 shares at $10 + $9.99 commission = $109.90 total
        _insert(conn, uid, trade_date, 'BUY', 'CASH', 0, price, -cost, 'accrual', f'TEST2 buy cash hold ({trade_date})')
        _insert(conn, uid, trade_date, 'BUY', 'CASH', 0, price, -cost, 'portfolio', f'TEST2 buy reserve ({trade_date})')
        _insert(conn, uid, settlement, 'BUY', 'CASH', 0, price, cost, 'accrual', f'TEST2 buy settlement ({settlement})')
        _insert(conn, uid, settlement, 'BUY', 'TEST2', 1, price, price, 'portfolio', f'TEST2 buy completed ({settlement})')
        conn.commit()

        t0 = _cash_balance(conn, uid, trade_date)
        t1 = _cash_balance(conn, uid, settlement - timedelta(days=1))
        t2 = _cash_balance(conn, uid, settlement)

        logger.info('T+0 cash: $%.2f', t0)
        logger.info('T+1 cash: $%.2f', t1)
        logger.info('T+2 cash: $%.2f', t2)

        # With 0 start cash, T+0/T+1 should still be 0 (negative not allowed)
        assert t0 == start, f'T+0 expected {start}, got {t0}'
        assert t1 == start, f'T+1 expected {start}, got {t1}'
        # T+2: accrual +$109.90 cancels portfolio -$109.90, net still 0 because shares came in
        assert t2 == start, f'T+2 expected {start}, got {t2}'

        logger.info('PASS: T+2 cash math is correct for zero-start')
        return 0
    except AssertionError as e:
        logger.error('FAIL: %s', e)
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
