#!/usr/bin/env python3
"""
strategy_pipeline.py — Full backtest pipeline with all legacy strategies
=========================================================================
Implements all strategies from the legacy PHP system:
  1. Turtle Trading (20-day breakout / 55-day breakout variants)
  2. 4-Week Rule (buy if price > 4-week high, sell if < 4-week low)
  3. Candlestick Pattern (TA-Lib CDL patterns → buy/sell signals)
  4. Coin Toss (random 50/50 with position sizing)
  5. Buy and Hold
  6. RSI Momentum (mean-reversion + momentum)
  7. MACD Trend Following
  8. Bollinger Band Mean Reversion
  9. Multi-Strategy Combos (1→2→3→...N strategies, majority vote)

Parameter sweep: varies trade size, allocation %, stop size, rebalance freq.
Combo testing: tries all combinations of strategies with consensus voting.

Usage:
  python3 strategy_pipeline.py                          # Full sweep
  python3 strategy_pipeline.py --strategy turtle        # Single strategy
  python3 strategy_pipeline.py --combos                 # Combo only
  python3 strategy_pipeline.py --quick                  # Fast mode (fewer params)
"""

import argparse, json, sqlite3, sys, os, itertools, random, time
import numpy as np
import pandas as pd
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
np.random.seed(42)

DB_PATH = Path("/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db")
RESULTS_TABLE = "strategy_pipeline_results"

# =========================================================================
# DATA LOADING (reused from run_backtest_v2.py)
# =========================================================================

def load_prices(symbol, start, end):
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("""
        SELECT price_date, day_open as open, day_high as high,
               day_low as low, day_close as close, volume
        FROM stockprices
        WHERE symbol = ? AND price_date BETWEEN ? AND ?
        ORDER BY price_date
    """, conn, params=(symbol, start, end), parse_dates=['price_date'])
    conn.close()
    if df.empty: return df
    df = df.set_index('price_date').sort_index()
    for c in ['open', 'high', 'low', 'close', 'volume']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


# =========================================================================
# TECHNICAL INDICATOR COMPUTATION (shared by all strategies)
# =========================================================================

def compute_indicators(df):
    """Compute full TA suite. Returns DataFrame with indicator columns."""
    c = df['close'].values.astype(float)
    h = df['high'].values.astype(float)
    l = df['low'].values.astype(float)
    n = len(c)
    df = df.copy()

    # True Range / ATR
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(np.roll(c, 1) - l)))
    tr[0] = h[0] - l[0]
    for period in [1, 7, 14, 20]:
        df[f'atr_{period}'] = pd.Series(tr, index=df.index).rolling(period).mean().values * (1 if period == 1 else 1)

    # ATR-stops: entry_price ± factor * ATR
    for factor in [1.0, 1.5, 2.0, 2.5, 3.0]:
        df[f'atr_stop_upper_{factor}'] = c + factor * df['atr_14'].values
        df[f'atr_stop_lower_{factor}'] = c - factor * df['atr_14'].values

    # SMA
    for period in [5, 10, 20, 50, 55, 100, 200]:
        df[f'sma_{period}'] = pd.Series(c).rolling(period).mean().values

    # EMA
    for period in [12, 26]:
        df[f'ema_{period}'] = pd.Series(c).ewm(span=period).mean().values

    # RSI
    delta = pd.Series(c).diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = (100 - (100 / (1 + rs))).values

    # RSI (7-day for short-term)
    gain7 = delta.where(delta > 0, 0).rolling(7).mean()
    loss7 = (-delta.where(delta < 0, 0)).rolling(7).mean()
    rs7 = gain7 / loss7.replace(0, np.nan)
    df['rsi_7'] = (100 - (100 / (1 + rs7))).values

    # MACD
    ema12 = pd.Series(c).ewm(span=12).mean()
    ema26 = pd.Series(c).ewm(span=26).mean()
    df['macd'] = (ema12 - ema26).values
    df['macd_signal'] = pd.Series(df['macd']).ewm(span=9).mean().values
    df['macd_hist'] = (df['macd'] - df['macd_signal'])

    # Bollinger Bands
    bb_mid = pd.Series(c).rolling(20).mean()
    bb_std = pd.Series(c).rolling(20).std()
    df['bb_upper'] = (bb_mid + 2 * bb_std).values
    df['bb_lower'] = (bb_mid - 2 * bb_std).values
    df['bb_pct'] = ((c - df['bb_lower'].values) / (df['bb_upper'].values - df['bb_lower'].values + 1e-10))

    # Rolling high/low (Turtle, 4-Week)
    for period in [10, 20, 55]:
        df[f'high_{period}'] = pd.Series(h).rolling(period).max().values
        df[f'low_{period}'] = pd.Series(l).rolling(period).min().values

    # Stochastic
    low_14 = pd.Series(l).rolling(14).min()
    high_14 = pd.Series(h).rolling(14).max()
    df['stoch_k'] = ((c - low_14) / (high_14 - low_14 + 1e-10) * 100).values
    df['stoch_d'] = pd.Series(df['stoch_k']).rolling(3).mean().values

    # Candle doji / hammer detection (simple)
    body = np.abs(c - df['open'].values.astype(float))
    upper_shadow = h - np.maximum(c, df['open'].values.astype(float))
    lower_shadow = np.minimum(c, df['open'].values.astype(float)) - l
    rng = h - l + 1e-10
    df['doji'] = (body / rng < 0.1).astype(int)
    df['hammer'] = ((lower_shadow > 2 * body) & (upper_shadow < body)).astype(int)
    df['shooting_star'] = ((upper_shadow > 2 * body) & (lower_shadow < body)).astype(int)
    df['engulfing_bull'] = ((c > df['open'].values.astype(float)) &
                             (np.roll(c, 1) <= np.roll(df['open'].values.astype(float), 1)) &
                             (np.abs(c - df['open'].values.astype(float)) > np.abs(np.roll(c, 1) - np.roll(df['open'].values.astype(float), 1)))).astype(float)
    df['engulfing_bull'] = df['engulfing_bull'].fillna(0).astype(int)

    # Volume ratio
    vol = df['volume'].values.astype(float) if 'volume' in df.columns else np.zeros(n)
    vol_sma20 = pd.Series(vol).rolling(20).mean().values
    df['vol_ratio'] = vol / (vol_sma20 + 1e-10)

    # Rate of change
    for period in [5, 10, 20]:
        df[f'roc_{period}'] = pd.Series(c).pct_change(period).values * 100

    # Donchian Channel (Turtle)
    df['donchian_upper_20'] = pd.Series(h).rolling(20).max().values
    df['donchian_lower_20'] = pd.Series(l).rolling(20).min().values
    df['donchian_upper_55'] = pd.Series(h).rolling(55).max().values
    df['donchian_lower_55'] = pd.Series(l).rolling(55).min().values

    # Legacy average stock value trigger
    df['buy_avg'] = pd.Series(c).rolling(60).mean().values   # buystockaverage default: 60
    df['sell_avg'] = pd.Series(c).rolling(40).mean().values   # sellstockaverage default: 40

    return df.fillna(0)


