#!/usr/bin/env python3
"""
backtest_engine.py — Strategy Backtesting Engine
===================================================
Simulates trading strategies over historical data with configurable:
- Entry/exit signals (from TA indicators + scoring tables)
- Rebalancing frequency (weekly, monthly, quarterly, semi-annual)
- Position sizing (fixed, percent of portfolio)
- Commission structure ($9.95/trade)
- Benchmark comparison (TSX Composite)

Usage:
  python3 backtest_engine.py --strategy combined --start 2020-01-01 --end 2024-12-31
  python3 backtest_engine.py --strategy motley_fool --frequency monthly --initial 100000
"""

import argparse
import json
import logging
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from python.db_connector import get_connection, get_active_symbols, fetch_price_data
from python.ta_calculator import compute_indicators, compute_signal_strength, compute_signal_reasons

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Default backtest parameters
DEFAULT_INITIAL_CAPITAL = 100000.00
DEFAULT_COMMISSION = 9.95
DEFAULT_MAX_POSITION_PCT = 0.01  # 1% max per trade
REBALANCE_FREQUENCIES = {
    'weekly': 7,
    'monthly': 30,
    'quarterly': 91,
    'semi_annual': 182,
}


class BacktestEngine:
    """Runs a backtest for a single strategy."""

    def __init__(self, conn, strategy: str, start_date: date, end_date: date,
                 initial_capital: float = DEFAULT_INITIAL_CAPITAL,
                 commission: float = DEFAULT_COMMISSION,
                 max_position_pct: float = DEFAULT_MAX_POSITION_PCT,
                 frequency: str = 'monthly', symbols: list = None):
        self.conn = conn
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.commission = commission
        self.max_position_pct = max_position_pct
        self.frequency = frequency
        self.rebalance_interval = REBALANCE_FREQUENCIES[frequency]
        self.symbols = symbols or []

        # State
        self.cash = initial_capital
        self.positions = {}  # symbol -> {shares, cost_basis, entry_date}
        self.trades = []  # list of trade dicts
        self.portfolio_history = []  # daily snapshots
        self.current_date = start_date

    def get_universe(self) -> list:
        """Get the symbol universe for this backtest."""
        if self.symbols:
            return self.symbols

        cursor = self.conn.cursor()
        # Get symbols that have data for the entire backtest period
        cursor.execute("""
            SELECT symbol FROM stockprices
            WHERE price_date BETWEEN %s AND %s
            GROUP BY symbol
            HAVING COUNT(DISTINCT price_date) >= %s
            ORDER BY symbol
        """, (self.start_date, self.end_date,
              (self.end_date - self.start_date).days * 0.7))  # At least 70% of trading days

        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return symbols

    def get_price_on_date(self, symbol: str, target_date: date) -> dict:
        """Get the price for a symbol on a specific date."""
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT day_open, day_high, day_low, day_close, volume
            FROM stockprices
            WHERE symbol = %s AND price_date = %s
        """, (symbol, target_date))
        row = cursor.fetchone()
        cursor.close()
        return row

    def get_prices_range(self, symbol: str, from_date: date, to_date: date) -> list:
        """Get price data for a symbol over a date range."""
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT price_date, day_open, day_high, day_low, day_close, volume
            FROM stockprices
            WHERE symbol = %s AND price_date BETWEEN %s AND %s
            ORDER BY price_date ASC
        """, (symbol, from_date, to_date))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def is_rebalance_day(self, current_date: date, last_rebalance: date) -> bool:
        """Check if today is a rebalance day."""
        days_since = (current_date - last_rebalance).days
        return days_since >= self.rebalance_interval

    def generate_signals(self, symbol: str, as_of_date: date) -> dict:
        """
        Generate trading signals for a symbol as of a specific date.
        Returns dict with 'signal' (BUY/SELL/HOLD), 'strength', 'reasons'.

        For backtesting, we compute indicators from historical data up to as_of_date.
        This simulates what the system would have seen on that date.
        """
        # Fetch historical data up to this date
        from pandas import DataFrame
        import pandas as pd

        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT price_date, day_open, day_high, day_low, day_close, volume
            FROM stockprices
            WHERE symbol = %s AND price_date <= %s
            ORDER BY price_date ASC
            LIMIT 250
        """, (symbol, as_of_date))
        rows = cursor.fetchall()
        cursor.close()

        if len(rows) < 200:
            return {'signal': 'HOLD', 'strength': 0, 'reasons': 'insufficient_data'}

        df = DataFrame(rows)
        df['price_date'] = pd.to_datetime(df['price_date'])
        df.set_index('price_date', inplace=True)

        # Compute indicators
        ta_results = compute_indicators(df, symbol)

        if not ta_results:
            return {'signal': 'HOLD', 'strength': 0, 'reasons': 'no_indicators'}

        # Get scoring data if available
        score_bonus = 0
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT totalscore FROM evalsummary WHERE symbol = %s
            """, (symbol,))
            score_row = cursor.fetchone()
            cursor.close()
            if score_row and score_row.get('totalscore'):
                # Add score bonus: +10 for each 5 points above 20
                score_bonus = max(0, (score_row['totalscore'] - 20) / 5 * 10)
        except Exception:
            pass

        strength = compute_signal_strength(ta_results, 'UNKNOWN') + score_bonus
        reasons = compute_signal_reasons(ta_results, 'UNKNOWN')

        if strength > 20:
            signal = 'BUY'
        elif strength < -20:
            signal = 'SELL'
        else:
            signal = 'HOLD'

        return {
            'signal': signal,
            'strength': strength,
            'reasons': reasons,
            'indicators': ta_results,
        }

    def execute_trade(self, symbol: str, trade_type: str, price: float,
                      date: date, reason: str = '') -> bool:
        """Execute a trade (BUY or SELL)."""
        if trade_type == 'BUY':
            # Calculate position size
            max_investment = self.cash * self.max_position_pct
            shares = int(max_investment / price)
            if shares <= 0:
                return False

            cost = shares * price + self.commission
            if cost > self.cash:
                # Reduce shares to fit budget
                shares = int((self.cash - self.commission) / price)
                if shares <= 0:
                    return False
                cost = shares * price + self.commission

            # Execute
            if symbol in self.positions:
                # Add to existing position
                pos = self.positions[symbol]
                total_shares = pos['shares'] + shares
                total_cost = pos['shares'] * pos['cost_basis'] + shares * price
                pos['shares'] = total_shares
                pos['cost_basis'] = total_cost / total_shares
            else:
                self.positions[symbol] = {
                    'shares': shares,
                    'cost_basis': price,
                    'entry_date': date,
                }

            self.cash -= cost

            self.trades.append({
                'symbol': symbol,
                'trade_type': 'BUY',
                'trade_date': date,
                'price': price,
                'quantity': shares,
                'commission': self.commission,
                'total_cost': cost,
                'signal_reasons': reason,
            })

            logger.debug(f"  BUY {shares} {symbol} @ ${price:.2f} = ${cost:.2f}")
            return True

        elif trade_type == 'SELL':
            if symbol not in self.positions:
                return False

            pos = self.positions[symbol]
            shares = pos['shares']
            proceeds = shares * price - self.commission

            # Compute P&L
            cost_basis_total = shares * pos['cost_basis']
            pnl = proceeds - cost_basis_total

            self.cash += proceeds

            self.trades.append({
                'symbol': symbol,
                'trade_type': 'SELL',
                'trade_date': date,
                'price': price,
                'quantity': shares,
                'commission': self.commission,
                'total_cost': -proceeds,
                'signal_reasons': reason,
                'pnl': pnl,
            })

            del self.positions[symbol]
            logger.debug(f"  SELL {shares} {symbol} @ ${price:.2f} = ${proceeds:.2f} (P&L: ${pnl:.2f})")
            return True

        return False

    def compute_portfolio_value(self, as_of_date: date) -> dict:
        """Compute total portfolio value as of a date."""
        total_value = self.cash
        position_values = {}

        for symbol, pos in self.positions.items():
            price_data = self.get_price_on_date(symbol, as_of_date)
            if price_data:
                current_price = price_data['day_close']
                market_value = pos['shares'] * current_price
                unrealized_pnl = market_value - (pos['shares'] * pos['cost_basis'])
                total_value += market_value
                position_values[symbol] = {
                    'shares': pos['shares'],
                    'cost_basis': pos['cost_basis'],
                    'current_price': current_price,
                    'market_value': market_value,
                    'unrealized_pnl': unrealized_pnl,
                }

        return {
            'date': as_of_date,
            'cash': self.cash,
            'total_value': total_value,
            'positions': position_values,
            'num_positions': len(self.positions),
        }

    def run(self) -> dict:
        """Run the backtest."""
        universe = self.get_universe()
        logger.info(f"Backtest: {self.strategy} | {self.start_date} to {self.end_date}")
        logger.info(f"  Universe: {len(universe)} symbols")
        logger.info(f"  Initial capital: ${self.initial_capital:,.2f}")
        logger.info(f"  Commission: ${self.commission:.2f}")
        logger.info(f"  Frequency: {self.frequency}")
        logger.info(f"  Max position: {self.max_position_pct*100:.1f}%")

        # Get all trading dates in range
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT price_date FROM stockprices
            WHERE price_date BETWEEN %s AND %s
            ORDER BY price_date ASC
        """, (self.start_date, self.end_date))
        trading_dates = [row[0] for row in cursor.fetchall()]
        cursor.close()

        if not trading_dates:
            logger.error("No trading dates found in range")
            return {}

        logger.info(f"  Trading days: {len(trading_dates)}")

        last_rebalance = self.start_date - timedelta(days=self.rebalance_interval + 1)

        for i, current_date in enumerate(trading_dates):
            # Check rebalance day
            if self.is_rebalance_day(current_date, last_rebalance):
                last_rebalance = current_date
                logger.info(f"  Rebalance: {current_date} ({i+1}/{len(trading_dates)})")

                # Generate signals for all symbols
                buy_signals = []
                sell_signals = []

                for symbol in universe:
                    signals = self.generate_signals(symbol, current_date)
                    if signals['signal'] == 'BUY' and signals['strength'] > 30:
                        buy_signals.append((symbol, signals['strength'], signals['reasons']))
                    elif signals['signal'] == 'SELL':
                        sell_signals.append((symbol, signals['strength'], signals['reasons']))

                # Sort by signal strength
                buy_signals.sort(key=lambda x: x[1], reverse=True)
                sell_signals.sort(key=lambda x: x[1])

                # Execute sells first (free up capital)
                for symbol, strength, reasons in sell_signals:
                    if symbol in self.positions:
                        price_data = self.get_price_on_date(symbol, current_date)
                        if price_data:
                            self.execute_trade(symbol, 'SELL', price_data['day_close'],
                                              current_date, reasons)

                # Execute buys (top N by signal strength)
                max_positions = 20  # Limit portfolio to 20 positions
                for symbol, strength, reasons in buy_signals:
                    if len(self.positions) >= max_positions:
                        break
                    if symbol in self.positions:
                        continue

                    price_data = self.get_price_on_date(symbol, current_date)
                    if price_data:
                        self.execute_trade(symbol, 'BUY', price_data['day_close'],
                                          current_date, reasons)

            # Record weekly portfolio snapshot
            if i % 5 == 0:
                snapshot = self.compute_portfolio_value(current_date)
                self.portfolio_history.append(snapshot)

        # Final valuation
        final = self.compute_portfolio_value(trading_dates[-1])

        # Compute metrics
        total_return = (final['total_value'] - self.initial_capital) / self.initial_capital
        num_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.get('pnl', 0) > 0]
        win_rate = len(winning_trades) / num_trades if num_trades > 0 else 0

        # Compute max drawdown
        peak = self.initial_capital
        max_drawdown = 0
        for snapshot in self.portfolio_history:
            value = snapshot['total_value']
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Annualized return
        years = (self.end_date - self.start_date).days / 365.25
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        results = {
            'strategy': self.strategy,
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
            'initial_capital': self.initial_capital,
            'final_value': round(final['total_value'], 2),
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(annualized_return * 100, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'num_trades': num_trades,
            'win_rate': round(win_rate * 100, 2),
            'sharpe_ratio': 0,  # Computed below
            'num_positions': final['num_positions'],
            'trades': self.trades,
            'portfolio_history': self.portfolio_history,
        }

        # Sharpe ratio (simplified)
        if self.portfolio_history:
            returns = []
            for i in range(1, len(self.portfolio_history)):
                prev = self.portfolio_history[i-1]['total_value']
                curr = self.portfolio_history[i]['total_value']
                if prev > 0:
                    returns.append((curr - prev) / prev)
            if returns:
                import numpy as np
                returns_arr = np.array(returns)
                if returns_arr.std() > 0:
                    results['sharpe_ratio'] = round(
                        (returns_arr.mean() / returns_arr.std()) * (252 ** 0.5), 4
                    )

        # Save results to database
        self.save_results(results)

        logger.info(f"\n{'='*60}")
        logger.info(f"Backtest Complete")
        logger.info(f"  Total Return:     {results['total_return']:>8.2f}%")
        logger.info(f"  Annualized:       {results['annualized_return']:>8.2f}%")
        logger.info(f"  Max Drawdown:     {results['max_drawdown']:>8.2f}%")
        logger.info(f"  Sharpe Ratio:     {results['sharpe_ratio']:>8.4f}")
        logger.info(f"  Win Rate:         {results['win_rate']:>8.1f}%")
        logger.info(f"  Total Trades:     {results['num_trades']:>8d}")
        logger.info(f"  Final Value:      ${results['final_value']:>10,.2f}")
        logger.info(f"{'='*60}")

        return results

    def save_results(self, results: dict):
        """Save backtest results to the database."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO backtest_runs
                (user_id, strategy, parameters, start_date, end_date,
                 initial_capital, final_value, total_return, annualized_return,
                 sharpe_ratio, max_drawdown, num_trades, win_rate, status, completed_at)
            VALUES
                (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'complete', NOW())
        """, (
            self.strategy,
            json.dumps({
                'frequency': self.frequency,
                'max_position_pct': self.max_position_pct,
                'commission': self.commission,
                'universe_size': len(self.symbols) if self.symbols else 'all',
            }),
            self.start_date, self.end_date,
            self.initial_capital,
            results['final_value'],
            results['total_return'] / 100,
            results['annualized_return'] / 100,
            results['sharpe_ratio'],
            results['max_drawdown'] / 100,
            results['num_trades'],
            results['win_rate'] / 100,
        ))

        run_id = cursor.lastrowid

        # Store trades
        for trade in results['trades']:
            cursor.execute("""
                INSERT INTO backtest_trades
                    (backtest_id, symbol, trade_type, trade_date, price,
                     quantity, commission, total_cost, signal_reasons)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                run_id,
                trade['symbol'],
                trade['trade_type'],
                trade['trade_date'],
                trade['price'],
                trade['quantity'],
                trade['commission'],
                trade['total_cost'],
                trade.get('signal_reasons', ''),
            ))

        self.conn.commit()
        cursor.close()

        logger.info(f"Saved backtest run #{run_id} with {len(results['trades'])} trades")


def main():
    parser = argparse.ArgumentParser(description='Backtest Engine')
    parser.add_argument('--strategy', required=True,
                        choices=['combined', 'motley_fool', 'buffett', 'turtle'])
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--initial', type=float, default=DEFAULT_INITIAL_CAPITAL)
    parser.add_argument('--commission', type=float, default=DEFAULT_COMMISSION)
    parser.add_argument('--max-position', type=float, default=DEFAULT_MAX_POSITION_PCT)
    parser.add_argument('--frequency', default='monthly',
                        choices=['weekly', 'monthly', 'quarterly', 'semi_annual'])
    parser.add_argument('--symbols', nargs='*', help='Specific symbols')

    args = parser.parse_args()

    conn = get_connection()

    engine = BacktestEngine(
        conn=conn,
        strategy=args.strategy,
        start_date=datetime.strptime(args.start, '%Y-%m-%d').date(),
        end_date=datetime.strptime(args.end, '%Y-%m-%d').date(),
        initial_capital=args.initial,
        commission=args.commission,
        max_position_pct=args.max_position,
        frequency=args.frequency,
        symbols=args.symbols or [],
    )

    results = engine.run()
    conn.close()


if __name__ == '__main__':
    main()
