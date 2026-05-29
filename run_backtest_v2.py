#!/usr/bin/env python3
"""
run_backtest_v2.py — Self-contained backtest against SQLite dev DB
====================================================================
No dependency on mysql.connector, db_connector, ta_calculator, or scoring_engine.
Reads prices + evalsummary directly from SQLite, generates signals, runs backtest.

Usage:
  python3 run_backtest_v2.py                    # All symbols, 2014-2025
  python3 run_backtest_v2.py --start 2020-01-01 --end 2024-12-31
  python3 run_backtest_v2.py --strategy momentum
"""

import argparse
import sqlite3
import sys
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict

DB_PATH = '/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db'

def load_prices(symbol, start_date, end_date):
    """Load price data for a symbol from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT price_date, day_open as open, day_high as high,
               day_low as low, day_close as close, volume
        FROM stockprices
        WHERE symbol = ? AND price_date BETWEEN ? AND ?
        ORDER BY price_date
    """, conn, params=(symbol, start_date, end_date), parse_dates=['price_date'])
    conn.close()
    df = df.set_index('price_date')
    return df

def load_scores(symbol, start_date, end_date):
    """Load evalsummary scores for a symbol from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT eval_date, signal_strength, momentum_score, trend_score,
               mean_reversion_score, rsi_14, macd_hist, roc_10, roc_20, hvol_20
        FROM evalsummary
        WHERE symbol = ? AND eval_date BETWEEN ? AND ?
        ORDER BY eval_date
    """, conn, params=(symbol, start_date, end_date), parse_dates=['eval_date'])
    conn.close()
    return df

def compute_signals(df, scores_df):
    """
    Generate trading signals from price data + scoring.
    Returns a DataFrame with signal columns.
    """
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)

    # ATR (14-day)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr_14 = tr.rolling(14).mean()

    # SMAs
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9).mean()
    macd_hist = macd - macd_signal

    # Bollinger Bands
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_pct = (close - (bb_mid - 2*bb_std)) / ((bb_mid + 2*bb_std) - (bb_mid - 2*bb_std)).replace(0, np.nan)

    # ROC
    roc_10 = close.pct_change(10) * 100
    roc_20 = close.pct_change(20) * 100

    # Build signal DataFrame
    signals = pd.DataFrame(index=df.index)
    signals['close'] = close
    signals['atr_14'] = atr_14
    signals['atr_pct'] = atr_14 / close * 100
    signals['rsi'] = rsi
    signals['macd_hist'] = macd_hist
    signals['sma_20'] = sma_20
    signals['sma_50'] = sma_50
    signals['sma_200'] = sma_200
    signals['bb_pct'] = bb_pct
    signals['roc_10'] = roc_10
    signals['roc_20'] = roc_20

    # Merge with scoring data if available (drop overlapping columns from scores)
    if len(scores_df) > 0:
        scores_df = scores_df.set_index('eval_date').sort_index()
        overlap_cols = [c for c in signals.columns if c in scores_df.columns]
        scores_df = scores_df.drop(columns=overlap_cols, errors='ignore')
        signals = signals.join(scores_df, how='left')

    # === SIGNAL GENERATION ===
    # Individual signal components (0 or 1)
    signals['sig_rsi_oversold'] = (rsi < 30).astype(int)
    signals['sig_rsi_overbought'] = (rsi > 70).astype(int)
    signals['sig_macd_bull'] = (macd_hist > 0).astype(int)
    signals['sig_macd_bear'] = (macd_hist < 0).astype(int)
    signals['sig_price_above_sma20'] = (close > sma_20).astype(int)
    signals['sig_price_above_sma50'] = (close > sma_50).astype(int)
    signals['sig_sma20_above_sma50'] = (sma_20 > sma_50).astype(int)
    signals['sig_bb_low'] = (bb_pct < 0.2).astype(int)
    signals['sig_bb_high'] = (bb_pct > 0.8).astype(int)

    # Composite signal: +1 bullish, -1 bearish, 0 neutral
    bull = (
        signals['sig_rsi_oversold'] * 1 +
        signals['sig_macd_bull'] * 1 +
        signals['sig_price_above_sma20'] * 0.5 +
        signals['sig_price_above_sma50'] * 0.5 +
        signals['sig_sma20_above_sma50'] * 1 +
        signals['sig_bb_low'] * 1
    )

    bear = (
        signals['sig_rsi_overbought'] * 1 +
        signals['sig_macd_bear'] * 1 +
        (1 - signals['sig_price_above_sma20']) * 0.5 +
        (1 - signals['sig_price_above_sma50']) * 0.5 +
        (1 - signals['sig_sma20_above_sma50']) * 1 +
        signals['sig_bb_high'] * 1
    )

    # Add scoring signal if available (amplify for stronger signals)
    if 'signal_strength' in signals.columns:
        score = signals['signal_strength'].fillna(0)
        # Add momentum and trend if available
        mom = signals['momentum_score'].fillna(0) if 'momentum_score' in signals.columns else 0
        tr = signals['trend_score'].fillna(0) if 'trend_score' in signals.columns else 0
        signals['raw_signal'] = score * 0.5 + (bull - bear) * 5 + mom * 0.3 + tr * 0.3
    else:
        signals['raw_signal'] = (bull - bear) * 5

    # Threshold-based signals (lower threshold for more trades)
    signals['action'] = 0  # 0=hold, 1=buy, -1=sell
    signals.loc[signals['raw_signal'] > 3, 'action'] = 1
    signals.loc[signals['raw_signal'] < -3, 'action'] = -1

    # Debug: print signal stats
    if 'signal_strength' in signals.columns:
        print(f"    raw_signal: mean={signals['raw_signal'].mean():.2f}, "
              f"max={signals['raw_signal'].max():.2f}, min={signals['raw_signal'].min():.2f}")
        print(f"    actions: BUY={(signals['action']==1).sum()}, SELL={(signals['action']==-1).sum()}, HOLD={(signals['action']==0).sum()}")

    return signals