# =========================================================================
# STRATEGY DEFINITIONS
# Each strategy takes (df, params) → returns DataFrame with 'signal' column
# Signal: +1 = BUY, -1 = SELL, 0 = HOLD
# =========================================================================

def strategy_turtle_20(df, p):
    """Turtle Trading: 20-day Donchian breakout (long) / 20-day low breakout (exit)."""
    sig = pd.Series(0, index=df.index)
    for i in range(20, len(df)):
        if df['close'].iloc[i] > df['donchian_upper_20'].iloc[i-1]:
            sig.iloc[i] = 1
        elif df['close'].iloc[i] < df['donchian_lower_20'].iloc[i-1]:
            sig.iloc[i] = -1
    return sig

def strategy_turtle_55(df, p):
    """Turtle Trading: 55-day Donchian breakout system."""
    sig = pd.Series(0, index=df.index)
    for i in range(55, len(df)):
        if df['close'].iloc[i] > df['donchian_upper_55'].iloc[i-1]:
            sig.iloc[i] = 1
        elif df['close'].iloc[i] < df['donchian_lower_55'].iloc[i-1]:
            sig.iloc[i] = -1
    return sig

def strategy_turtle_dual(df, p):
    """Turtle Dual: 55-day entry + 20-day exit (classic Turtle)."""
    sig = pd.Series(0, index=df.index)
    in_position = False
    for i in range(55, len(df)):
        if not in_position:
            if df['close'].iloc[i] > df['donchian_upper_55'].iloc[i-1]:
                sig.iloc[i] = 1
                in_position = True
        else:
            if df['close'].iloc[i] < df['donchian_lower_20'].iloc[i-1]:
                sig.iloc[i] = -1
                in_position = False
    return sig

def strategy_4week(df, p):
    """4-Week Rule: Buy if close > 4-week (20-day) high, sell if < 4-week low."""
    sig = pd.Series(0, index=df.index)
    for i in range(20, len(df)):
        if df['close'].iloc[i] > df['high_20'].iloc[i-1]:
            sig.iloc[i] = 1
        elif df['close'].iloc[i] < df['low_20'].iloc[i-1]:
            sig.iloc[i] = -1
    return sig

