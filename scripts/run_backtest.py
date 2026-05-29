#!/usr/bin/env python3
"""
run_backtest.py — SQLite-compatible backtest runner
===================================================
Runs the existing BacktestEngine against our dev SQLite DB.
Handles MySQL→SQLite differences in date handling and SQL.

Usage:
  python3 run_backtest.py                          # 2020-2024, all symbols
  python3 run_backtest.py --start 2015-01-01       # Custom start
  python3 run_backtest.py --symbols RY.TO,TD.TO    # Specific symbols
  python3 run_backtest.py --strategy motley_fool   # Different strategy
"""

import sys
import os
import sqlite3
import argparse
from datetime import date, datetime

# Force SQLite backend
os.environ['DB_BACKEND'] = 'sqlite'
os.environ['SQLITE_PATH'] = os.path.join(os.path.dirname(__file__), '..', 'analysis_results.db')

sys.path.insert(0, os.path.dirname(__file__))
from python.db_connector import get_connection


def get_symbols_with_data(conn, start_date, end_date, min_days=500):
    """Get symbols that have sufficient data in the date range."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, COUNT(*) as n_days
        FROM stockprices
        WHERE price_date >= ? AND price_date <= ?
        GROUP BY symbol
        HAVING n_days >= ?
        ORDER BY symbol
    """, (start_date.isoformat(), end_date.isoformat(), min_days))
    return [row[0] for row in cursor.fetchall()]


def adapt_for_sqlite(conn):
    """
    Patch sqlite3 date handling for the backtest engine.
    Register adapters so dates come through correctly.
    """
    import sqlite3
    # Register date adapter
    sqlite3.register_adapter(date, lambda d: d.isoformat())
    sqlite3.register_converter("DATE", lambda s: date.fromisoformat(s.decode()))
    sqlite3.register_converter("date", lambda s: date.fromisoformat(s.decode()))


def main():
    parser = argparse.ArgumentParser(description='Run backtest against SQLite portfolio data')
    parser.add_argument('--strategy', default='combined',
                        choices=['combined', 'motley_fool', 'buffett', 'turtle'])
    parser.add_argument('--start', default='2020-01-01')
    parser.add_argument('--end', default='2024-12-31')
    parser.add_argument('--initial', type=float, default=100000.0)
    parser.add_argument('--commission', type=float, default=9.95)
    parser.add_argument('--max-position', type=float, default=0.01)
    parser.add_argument('--frequency', default='monthly',
                        choices=['weekly', 'monthly', 'quarterly', 'semi_annual'])
    parser.add_argument('--symbols', nargs='*')
    parser.add_argument('--show-trades', action='store_true')

    args = parser.parse_args()
    start = datetime.strptime(args.start, '%Y-%m-%d').date()
    end = datetime.strptime(args.end, '%Y-%m-%d').date()

    conn = get_connection()
    adapt_for_sqlite(conn)

    # Get universe
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = get_symbols_with_data(conn, start, end)
        if not symbols:
            print("❌ No symbols found with sufficient data in date range")
            print("   Try: python3 run_backtest.py --start 2015-01-01")
            conn.close()
            sys.exit(1)

    print(f"📊 Backtest Configuration")
    print(f"   Strategy:  {args.strategy}")
    print(f"   Period:    {start} → {end}")
    print(f"   Capital:   ${args.initial:,.2f}")
    print(f"   Commission: ${args.commission:.2f}")
    print(f"   Frequency: {args.frequency}")
    print(f"   Max pos:   {args.max_position*100:.1f}%")
    print(f"   Universe:  {len(symbols)} symbols")
    print(f"   Symbols:   {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")

    # Build the engine
    from python.backtest_engine import BacktestEngine, DEFAULT_INITIAL_CAPITAL

    engine = BacktestEngine(
        conn=conn,
        strategy=args.strategy,
        start_date=start,
        end_date=end,
        initial_capital=args.initial,
        commission=args.commission,
        max_position_pct=args.max_position,
        frequency=args.frequency,
        symbols=symbols,
    )

    results = engine.run()

    if args.show_trades and results.get('trades'):
        print(f"\n📋 TRADES")
        for t in results['trades'][:20]:
            print(f"   {t['trade_date']} {t['trade_type']:4s} {t['quantity']:>6,} {t['symbol']:8s} "
                  f"@ ${t['price']:>8.2f}  ${t['total_cost']:>10,.2f}")
        if len(results['trades']) > 20:
            print(f"   ... and {len(results['trades']) - 20} more trades")

    conn.close()


if __name__ == '__main__':
    main()