def run_backtest(symbols, start_date, end_date, initial_capital, commission, max_pos_pct, frequency_days):
    """
    Run backtest across all symbols.
    Returns results dict.
    """
    all_dates = set()
    symbol_data = {}

    for symbol in symbols:
        df = load_prices(symbol, start_date, end_date)
        if len(df) < 60:
            print(f"  Skipping {symbol}: only {len(df)} rows")
            continue
        scores = load_scores(symbol, start_date, end_date)
        signals = compute_signals(df, scores)
        print(f"  {symbol}: signals index type={type(signals.index[0])}, range={signals.index[0]} → {signals.index[-1]}")
        symbol_data[symbol] = signals
        all_dates.update([pd.Timestamp(d) for d in signals.index.tolist()])

    if not all_dates:
        print("No price data found!")
        return {}

    all_dates = sorted(all_dates)
    print(f"  Date range: {all_dates[0]} → {all_dates[-1]} ({len(all_dates)} dates)")
    print(f"  last_rebalance init: {all_dates[0] - timedelta(days=1)}")

    # State
    cash = initial_capital
    positions = {}  # symbol -> shares
    cost_basis = {}  # symbol -> avg cost
    trades = []
    portfolio_values = []
    last_rebalance = all_dates[0] - timedelta(days=1)

    n_rebalance = 0
    for date_idx in all_dates:
        current_date = date_idx

        # Monthly rebalance trigger
        try:
            days_since = (current_date - last_rebalance).days
        except Exception as e:
            print(f"    DATE ERROR: {e}, current_date={current_date} ({type(current_date)}), last_rebalance={last_rebalance} ({type(last_rebalance)})")
            break
        is_rebalance = days_since >= frequency_days

        if is_rebalance:
            n_rebalance += 1
            last_rebalance = current_date

            # Get current prices
            prices = {}
            for sym, sig in symbol_data.items():
                if current_date in sig.index:
                    prices[sym] = sig.loc[current_date, 'close']

            if not prices:
                continue

            # Portfolio value
            port_value = cash + sum(
                positions.get(sym, 0) * prices[sym]
                for sym in prices if sym in positions
            )

            # Target allocation per symbol
            n_symbols = len(symbol_data)
            if n_symbols == 0:
                continue

            target_per_symbol = port_value * max_pos_pct
            total_target = target_per_symbol * n_symbols
            # Scale down if too many positions
            if total_target > port_value * 0.95:
                target_per_symbol = port_value * 0.95 / n_symbols

            # Rebalance each symbol
            for sym, sig in symbol_data.items():
                if current_date not in sig.index:
                    continue

                price = sig.loc[current_date, 'close']
                action = sig.loc[current_date, 'action']
                current_shares = positions.get(sym, 0)

                if action == 1 and current_shares == 0:
                    # BUY
                    shares_to_buy = int(target_per_symbol / price)
                    if shares_to_buy < 1:
                        continue
                    cost = shares_to_buy * price + commission
                    if cost > cash:
                        shares_to_buy = int((cash - commission) / price)
                        if shares_to_buy < 1:
                            continue
                        cost = shares_to_buy * price + commission
                    cash -= cost
                    positions[sym] = positions.get(sym, 0) + shares_to_buy
                    cost_basis[sym] = price
                    trades.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'symbol': sym,
                        'action': 'BUY',
                        'shares': shares_to_buy,
                        'price': round(price, 2),
                        'commission': commission,
                    })
                    print(f"    {current_date.strftime('%Y-%m-%d')} BUY {shares_to_buy} {sym} @ ${price:.2f}")

                elif action == -1 and current_shares > 0:
                    # SELL
                    proceeds = current_shares * price - commission
                    cash += proceeds
                    trades.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'symbol': sym,
                        'action': 'SELL',
                        'shares': current_shares,
                        'price': round(price, 2),
                        'commission': commission,
                    })
                    print(f"    {current_date.strftime('%Y-%m-%d')} SELL {current_shares} {sym} @ ${price:.2f}")
                    del positions[sym]
                    if sym in cost_basis:
                        del cost_basis[sym]

        # Track portfolio value
        port_value = cash
        for sym, shares in positions.items():
            if current_date in symbol_data[sym].index:
                port_value += shares * symbol_data[sym].loc[current_date, 'close']
            else:
                # Use last known price
                last_price = symbol_data[sym]['close'].iloc[-1]
                port_value += shares * last_price

        portfolio_values.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'value': round(port_value, 2),
            'cash': round(cash, 2),
            'positions': len(positions),
        })

    print(f"  Rebalance days triggered: {n_rebalance}")
    print(f"  Final positions: {positions}")
    print(f"  Final cash: ${cash:,.2f}")

    # Final portfolio
    final_value = portfolio_values[-1]['value'] if portfolio_values else initial_capital
    pnl = final_value - initial_capital
    pnl_pct = (pnl / initial_capital) * 100

    # Max drawdown
    values = [pv['value'] for pv in portfolio_values]
    peak = values[0]
    max_dd = 0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Sharpe (annualized)
    returns = pd.Series(values).pct_change().dropna()
    if len(returns) > 1 and returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
    else:
        sharpe = 0

    results = {
        'start_date': start_date,
        'end_date': end_date,
        'symbols': len(symbol_data),
        'trades': len(trades),
        'initial_capital': initial_capital,
        'final_value': round(final_value, 2),
        'pnl': round(pnl, 2),
        'pnl_pct': round(pnl_pct, 2),
        'max_drawdown': round(max_dd, 2),
        'sharpe': round(sharpe, 3),
        'portfolio_values': portfolio_values,
        'trades': trades,
    }

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str, default='2014-01-01')
    parser.add_argument('--end', type=str, default='2024-12-31')
    parser.add_argument('--capital', type=float, default=100000)
    parser.add_argument('--commission', type=float, default=9.95)
    parser.add_argument('--max-pos', type=float, default=0.10)
    parser.add_argument('--freq', type=str, default='monthly', choices=['weekly', 'monthly', 'quarterly'])
    args = parser.parse_args()

    freq_days = {'weekly': 7, 'monthly': 30, 'quarterly': 91}[args.freq]
    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    # Get all symbols with data
    conn = sqlite3.connect(DB_PATH)
    symbols = [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM stockprices ORDER BY symbol"
    ).fetchall()]
    conn.close()

    print("=" * 70)
    print("BACKTEST v2 — Self-Contained SQLite")
    print("=" * 70)
    print(f"  Period:     {start_date} → {end_date}")
    print(f"  Capital:    ${args.capital:,.0f}")
    print(f"  Commission: ${args.commission}")
    print(f"  Max Pos:    {args.max_pos*100:.0f}%")
    print(f"  Frequency:  {args.freq} ({freq_days} days)")
    print(f"  DB:         {DB_PATH}")
    print()

    results = run_backtest(symbols, start_date, end_date, args.capital, args.commission, args.max_pos, freq_days)

    if not results:
        print("No results!")
        return

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"  Symbols:        {results['symbols']}")
    print(f"  Total Trades:   {results['trades']}")
    print(f"  Final Value:    ${results['final_value']:,.2f}")
    print(f"  P&L:            ${results['pnl']:,.2f} ({results['pnl_pct']:+.1f}%)")
    print(f"  Max Drawdown:   {results['max_drawdown']:.1f}%")
    print(f"  Sharpe Ratio:   {results['sharpe']:.3f}")
    print()

    # Trade log
    if results['trades']:
        print("TRADE LOG:")
        print("-" * 50)
        for t in results['trades'][:30]:
            print(f"  {t['date']}  {t['action']:4s} {t['shares']:4d} {t['symbol']:8s} @ ${t['price']:8.2f}")
        if len(results['trades']) > 30:
            print(f"  ... ({len(results['trades'])} total trades)")

    # Equity curve (last 10 points)
    pv = results['portfolio_values']
    if pv:
        print(f"\nEQUITY CURVE (last 10 days):")
        print("-" * 50)
        for point in pv[-10:]:
            print(f"  {point['date']}  ${point['value']:>12,.2f}  ({point['positions']} pos, ${point['cash']:,.0f} cash)")

    # Save results to SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS backtest_runs_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,
            start_date TEXT,
            end_date TEXT,
            symbols INTEGER,
            trades INTEGER,
            initial_capital REAL,
            final_value REAL,
            pnl REAL,
            pnl_pct REAL,
            max_drawdown REAL,
            sharpe REAL
        );
        CREATE TABLE IF NOT EXISTS backtest_trades_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            trade_date TEXT,
            symbol TEXT,
            action TEXT,
            shares INTEGER,
            price REAL,
            commission REAL
        );
    """)
    cur = conn.execute("""
        INSERT INTO backtest_runs_v2 (run_date, start_date, end_date, symbols, trades, initial_capital, final_value, pnl, pnl_pct, max_drawdown, sharpe)
        VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(start_date), str(end_date), results['symbols'], len(results['trades']),
          args.capital, results['final_value'], results['pnl'], results['pnl_pct'],
          results['max_drawdown'], results['sharpe']))
    run_id = cur.lastrowid
    conn.commit()

    for t in results['trades']:
        conn.execute("""
            INSERT INTO backtest_trades_v2 (run_id, trade_date, symbol, action, shares, price, commission)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_id, t['date'], t['symbol'], t['action'], t['shares'], t['price'], t['commission']))
    conn.commit()
    conn.close()

    print(f"\n✅ Results saved: backtest_runs_v2 row {run_id}")


if __name__ == '__main__':
    main()