def strategy_candlestick(df, p):
    """Candlestick Pattern strategy: score-based from DOJI/HAMMER/SHOOTING_STAR/ENGULFING."""
    buy_thresh = p.get('buy_avg', 60)
    sell_thresh = p.get('sell_avg', 40)
    # Score each candle: bullish +1, bearish -1, neutral 0
    score = pd.Series(0.0, index=df.index)
    score += df['hammer'].values.astype(float) * 30
    score += df['engulfing_bull'].values.astype(float) * 40
    score -= df['shooting_star'].values.astype(float) * 30
    score -= df['doji'].values.astype(float) * 10  # doji = uncertainty, slight negative

    sig = pd.Series(0, index=df.index)
    # Look back 3 days for pattern confirmation
    for i in range(3, len(df)):
        window_score = score.iloc[i-2:i+1].mean()
        if window_score > buy_thresh:
            sig.iloc[i] = 1
        elif window_score < sell_thresh:
            sig.iloc[i] = -1
    return sig

def strategy_coin_toss(df, p):
    """Coin Toss: Random 50/50 with optional bias. Includes position sizing."""
    bias = p.get('bias', 0.5)  # 0.5 = fair, >0.5 = bullish
    hold_prob = p.get('hold_prob', 0.7)  # 70% chance of doing nothing
    sig = pd.Series(0, index=df.index)
    for i in range(1, len(df)):
        r = random.random()
        if r < hold_prob:
            sig.iloc[i] = 0  # hold
        elif random.random() < bias:
            sig.iloc[i] = 1  # buy
        else:
            sig.iloc[i] = -1  # sell
    return sig

def strategy_buy_and_hold(df, p):
    """Buy and Hold: Buy at start, never sell."""
    sig = pd.Series(0, index=df.index)
    sig.iloc[20] = 1  # buy once at start (after warmup)
    return sig

def strategy_rsi_momentum(df, p):
    """RSI Mean Reversion + Momentum combo."""
    oversold = p.get('rsi_oversold', 30)
    overbought = p.get('rsi_overbought', 70)
    sig = pd.Series(0, index=df.index)
    for i in range(1, len(df)):
        rsi = df['rsi_14'].iloc[i]
        if rsi < oversold and df['close'].iloc[i] > df['sma_50'].iloc[i]:
            sig.iloc[i] = 1
        elif rsi > overbought:
            sig.iloc[i] = -1
    return sig

def strategy_macd_trend(df, p):
    """MACD Trend Following: buy on MACD cross up, sell on cross down."""
    sig = pd.Series(0, index=df.index)
    macd_hist = df['macd_hist'].values
    for i in range(1, len(df)):
        if macd_hist[i] > 0 and macd_hist[i-1] <= 0:
            sig.iloc[i] = 1
        elif macd_hist[i] < 0 and macd_hist[i-1] >= 0:
            sig.iloc[i] = -1
    return sig

def strategy_bollinger_mean_rev(df, p):
    """Bollinger Band Mean Reversion: buy at lower band, sell at upper band."""
    sig = pd.Series(0, index=df.index)
    for i in range(1, len(df)):
        bb_pct = df['bb_pct'].iloc[i]
        if bb_pct < 0.1 and df['close'].iloc[i] > df['sma_200'].iloc[i]:
            sig.iloc[i] = 1
        elif bb_pct > 0.9:
            sig.iloc[i] = -1
    return sig

def strategy_stochastic(df, p):
    """Stochastic Oscillator: buy when K crosses above D in oversold."""
    sig = pd.Series(0, index=df.index)
    for i in range(1, len(df)):
        k = df['stoch_k'].iloc[i]
        d = df['stoch_d'].iloc[i]
        k_prev = df['stoch_k'].iloc[i-1]
        d_prev = df['stoch_d'].iloc[i-1]
        if k > d and k_prev <= d_prev and k < 20:
            sig.iloc[i] = 1
        elif k < d and k_prev >= d_prev and k > 80:
            sig.iloc[i] = -1
    return sig


# Strategy registry
ALL_STRATEGIES = {
    'turtle_20':       strategy_turtle_20,
    'turtle_55':       strategy_turtle_55,
    'turtle_dual':     strategy_turtle_dual,
    '4week':           strategy_4week,
    'candlestick':     strategy_candlestick,
    'coin_toss':       strategy_coin_toss,
    'buy_and_hold':    strategy_buy_and_hold,
    'rsi_momentum':    strategy_rsi_momentum,
    'macd_trend':      strategy_macd_trend,
    'bollinger_mr':    strategy_bollinger_mean_rev,
    'stochastic':      strategy_stochastic,
}


# =========================================================================
# MONEY MANAGEMENT (from backtest.class.php)
# =========================================================================

def calc_position_size(port_price, cash, portfolio_value, params):
    """
    Calculate number of shares to buy based on money management rules:
    - max_pct_portfolio: max % of portfolio per trade (legacy default: 10%)
    - max_risk_pct: max % of portfolio to risk per trade (legacy default: 1%)
    - stop_factor: ATR multiplier for stop size
    """
    max_pct = params.get('max_pct_portfolio', 0.10)
    max_risk_pct = params.get('max_risk_pct', 0.01)
    stop_factor = params.get('stop_factor', 2.0)

    # Dollar max per trade (float)
    trade_dollars = min(cash, portfolio_value * max_pct)
    # Risk-based sizing
    risk_dollars = portfolio_value * max_risk_pct
    # Position = min(float / price, risk / stop_size)
    if port_price <= 0:
        return 0
    shares_by_float = int(trade_dollars / port_price)
    stop_size = port_price * max_risk_pct  # legacy: maxrisk * sharecost
    if stop_size <= 0:
        stop_size = port_price * 0.01
    shares_by_risk = int(risk_dollars / stop_size) if stop_size > 0 else shares_by_float
    return max(0, min(shares_by_float, shares_by_risk))


# =========================================================================
# BACKTEST ENGINE
# =========================================================================

def run_backtest(df, signal_col, params, symbol):
    """Run a single backtest given a DataFrame with a signal column."""
    initial_cash = params.get('initial_cash', 100000)
    commission = params.get('commission', 9.95)
    rebalance_days = params.get('rebalance_days', 30)
    max_pct = params.get('max_pct_portfolio', 0.10)
    stop_factor = params.get('stop_factor', 2.0)
    atr_stop = params.get('atr_stop', True)

    cash = initial_cash
    shares = 0
    entry_price = 0
    entry_date_idx = 0
    trades = []
    equity_curve = []
    last_rebalance = -1
    holding_days = 0
    max_holding = params.get('max_holding_days', 0)  # 0 = unlimited

    close = df['close'].values.astype(float)
    high = df['high'].values.astype(float)
    low = df['low'].values.astype(float)
    sig = signal_col.values if hasattr(signal_col, 'values') else signal_col
    atr_vals = df['atr_14'].values.astype(float)

    for i in range(55, len(df)):  # warmup for 55-period indicators
        current_price = close[i]
        current_sig = sig[i]

        # Navigable date
        portfolio_value = cash + shares * current_price

        # Rebalance check
        is_rebalance = (i - last_rebalance) >= rebalance_days
        if is_rebalance:
            last_rebalance = i

            if current_sig == 1 and shares == 0 and cash > commission:
                # BUY
                n = calc_position_size(current_price, cash, portfolio_value,
                                      {'max_pct_portfolio': max_pct,
                                       'max_risk_pct': params.get('max_risk_pct', 0.01),
                                       'stop_factor': stop_factor})
                if n > 0:
                    cost = n * current_price + commission
                    if cost <= cash:
                        shares = n
                        cash -= cost
                        entry_price = current_price
                        entry_date_idx = i

            elif current_sig == -1 and shares > 0:
                # SELL
                proceeds = shares * current_price - commission
                pnl = proceeds - (shares * entry_price + commission)
                cash += proceeds
                trades.append({
                    'entry_idx': entry_date_idx, 'exit_idx': i,
                    'pnl': pnl, 'return_pct': pnl / (shares * entry_price + commission) * 100,
                    'holding_days': i - entry_date_idx,
                })
                shares = 0
                entry_price = 0

        # ATR trailing stop check
        if atr_stop and shares > 0 and atr_vals[i] > 0:
            stop_price = entry_price - stop_factor * atr_vals[i]
            if low[i] <= stop_price:
                proceeds = shares * stop_price - commission
                pnl = proceeds - (shares * entry_price + commission)
                cash += proceeds
                trades.append({
                    'entry_idx': entry_date_idx, 'exit_idx': i,
                    'pnl': pnl, 'return_pct': pnl / (shares * entry_price + commission) * 100,
                    'holding_days': i - entry_date_idx,
                })
                shares = 0
                entry_price = 0

        # Max holding days stop
        if max_holding > 0 and shares > 0 and (i - entry_date_idx) >= max_holding:
            proceeds = shares * current_price - commission
            pnl = proceeds - (shares * entry_price + commission)
            cash += proceeds
            trades.append({
                'entry_idx': entry_date_idx, 'exit_idx': i,
                'pnl': pnl, 'return_pct': pnl / (shares * entry_price + commission) * 100,
                'holding_days': i - entry_date_idx,
            })
            shares = 0
            entry_price = 0

        equity_curve.append(cash + shares * current_price)

    # Close final position
    final_price = close[-1]
    final_value = cash + shares * final_price
    if shares > 0:
        trades.append({
            'entry_idx': entry_date_idx, 'exit_idx': len(df)-1,
            'pnl': shares * (final_price - entry_price),
            'return_pct': (final_price - entry_price) / entry_price * 100,
            'holding_days': len(df) - 1 - entry_date_idx,
        })

    # Compute stats
    n_trades = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    win_rate = len(wins) / n_trades if n_trades > 0 else 0
    avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss if n_trades > 0 else 0
    total_pnl = final_value - initial_cash
    pnl_pct = total_pnl / initial_cash * 100

    # Max drawdown
    peak = equity_curve[0] if equity_curve else initial_cash
    max_dd = 0
    for v in equity_curve:
        if v > peak: peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd: max_dd = dd

    # Sharpe
    eq = pd.Series(equity_curve)
    returns = eq.pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() > 0 else 0

    # Profit factor
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        'symbol': symbol,
        'initial_cash': initial_cash,
        'final_value': round(final_value, 2),
        'total_pnl': round(total_pnl, 2),
        'pnl_pct': round(pnl_pct, 2),
        'n_trades': n_trades,
        'win_rate': round(win_rate * 100, 1),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'expectancy': round(expectancy, 2),
        'profit_factor': round(profit_factor, 2),
        'max_drawdown': round(max_dd, 2),
        'sharpe': round(sharpe, 3),
    }


# =========================================================================
# COMBINED / CONSENSUS STRATEGY
# =========================================================================

def run_combo_backtest(df, strategies, params, symbol):
    """
    Run multiple strategies and take consensus:
    majority vote = action. If tie, hold.
    With 2 strategies: need both agree to trade.
    With 3+ strategies: majority rules.
    """
    warmup = 55
    n = len(df)
    close = df['close'].values.astype(float)
    low = df['low'].values.astype(float)
    atr_vals = df['atr_14'].values.astype(float)

    cash = params.get('initial_cash', 100000)
    commission = params.get('commission', 9.95)
    rebalance_days = params.get('rebalance_days', 30)
    max_pct = params.get('max_pct_portfolio', 0.10)
    stop_factor = params.get('stop_factor', 2.0)

    shares = 0
    entry_price = 0
    entry_idx = 0
    trades = []
    equity = []
    last_rebalance = -1

    # Pre-compute signals for each strategy
    signal_cols = {}
    for s_name, s_func in strategies.items():
        try:
            signal_cols[s_name] = s_func(df, params)
        except Exception as e:
            print(f"  WARNING: strategy {s_name} failed for {symbol}: {e}")
            signal_cols[s_name] = pd.Series(0, index=df.index)

    for i in range(warmup, n):
        current_price = close[i]
        is_rebalance = (i - last_rebalance) >= rebalance_days
        if is_rebalance:
            last_rebalance = i

            # Consensus vote
            votes = {1: 0, -1: 0, 0: 0}
            for s_name, sig in signal_cols.items():
                if i < len(sig):
                    votes[sig.iloc[i]] += 1

            total_strats = len(strategies)
            portfolio_value = cash + shares * current_price

            if shares == 0 and cash > commission:
                # Need majority of non-hold votes to buy
                non_hold = total_strats - votes[0]
                buy_pct = votes[1] / non_hold if non_hold > 0 else 0
                if votes[1] > votes[-1] and buy_pct >= params.get('consensus_threshold', 0.5):
                    n_shares = calc_position_size(current_price, cash, portfolio_value,
                                                  {'max_pct_portfolio': max_pct,
                                                   'max_risk_pct': params.get('max_risk_pct', 0.1),
                                                   'stop_factor': stop_factor})
                    if n_shares > 0:
                        cost = n_shares * current_price + commission
                        if cost <= cash:
                            shares = n_shares
                            cash -= cost
                            entry_price = current_price
                            entry_idx = i

            elif shares > 0:
                sell_pct = votes[-1] / (total_strats - votes[0]) if (total_strats - votes[0]) > 0 else 0
                if votes[-1] > votes[1] and sell_pct >= params.get('consensus_threshold', 0.5):
                    proceeds = shares * current_price - commission
                    pnl = proceeds - (shares * entry_price + commission)
                    cash += proceeds
                    trades.append({'pnl': pnl, 'return_pct': pnl / (shares * entry_price + commission) * 100,
                                   'holding_days': i - entry_idx})
                    shares = 0

        # ATR stop
        if shares > 0 and atr_vals[i] > 0:
            stop_price = entry_price - stop_factor * atr_vals[i]
            if low[i] <= stop_price:
                proceeds = shares * stop_price - commission
                pnl = proceeds - (shares * entry_price + commission)
                cash += proceeds
                trades.append({'pnl': pnl, 'return_pct': pnl / (shares * entry_price + commission) * 100,
                               'holding_days': i - entry_idx})
                shares = 0

        equity.append(cash + shares * current_price)

    final_value = cash + shares * close[-1]
    if shares > 0:
        trades.append({'pnl': shares * (close[-1] - entry_price),
                        'return_pct': (close[-1] - entry_price) / entry_price * 100,
                        'holding_days': n - 1 - entry_idx})

    # Stats
    n_trades = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    win_rate = len(wins) / n_trades if n_trades > 0 else 0
    avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss if n_trades > 0 else 0
    total_pnl = final_value - params.get('initial_cash', 100000)
    pnl_pct = total_pnl / params.get('initial_cash', 100000) * 100
    eq = pd.Series(equity)
    peak = equity[0] if equity else 1
    max_dd = max(((peak - v) / peak * 100 for v in equity if v < peak), default=0)
    returns = eq.pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() > 0 else 0
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        'symbol': symbol,
        'final_value': round(final_value, 2),
        'total_pnl': round(total_pnl, 2),
        'pnl_pct': round(pnl_pct, 2),
        'n_trades': n_trades,
        'win_rate': round(win_rate * 100, 1),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'expectancy': round(expectancy, 2),
        'profit_factor': round(profit_factor, 2),
        'max_drawdown': round(max_dd, 2),
        'sharpe': round(sharpe, 3),
    }


# =========================================================================
# PARAMETER GRID
# =========================================================================

def get_param_grid(quick=False):
    """Define parameter sweep grid."""
    if quick:
        return {
            'initial_cash': [100000],
            'commission': [9.95],
            'max_pct_portfolio': [0.10],
            'rebalance_days': [30],
            'max_risk_pct': [0.01],
            'stop_factor': [2.0],
            'atr_stop': [True],
        }
    return {
        'initial_cash': [100000],
        'commission': [9.95],
        'max_pct_portfolio': [0.05, 0.10, 0.15, 0.20],   # 5% - 20% per trade
        'rebalance_days': [7, 14, 30, 90],                 # weekly → quarterly
        'max_risk_pct': [0.005, 0.01, 0.02],             # 0.5% - 2% risk per trade
        'stop_factor': [1.5, 2.0, 2.5, 3.0],             # ATR stop multiplier
        'atr_stop': [True, False],
    }


# =========================================================================
# MAIN PIPELINE
# =========================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy', type=str, help='Run single strategy name')
    parser.add_argument('--combos', action='store_true', help='Run combo strategy tests')
    parser.add_argument('--quick', action='store_true', help='Quick mode (fewer params)')
    parser.add_argument('--start', type=str, default='2014-01-01')
    parser.add_argument('--end', type=str, default='2024-12-31')
    parser.add_argument('--symbols', type=str, help='Comma-separated symbols')
    args = parser.parse_args()

    start_date = args.start
    end_date = args.end

    # Get all symbols
    conn = sqlite3.connect(str(DB_PATH))
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
    else:
        symbols = [r[0] for r in conn.execute(
            "SELECT DISTINCT symbol FROM stockprices ORDER BY symbol").fetchall()]
    conn.close()

    # Load data + compute indicators for all symbols (cache for reuse)
    symbol_data = {}
    for sym in symbols:
        df = load_prices(sym, start_date, end_date)
        if len(df) > 60:
            df = compute_indicators(df)
            symbol_data[sym] = df
            print(f"  Loaded {sym}: {len(df)} rows, {df.index[0].date()} → {df.index[-1].date()}")
        else:
            print(f"  SKIP {sym}: only {len(df)} rows")

    print(f"\n{'='*80}")
    print(f"STRATEGY PIPELINE — {len(symbol_data)} symbols")
    print(f"Period: {start_date} → {end_date}")
    print(f"{'='*80}\n")

    param_grid = get_param_grid(args.quick)
    print(f"Parameter grid:")
    for k, v in param_grid.items():
        print(f"  {k}: {v}")
    print()

    # Create results table in DB
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_timestamp TEXT,
            strategy TEXT,
            combo_size INTEGER DEFAULT 0,
            combo_names TEXT,
            params_json TEXT,
            symbol TEXT,
            initial_cash REAL,
            final_value REAL,
            total_pnl REAL,
            pnl_pct REAL,
            n_trades INTEGER,
            win_rate REAL,
            avg_win REAL,
            avg_loss REAL,
            expectancy REAL,
            profit_factor REAL,
            max_drawdown REAL,
            sharpe REAL
        )
    """)
    conn.commit()

    run_ts = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    all_results = []

    # Determine which strategies to run
    if args.strategy:
        if args.strategy not in ALL_STRATEGIES:
            print(f"Unknown strategy: {args.strategy}")
            print(f"Available: {list(ALL_STRATEGIES.keys())}")
            return
        strategies_to_run = {args.strategy: ALL_STRATEGIES[args.strategy]}
    else:
        strategies_to_run = ALL_STRATEGIES

    # Generate parameter combinations
    param_keys = list(param_grid.keys())
    param_values = [param_grid[k] for k in param_keys]
    param_combos = list(itertools.product(*param_values))
    total_tests = len(strategies_to_run) * len(param_combos) * len(symbol_data)
    print(f"Parameter combinations: {len(param_combos)}")
    print(f"Strategies: {list(strategies_to_run.keys())}")
    print(f"Total single-strategy tests: {total_tests}")
    if args.combos or not args.strategy:
        combo_count = sum(len(list(itertools.combinations(strategies_to_run.keys(), cs)))
                         for cs in range(2, min(len(strategies_to_run) + 1, 6)))
        print(f"Combo tests: {combo_count * len(symbol_data)}")
    print()

    # ================================================================
    # PHASE 1: Single strategy sweep
    # ================================================================
    print(f"{'─'*80}")
    print(f"PHASE 1: Single Strategy Parameter Sweep")
    print(f"{'─'*80}")

    test_count = 0
    t0 = time.time()

    for strat_name, strat_func in strategies_to_run.items():
        print(f"\n  Strategy: {strat_name}")

        for pi, pvals in enumerate(param_combos):
            params = dict(zip(param_keys, pvals))
            if pi % max(1, len(param_combos) // 4) == 0:
                elapsed = time.time() - t0
                print(f"    Param set {pi+1}/{len(param_combos)} ({elapsed:.0f}s elapsed)")

            for sym, df in symbol_data.items():
                test_count += 1
                try:
                    signals = strat_func(df, params)
                    result = run_backtest(df, signals, params, sym)
                    result['strategy'] = strat_name
                    result['params'] = json.dumps(params)
                    result['combo_size'] = 1
                    result['combo_names'] = strat_name
                    result['run_timestamp'] = run_ts
                    all_results.append(result)

                    conn.execute(f"""
                        INSERT INTO {RESULTS_TABLE}
                        (run_timestamp, strategy, combo_size, combo_names, params_json, symbol,
                         initial_cash, final_value, total_pnl, pnl_pct, n_trades, win_rate,
                         avg_win, avg_loss, expectancy, profit_factor, max_drawdown, sharpe)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (run_ts, strat_name, 1, strat_name, json.dumps(params), sym,
                          params.get('initial_cash', 100000), result['final_value'],
                          result['total_pnl'], result['pnl_pct'], result['n_trades'],
                          result['win_rate'], result['avg_win'], result['avg_loss'],
                          result['expectancy'], result['profit_factor'],
                          result['max_drawdown'], result['sharpe']))
                except Exception as e:
                    print(f"    ERROR: {strat_name} / {sym}: {e}")

        conn.commit()

    elapsed = time.time() - t0
    print(f"\n  Phase 1 complete: {test_count} tests in {elapsed:.0f}s")

    # ================================================================
    # PHASE 2: Combo strategies (2, 3, 4... strategy consensus)
    # ================================================================
    if args.combos or not args.strategy:
        print(f"\n{'─'*80}")
        print(f"PHASE 2: Multi-Strategy Combo Consensus")
        print(f"{'─'*80}")

        strat_names = list(strategies_to_run.keys())
        consensus_params = {'max_pct_portfolio': 0.10, 'rebalance_days': 30,
                           'max_risk_pct': 0.01, 'stop_factor': 2.0,
                           'initial_cash': 100000, 'commission': 9.95,
                           'atr_stop': True, 'consensus_threshold': 0.5}

        for combo_size in range(2, min(len(strat_names) + 1, 6)):
            print(f"\n  Combo size: {combo_size}")
            combos = list(itertools.combinations(strat_names, combo_size))
            print(f"    Combinations: {len(combos)}")

            for ci, combo in enumerate(combos):
                combo_str = '+'.join(combo)
                print(f"    [{ci+1}/{len(combos)}] {combo_str}")

                combo_funcs = {s: ALL_STRATEGIES[s] for s in combo}

                for sym, df in symbol_data.items():
                    try:
                        result = run_combo_backtest(df, combo_funcs, consensus_params, sym)
                        result['strategy'] = 'combo'
                        result['combo_size'] = combo_size
                        result['combo_names'] = combo_str
                        result['params'] = json.dumps(consensus_params)
                        result['run_timestamp'] = run_ts
                        all_results.append(result)

                        conn.execute(f"""
                            INSERT INTO {RESULTS_TABLE}
                            (run_timestamp, strategy, combo_size, combo_names, params_json, symbol,
                             initial_cash, final_value, total_pnl, pnl_pct, n_trades, win_rate,
                             avg_win, avg_loss, expectancy, profit_factor, max_drawdown, sharpe)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (run_ts, 'combo', combo_size, combo_str,
                              json.dumps(consensus_params), sym,
                              100000, result['final_value'], result['total_pnl'],
                              result['pnl_pct'], result['n_trades'], result['win_rate'],
                              result['avg_win'], result['avg_loss'], result['expectancy'],
                              result['profit_factor'], result['max_drawdown'], result['sharpe']))
                    except Exception as e:
                        print(f"    ERROR: {combo_str} / {sym}: {e}")

                conn.commit()

    conn.close()

    # ================================================================
    # RESULTS SUMMARY
    # ================================================================
    print(f"\n{'='*80}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*80}")

    pdf = pd.DataFrame(all_results)

    # Rank by Sharpe ratio (minimum 10 trades)
    significant = pdf[pdf['n_trades'] >= 10].copy()
    if len(significant) > 0:
        top_sharpe = significant.nlargest(20, 'sharpe')
        print(f"\n🏆 TOP 20 BY SHARPE (min 10 trades):")
        print(f"{'Strategy':<30s} {'Sym':<8s} {'Trades':>6s} {'Win%':>6s} {'P&L%':>8s} {'Sharpe':>7s} {'MaxDD':>7s} {'PF':>6s} {'Expect':>8s}")
        print(f"{'-'*100}")
        for _, r in top_sharpe.iterrows():
            strategy_label = f"{r['combo_names']}" if r['combo_size'] > 1 else r['strategy']
            print(f"  {strategy_label:<28s} {r['symbol']:<8s} {r['n_trades']:>6d} {r['win_rate']:>5.1f}% "
                  f"{r['pnl_pct']:>+7.1f}% {r['sharpe']:>7.3f} {r['max_drawdown']:>6.1f}% "
                  f"{r['profit_factor']:>6.2f} ${r['expectancy']:>7.0f}")

        # Top by P&L
        top_pnl = significant.nlargest(20, 'pnl_pct')
        print(f"\n💰 TOP 20 BY P&L%:")
        print(f"{'Strategy':<30s} {'Sym':<8s} {'Trades':>6s} {'P&L%':>8s} {'Sharpe':>7s} {'MaxDD':>7s}")
        print(f"{'-'*70}")
        for _, r in top_pnl.iterrows():
            strategy_label = f"{r['combo_names']}" if r['combo_size'] > 1 else r['strategy']
            print(f"  {strategy_label:<28s} {r['symbol']:<8s} {r['n_trades']:>6d} "
                  f"{r['pnl_pct']:>+7.1f}% {r['sharpe']:>7.3f} {r['max_drawdown']:>6.1f}%")

        # By strategy (aggregated)
        print(f"\n📊 STRATEGY AGGREGATES (all symbols, all params):")
        print(f"{'Strategy':<30s} {'Avg P&L%':>9s} {'Median P&L%':>11s} {'Avg Sharp':>9s} {'Avg MaxDD':>9s} {'Trades':>7s} {'Tests':>5s}")
        print(f"{'-'*95}")
        for strat_name in pdf['strategy'].unique():
            sdat = pdf[pdf['strategy'] == strat_name]
            print(f"  {strat_name:<28s} {sdat['pnl_pct'].mean():>+8.1f}% {sdat['pnl_pct'].median():>+10.1f}% "
                  f"{sdat['sharpe'].mean():>9.3f} {sdat['max_drawdown'].mean():>8.1f}% "
                  f"{sdat['n_trades'].sum():>7d} {len(sdat):>5d}")

        # Aggregate by combo_size
        combo_results = pdf[pdf['combo_size'] > 1]
        if len(combo_results) > 0:
            print(f"\n🔗 COMBO SIZE ANALYSIS:")
            print(f"{'Combo Size':>10s} {'Avg P&L%':>9s} {'Avg Sharpe':>10s} {'Avg Win%':>8s} {'Tests':>5s}")
            print(f"{'-'*50}")
            for cs in sorted(combo_results['combo_size'].unique()):
                cdat = combo_results[combo_results['combo_size'] == cs]
                print(f"  {cs:>9d} {cdat['pnl_pct'].mean():>+8.1f}% {cdat['sharpe'].mean():>10.3f} "
                      f"{cdat['win_rate'].mean():>7.1f}% {len(cdat):>5d}")

    print(f"\n✅ Pipeline complete! {len(all_results)} results saved to {RESULTS_TABLE}")
    print(f"   DB: {DB_PATH}")


if __name__ == '__main__':
    main()
