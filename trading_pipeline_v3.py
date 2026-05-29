#!/usr/bin/env python3
"""
TRADING PIPELINE v3 — Correct layered architecture
====================================================
Three layers, three responsibilities:

LAYER 1 — SIGNALS (daily cron, runs nightly)
  Generate directional signals per strategy per symbol.
  Each strategy outputs: BUY / SELL / HOLD + signal_strength (0-100)
  Results → signal_table (one row per symbol per strategy per day)

LAYER 2 — RISK / MONEY MANAGEMENT (applied after Layer 1)
  For every BUY signal from Layer 1:
    - Position size = min(max_pct_portfolio, risk_based_size)
    - risk_based_size = (portfolio_value × max_risk_pct) / ATR(14)
    - Stop loss = entry - (stop_factor × ATR(14))
    - Max holding period check (exit if held > N days and no momentum)
  Every day: check existing positions for stop loss hits (EMERGENCY TRADE)
  Results: entry_price, stop_price, shares, risk_amt per signal

LAYER 3 — PORTFOLIO CONSTRUCTION (weekly/monthly/quarterly cron)
  - Gather all active BUY signals (across all strategies)
  - Score each: signal_strength × conviction_factor
  - Rank by score, apply constraints:
    * Max N positions (e.g. 12-16)
    * Max % per position (5-10%)
    * Heat limit (no more than X% in one sector)
    * Correlation filter (don't add highly correlated positions)
  - Generate target portfolio
  - Compare to current holdings → trades needed
  - Execute rebalance
  Results: target_portfolio, trades_to_execute

SPECIAL — EMERGENCY CRON (daily, runs intraday)
  - Check existing positions against ATR trailing stops
  - If any position hits stop → immediate SELL
  - No strategy vote for exits — pure risk management
  - Also: news-driven emergency exits (if news score drops below threshold)

CADENCE SUMMARY:
  Nightly:  Layer 1 (signals) + Tier 2 scoring update + price data import
  Daily:    Emergency stop check + news check + candidate list update
  Weekly:   Layer 3 (portfolio construction) for tactical rebalance
  Monthly:  Layer 3 for strategic rebalance + review strategy weights
  Quarterly: Full strategy review + parameter optimization

GA/NN/RL INTEGRATION:
  GA: Optimize signal weights (which strategies count more in Layer 1)
  NN: Predict next-week return given current signal state
  RL: Learn optimal rebalance timing and position sizing
  All three operate on the LAYERED output, not on raw price data.

Usage:
  python3 trading_pipeline_v3.py --layer all --mode daily
  python3 trading_pipeline_v3.py --layer 1 --mode nightly
  python3 trading_pipeline_v3.py --layer 2 --mode daily
  python3 trading_pipeline_v3.py --layer 3 --mode weekly
  python3 trading_pipeline_v3.py --emergency  # stop loss check only
"""

import argparse, itertools, json, random, sqlite3, sys, os, time
import datetime
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analysis_results.db')

random.seed(42)
np.random.seed(42)

# =========================================================================
# UTILITY
# ==========================================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def load_prices(symbol, start, end):
    conn = db()
    df = pd.read_sql_query("""
        SELECT price_date, day_open as o, day_high as h,
               day_low as l, day_close as c, volume as v
        FROM stockprices
        WHERE symbol = ? AND price_date BETWEEN ? AND ?
        ORDER BY price_date
    """, conn, params=(symbol, start, end), parse_dates=['price_date'])
    conn.close()
    if df.empty:
        return df
    df = df.set_index('price_date').sort_index()
    for col in ['o','h','l','c','v']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def get_holding_period(df):
    """Days of price data available for each symbol."""
    conn = db()
    rows = conn.execute("""
        SELECT symbol, MIN(price_date) as first_dt, MAX(price_date) as last_dt,
               COUNT(*) as n_days
        FROM stockprices GROUP BY symbol ORDER BY symbol
    """).fetchall()
    conn.close()
    return {r[0]: {'first': r[1], 'last': r[2], 'n': r[3]} for r in rows}

# =========================================================================
# TECHNICAL INDICATORS (numpy-based, fast)
# ==========================================================================

def atr(h, l, c, period=14):
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(np.roll(c, 1) - l)))
    tr[0] = h[0] - l[0]
    return pd.Series(tr, index=np.arange(len(tr))).rolling(period).mean().values

def rsi(c, period=14):
    d = np.diff(c, prepend=c[0])
    g = np.where(d > 0, d, 0.0)
    lo = np.where(d < 0, -d, 0.0)
    gain = pd.Series(g).rolling(period).mean().values
    loss = pd.Series(lo).rolling(period).mean().values
    rs = gain / np.where(loss == 0, 1e-10, loss)
    return 100.0 - (100.0 / (1.0 + rs))

def sma(c, period):
    return pd.Series(c).rolling(period).mean().values

def ema(c, period):
    return pd.Series(c).ewm(span=period).mean().values

def macd(c, fast=12, slow=26, sig=9):
    f = ema(c, fast); s = ema(c, slow)
    macd_line = f - s
    signal = ema(macd_line, sig)
    return macd_line, signal, macd_line - signal

def bollinger(c, period=20, nstd=2):
    m = sma(c, period)
    sd = pd.Series(c).rolling(period).std().values
    upper = m + nstd * sd
    lower = m - nstd * sd
    pct = (c - lower) / np.where((upper - lower) == 0, 1e-10, upper - lower)
    return upper, m, lower, pct

def donchian(h, l, period):
    return pd.Series(h).rolling(period).max().values, pd.Series(l).rolling(period).min().values

def stochastic(h, l, c, period=14, smooth=3):
    low = pd.Series(l).rolling(period).min().values
    high = pd.Series(h).rolling(period).max().values
    k = 100.0 * (c - low) / np.where(high - low == 0, 1e-10, high - low)
    return pd.Series(k).rolling(smooth).mean().values

def zscore(c, period=20):
    m = sma(c, period)
    sd = pd.Series(c).rolling(period).std().values
    return (c - m) / np.where(sd == 0, 1e-10, sd)

def compute_all_indicators(df):
    """Add all indicator columns to DataFrame in-place."""
    c = df['c'].values.astype(float)
    h = df['h'].values.astype(float)
    l = df['l'].values.astype(float)
    n = len(c)
    df['atr_14'] = atr(h, l, c, 14)
    df['atr_20'] = atr(h, l, c, 20)
    df['rsi_14'] = rsi(c, 14)
    for p in [5, 10, 20, 50, 200]:
        df[f'sma_{p}'] = sma(c, p)
    for p in [12, 26]:
        df[f'ema_{p}'] = ema(c, p)
    df['macd'], df['macd_sig'], df['macd_hist'] = macd(c)
    df['bb_upper'], df['bb_mid'], df['bb_lower'], df['bb_pct'] = bollinger(c)
    df['dc_upper_20'], df['dc_lower_20'] = donchian(h, l, 20)
    df['dc_upper_55'], df['dc_lower_55'] = donchian(h, l, 55)
    df['stoch_k'] = stochastic(h, l, c)
    df['zscore_20'] = zscore(c, 20)
    df['roc_10'] = pd.Series(c).pct_change(10).values * 100
    df['roc_20'] = pd.Series(c).pct_change(20).values * 100
    return df

# =========================================================================
# LAYER 1: SIGNAL GENERATORS
# Each returns (signal: 1=BUY, 0=HOLD, -1=SELL, strength: 0-100)
# Applied independently — these are CANDIDATES, not trades.
# =========================================================================

def signal_sma_cross(df, fast=10, slow=50, col='close'):
    """Golden cross / death cross. No position sizing — just direction."""
    sig = np.zeros(len(df))
    fast_s = df[f'sma_{fast}'].values
    slow_s = df[f'sma_{slow}'].values
    c = df['c'].values.astype(float)
    for i in range(1, len(df)):
        if np.isnan(fast_s[i]) or np.isnan(slow_s[i]):
            continue
        if fast_s[i] > slow_s[i] and fast_s[i-1] <= slow_s[i-1]:
            sig[i] = 1  # Golden cross
        elif fast_s[i] < slow_s[i] and fast_s[i-1] >= slow_s[i-1]:
            sig[i] = -1  # Death cross
    return sig, np.abs(sig) * 50  # binary signal strength

def signal_turtle_breakout(df, entry_period=20, exit_period=55):
    """Classic Turtle: buy on 20-day high breakout, sell on 55-day low breakout."""
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    c = df['c'].values.astype(float)
    h = df['h'].values.astype(float)
    l = df['l'].values.astype(float)
    dc_upper, dc_lower = donchian(h, l, entry_period)
    dc_exit_upper, dc_exit_lower = donchian(h, l, exit_period)

    in_long = False
    for i in range(1, len(df)):
        if np.isnan(dc_upper[i-1]):
            continue
        if not in_long and c[i] > dc_upper[i-1]:
            sig[i] = 1
            strength[i] = min(100, 50 + (c[i] - dc_upper[i-1]) / dc_upper[i-1] * 500)
            in_long = True
        elif in_long and c[i] < dc_exit_lower[i-1]:
            sig[i] = -1
            strength[i] = min(100, 50 + (dc_exit_lower[i-1] - c[i]) / c[i] * 500)
            in_long = False
    return sig, strength

def signal_4week(df):
    """4-Week Rule: buy if close > 4-week high, sell if close < 4-week low."""
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    c = df['c'].values.astype(float)
    h = df['h'].values.astype(float)
    l = df['l'].values.astype(float)
    period = 20
    highs = pd.Series(h).rolling(period).max().values
    lows = pd.Series(l).rolling(period).min().values

    in_long = False
    for i in range(1, len(df)):
        if np.isnan(highs[i-1]):
            continue
        if not in_long and c[i] > highs[i-1]:
            sig[i] = 1
            strength[i] = min(100, 60 + (c[i] - highs[i-1]) / highs[i-1] * 300)
            in_long = True
        elif in_long and c[i] < lows[i-1]:
            sig[i] = -1
            strength[i] = min(100, 60)
            in_long = False
    return sig, strength

def signal_bollinger_mean_rev(df):
    """Bollinger mean reversion: buy near lower band + RSI oversold."""
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    c = df['c'].values.astype(float)
    rsi_v = df['rsi_14'].values
    bb_pct_v = df['bb_pct'].values

    in_long = False
    for i in range(1, len(df)):
        if np.isnan(rsi_v[i]):
            continue
        if not in_long and (c[i] <= df['bb_lower'].iloc[i] or bb_pct_v[i] < 0.1) and rsi_v[i] < 35:
            sig[i] = 1
            strength[i] = min(100, 40 + (35 - rsi_v[i]) * 2)
            in_long = True
        elif in_long and (c[i] >= df['bb_mid'].iloc[i] or rsi_v[i] > 65):
            sig[i] = -1
            strength[i] = min(100, 50)
            in_long = False
    return sig, strength

def signal_macd_trend(df):
    """MACD trend following: buy on bullish crossover, sell on bearish."""
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    hist = df['macd_hist'].values
    rsi_v = df['rsi_14'].values

    for i in range(1, len(df)):
        if np.isnan(hist[i]):
            continue
        if hist[i] > 0 and hist[i-1] <= 0:
            sig[i] = 1
            strength[i] = min(100, 40 + abs(hist[i]) * 10)
        elif hist[i] < 0 and hist[i-1] >= 0:
            sig[i] = -1
            strength[i] = min(100, 40 + abs(hist[i]) * 10)
    return sig, strength

def signal_stochastic(df):
    """Stochastic: buy on oversold crossover, sell on overbought crossover."""
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    k = df['stoch_k'].values

    in_long = False
    for i in range(1, len(df)):
        if np.isnan(k[i]):
            continue
        if not in_long and k[i] > 20 and k[i-1] <= 20:
            sig[i] = 1
            strength[i] = 50
            in_long = True
        elif in_long and k[i] < 80 and k[i-1] >= 80:
            sig[i] = -1
            strength[i] = 50
            in_long = False
    return sig, strength

def signal_rsi_momentum(df):
    """RSI: buy on oversold (RSI<30) with positive ROC, sell on overbought."""
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    rsi_v = df['rsi_14'].values
    roc_v = df['roc_10'].values

    for i in range(1, len(df)):
        if np.isnan(rsi_v[i]):
            continue
        if rsi_v[i] < 30 and (np.isnan(roc_v[i]) or roc_v[i] > -5):
            sig[i] = 1
            strength[i] = min(100, 30 + (30 - rsi_v[i]) * 3)
        elif rsi_v[i] > 70:
            sig[i] = -1
            strength[i] = min(100, 30 + (rsi_v[i] - 70) * 3)
    return sig, strength

def signal_zscore_reversion(df):
    """Z-score mean reversion: buy when z < -2, sell when z > +2."""
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    zs = df['zscore_20'].values

    in_long = False
    for i in range(1, len(df)):
        if np.isnan(zs[i]):
            continue
        if not in_long and zs[i] < -2.0:
            sig[i] = 1
            strength[i] = min(100, 40 + abs(zs[i]) * 15)
            in_long = True
        elif in_long and zs[i] >= 0.0:
            sig[i] = -1
            strength[i] = 50
            in_long = False
    return sig, strength

def signal_donchian_breakout(df, period=20):
    """Donchian breakout — different from Turtle in that it doesn't use a slow exit."""
    sig = np.zeros(len(df))
    strength = np.zeros(len(df))
    c = df['c'].values.astype(float)
    upper, lower = donchian(df['h'].values, df['l'].values, period)

    in_long = False
    for i in range(1, len(df)):
        if np.isnan(upper[i-1]):
            continue
        if not in_long and c[i] > upper[i-1]:
            sig[i] = 1
            strength[i] = min(100, 50)
            in_long = True
        elif in_long and c[i] < lower[i-1]:
            sig[i] = -1
            strength[i] = 50
            in_long = False
    return sig, strength

# Registry: strategy_name → function
SIGNAL_STRATEGIES = {
    'sma_10_50':    lambda df: signal_sma_cross(df, 10, 50),
    'sma_20_50':    lambda df: signal_sma_cross(df, 20, 50),
    'sma_50_200':   lambda df: signal_sma_cross(df, 50, 200),
    'turtle_20':    lambda df: signal_turtle_breakout(df, 20, 55),
    '4week':        signal_4week,
    'bollinger_mr': signal_bollinger_mean_rev,
    'macd_trend':   signal_macd_trend,
    'stochastic':   signal_stochastic,
    'rsi_momentum': signal_rsi_momentum,
    'zscore_rev':   signal_zscore_reversion,
    'donchian_20':  lambda df: signal_donchian_breakout(df, 20),
}

# =========================================================================
# LAYER 2: RISK / MONEY MANAGEMENT
# Applied uniformly to all signals regardless of source strategy.
# =========================================================================

def calc_position_size(portfolio_value, max_pct, atr_val, max_risk_pct=0.01,
                         stop_factor=2.0, min_shares=1, price=0):
    """
    Two constraints — take the more conservative:
    1. Max % of portfolio: portfolio_value × max_pct / price
    2. Risk-based: (portfolio_value × max_risk_pct) / (stop_factor × ATR)
    Returns: (shares, stop_price, risk_amount)
    """
    if price <= 0 or np.isnan(atr_val) or atr_val <= 0:
        return 0, 0, 0

    # Constraint 1: max % portfolio
    size_by_pct = int(portfolio_value * max_pct / price)

    # Constraint 2: risk-based
    risk_per_share = stop_factor * atr_val
    if risk_per_share <= 0:
        return 0, 0, 0
    risk_amount = portfolio_value * max_risk_pct
    size_by_risk = int(risk_amount / risk_per_share)

    shares = max(min_shares, min(size_by_pct, size_by_risk))
    actual_risk = shares * risk_per_share
    stop_price = price - stop_factor * atr_val  # long-only for now

    return shares, stop_price, actual_risk

# =========================================================================
# CREATE TABLES
# =========================================================================

def create_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS layer1_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        symbol TEXT,
        strategy TEXT,
        price_date TEXT,
        signal INTEGER,          -- 1=BUY, 0=HOLD, -1=SELL
        strength REAL,           -- 0-100
        close REAL,
        atr_14 REAL,
        rsi_14 REAL,
        UNIQUE(symbol, strategy, price_date)
    );
    CREATE INDEX IF NOT EXISTS idx_l1_sym_strat ON layer1_signals(symbol, strategy, price_date);
    CREATE INDEX IF NOT EXISTS idx_l1_date ON layer1_signals(price_date);
    CREATE INDEX IF NOT EXISTS idx_l1_signal ON layer1_signals(signal, strength);

    CREATE TABLE IF NOT EXISTS layer2_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        symbol TEXT,
        strategy TEXT,           -- which signal strategy triggered this
        entry_date TEXT,
        entry_price REAL,
        shares INTEGER,
        stop_price REAL,
        risk_amount REAL,
        max_risk_pct REAL,
        stop_factor REAL,
        atr_14_at_entry REAL,
        status TEXT DEFAULT 'OPEN',  -- OPEN, CLOSED_STOP, CLOSED_EXIT
        exit_date TEXT,
        exit_price REAL,
        pnl REAL
    );
    CREATE INDEX IF NOT EXISTS idx_l2_symbol ON layer2_positions(symbol);
    CREATE INDEX IF NOT EXISTS idx_l2_status ON layer2_positions(status);

    CREATE TABLE IF NOT EXISTS layer3_portfolios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        rebalance_date TEXT,
        mode TEXT,               -- weekly, monthly, quarterly, emergency
        capital REAL,
        target_json TEXT,        -- JSON of target positions
        current_json TEXT,       -- JSON of current holdings
        trades_json TEXT,        -- JSON of trades to execute
        constraints_json TEXT    -- applied rules: max_pos, max_pct, etc
    );

    CREATE TABLE IF NOT EXISTS layer3_candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        symbol TEXT,
        n_buy_signals INTEGER,   -- how many strategies say BUY
        avg_strength REAL,       -- average strength across BUY signals
        max_strength REAL,       -- highest single signal strength
        consensus_pct REAL,      -- % of active strategies saying BUY
        price REAL,
        atr_14 REAL,
        score REAL,              -- composite: avg_strength * consensus_pct / 100
        rank INTEGER             -- 1 = highest score
    );
    CREATE INDEX IF NOT EXISTS idx_l3c_score ON layer3_candidates(score DESC);

    CREATE TABLE IF NOT EXISTS strategy_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        strategy TEXT,
        symbol TEXT,
        n_entries INTEGER,
        n_exits INTEGER,
        win_rate REAL,
        avg_win REAL,
        avg_loss REAL,
        expectancy REAL,
        profit_factor REAL,
        total_pnl REAL,
        avg_holding_days REAL,
        UNIQUE(strategy, symbol, ts)
    );
    """)
    conn.commit()

# =========================================================================
# LAYER 1 RUNNER
# =========================================================================

def run_layer1(symbols, start, end, strategies=None):
    """
    For each symbol × strategy, generate signals.
    Store all in layer1_signals table.
    Returns: {symbol: {strategy: (signals, strengths)}}
    """
    if strategies is None:
        strategies = list(SIGNAL_STRATEGIES.keys())

    conn = db()
    create_tables(conn)

    results = {}
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    rows = []

    for symbol in symbols:
        df = load_prices(symbol, start, end)
        if len(df) < 60:
            continue
        df = compute_all_indicators(df)
        results[symbol] = {}

        for strat_name, strat_fn in strategies.items() if isinstance(strategies, dict) else \
                [(s, SIGNAL_STRATEGIES[s]) for s in strategies]:
            try:
                sig, strength = strat_fn(df)
                results[symbol][strat_name] = (sig, strength)

                for i in range(len(df)):
                    if sig[i] != 0:  # only store non-HOLD
                        rows.append((
                            ts, symbol, str(strat_name),
                            str(df.index[i])[:10],
                            int(sig[i]),
                            round(float(strength[i]), 2),
                            round(float(df['c'].iloc[i]), 4) if not np.isnan(df['c'].iloc[i]) else None,
                            round(float(df['atr_14'].iloc[i]), 4) if not np.isnan(df['atr_14'].iloc[i]) else None,
                            round(float(df['rsi_14'].iloc[i]), 4) if not np.isnan(df['rsi_14'].iloc[i]) else None,
                        ))
            except Exception as e:
                print(f"  ERROR {symbol} × {strat_name}: {e}")

    # Batch insert
    if rows:
        conn.executemany("""
            INSERT OR REPLACE INTO layer1_signals
            (ts, symbol, strategy, price_date, signal, strength, close, atr_14, rsi_14)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()

    conn.close()
    print(f"  Layer 1: {len(rows)} signals generated for {len(results)} symbols")
    return results

# =========================================================================
# WALK-FORWARD SIMULATION ENGINE
# The core backtest loop — one day at a time, strictly history-blind.
#
# For each trading day:
#   1. Look at signals generated UP TO this day (no future peeking)
#   2. Check open positions for stop-loss hits (EMERGENCY — Layer 2)
#   3. If this is a rebalance day, construct target portfolio (Layer 3)
#   4. Execute trades (buy new candidates, sell to make room)
#   5. Record portfolio state
#
# After the walk completes, compute performance metrics.
# THIS is what we sweep parameters over.
# ==========================================================================

def run_walkforward(config, conn=None):
    """
    Run a complete walk-forward simulation for one parameter set.
    Returns: {portfolio: [{date, value, cash, positions}], trades: [...], metrics: {...}}

    This is the ONLY function that should be called for backtesting.
    It is strictly history-blind — on day N, only days 1..N are visible.
    """
    symbols       = config['symbols']
    strat_names   = config['strategies']
    start         = config['start']
    end           = config['end']
    capital       = config.get('initial_capital', 100000)
    commission    = config.get('commission', 9.95)
    max_pct       = config.get('max_pct_portfolio', 0.05)
    max_risk_pct  = config.get('max_risk_pct', 0.01)
    max_positions = config.get('max_positions', 12)
    stop_factor   = config.get('stop_factor', 2.0)
    rebalance_days = config.get('rebalance_days', 30)
    min_score    = config.get('min_score', 25.0)

    if conn is None:
        conn = db()
    own_conn = conn is None

    # ── Load all price data AND precompute all signals ──
    # This is the ONLY place future data is loaded, and it's
    # done once upfront for efficiency. On each simulation day
    # we slice df.loc[:current_day] so the strategy functions
    # only see history.
    symbol_data = {}
    for sym in symbols:
        df = load_prices(sym, start, end)
        if len(df) < 60:
            continue
        df = compute_all_indicators(df)
        symbol_data[sym] = df

    symbols = list(symbol_data.keys())
    if not symbols:
        return {'error': 'no symbols with data'}

    # ── Build unified date index (all trading days across all symbols) ──
    all_dates = set()
    for df in symbol_data.values():
        all_dates.update(df.index.tolist())
    all_dates = sorted(all_dates)

    # ── Simulation state ──
    cash = capital
    positions = {}  # sym → {shares, entry_price, stop_price, entry_date, strategy}
    trades = []
    portfolio_history = []
    last_rebalance = all_dates[0] - timedelta(days=1) if all_dates else None

    for day_idx, current_date in enumerate(all_dates):
        # ── STEP 1: Check stops (EMERGENCY layer) — run every day ──
        for sym in list(positions.keys()):
            if sym in symbol_data and current_date in symbol_data[sym].index:
                price = float(symbol_data[sym].loc[current_date, 'c'])
                pos = positions[sym]
                if price <= pos['stop_price']:
                    # STOP HIT — sell immediately
                    proceeds = pos['shares'] * price - commission
                    pnl = proceeds - (pos['shares'] * pos['entry_price'] + commission)
                    cash += proceeds
                    trades.append({
                        'date': str(current_date)[:10], 'symbol': sym,
                        'action': 'STOP', 'shares': pos['shares'],
                        'price': round(price, 2), 'pnl': round(pnl, 2)
                    })
                    del positions[sym]

        # ── STEP 2: Is it time to rebalance? ──
        days_since = (current_date - last_rebalance).days
        do_rebalance = days_since >= rebalance_days

        if do_rebalance:
            last_rebalance = current_date

            # ── STEP 2a: Generate signals for this day (history-blind) ──
            # Each symbol × each strategy gets a look at only the data up to today.
            # We slice df.loc[:current_date] so NO future data leaks in.
            candidates = []
            for sym, df in symbol_data.items():
                if current_date not in df.index:
                    continue
                hist = df.loc[:current_date]  # ← STRICT CUT-OFF

                buy_votes = 0
                sell_votes = 0
                buy_strengths = []

                for strat_name in strat_names:
                    if strat_name not in SIGNAL_STRATEGIES:
                        continue
                    try:
                        sig, strength = SIGNAL_STRATEGIES[strat_name](hist)
                        if len(sig) > 0 and sig[-1] == 1:
                            buy_votes += 1
                            buy_strengths.append(strength[-1] if len(strength) > 0 else 50)
                        elif len(sig) > 0 and sig[-1] == -1:
                            sell_votes += 1
                    except Exception:
                        pass

                n_strats = len(strat_names)
                price = float(df.loc[current_date, 'c'])
                atr_val = float(df.loc[current_date, 'atr_14']) if not np.isnan(df.loc[current_date, 'atr_14']) else 0

                consensus = buy_votes / n_strats * 100 if n_strats > 0 else 0
                avg_str = np.mean(buy_strengths) if buy_strengths else 0
                score = avg_str * (consensus / 100)

                # Also compute sell consensus for existing positions
                sell_consensus = sell_votes / n_strats * 100 if n_strats > 0 else 0

                candidates.append({
                    'symbol': sym,
                    'buy_votes': buy_votes,
                    'sell_votes': sell_votes,
                    'sell_consensus': sell_consensus,
                    'avg_strength': round(avg_str, 2),
                    'consensus': round(consensus, 1),
                    'score': round(score, 2),
                    'price': price,
                    'atr_14': atr_val,
                    'in_position': sym in positions,
                })

            # ── STEP 2b: Sell candidates that any strategy says SELL ──
            # (All-else being equal, if the buy/sell consensus tilts negative, trim)
            for c in candidates:
                if c['in_position'] and c['sell_consensus'] >= 50:
                    sym = c['symbol']
                    pos = positions[sym]
                    price = c['price']
                    proceeds = pos['shares'] * price - commission
                    pnl = proceeds - (pos['shares'] * pos['entry_price'] + commission)
                    cash += proceeds
                    trades.append({
                        'date': str(current_date)[:10], 'symbol': sym,
                        'action': 'SELL', 'shares': pos['shares'],
                        'price': round(price, 2), 'pnl': round(pnl, 2),
                        'reason': f'sell_consensus={c["sell_consensus"]:.0f}%'
                    })
                    del positions[sym]
                    c['in_position'] = False

            # ── STEP 2c: Rank BUY candidates ──
            buy_candidates = [c for c in candidates if not c['in_position'] and c['score'] >= min_score]
            buy_candidates.sort(key=lambda x: x['score'], reverse=True)

            # ── STEP 2d: Open new positions (Layer 2 position sizing) ──
            current_n = len(positions)
            for c in buy_candidates:
                if current_n >= max_positions:
                    break

                sym = c['symbol']
                price = c['price']
                atr_val = c['atr_14']

                if atr_val <= 0 or np.isnan(atr_val):
                    continue

                # Portfolio value including current positions
                pv = cash
                for s, p in positions.items():
                    if s in symbol_data and current_date in symbol_data[s].index:
                        pv += p['shares'] * float(symbol_data[s].loc[current_date, 'c'])

                shares, stop_price, risk_amt = calc_position_size(
                    pv, max_pct, atr_val, max_risk_pct, stop_factor, price=price
                )
                if shares < 1:
                    continue

                cost = shares * price + commission
                if cost > cash:
                    shares = max(1, int((cash - commission) / price))
                    if shares < 1:
                        continue
                    cost = shares * price + commission

                cash -= cost
                positions[sym] = {
                    'shares': shares,
                    'entry_price': price,
                    'stop_price': stop_price,
                    'entry_date': str(current_date)[:10],
                    'strategy': f'consensus_{c["buy_votes"]}of{len(strat_names)}'
                }
                trades.append({
                    'date': str(current_date)[:10], 'symbol': sym,
                    'action': 'BUY', 'shares': shares,
                    'price': round(price, 2), 'pnl': 0
                })
                current_n += 1

        # ── STEP 3: Record portfolio value ──
        pv = cash
        for sym, pos in positions.items():
            if sym in symbol_data and current_date in symbol_data[sym].index:
                pv += pos['shares'] * float(symbol_data[sym].loc[current_date, 'c'])

        portfolio_history.append({
            'date': str(current_date)[:10],
            'value': round(pv, 2),
            'cash': round(cash, 2),
            'n_positions': len(positions),
        })

    # ── Close any remaining open positions at last available price ──
    last_date = all_dates[-1] if all_dates else None
    for sym, pos in list(positions.items()):
        if sym in symbol_data and last_date in symbol_data[sym].index:
            price = float(symbol_data[sym].loc[last_date, 'c'])
            proceeds = pos['shares'] * price - commission
            pnl = proceeds - (pos['shares'] * pos['entry_price'] + commission)
            cash += proceeds
            trades.append({
                'date': str(last_date)[:10], 'symbol': sym,
                'action': 'FINAL', 'shares': pos['shares'],
                'price': round(price, 2), 'pnl': round(pnl, 2)
            })

    # ── Compute performance metrics ──
    final_value = cash  # all closed
    values = [p['value'] for p in portfolio_history]
    peak = values[0] if values else capital
    max_dd = 0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

    pnl = final_value - capital
    pnl_pct = (pnl / capital) * 100

    returns = pd.Series(values).pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() > 0 else 0

    # Trade stats
    buy_trades = [t for t in trades if t['action'] == 'BUY']
    sell_trades = [t for t in trades if t['action'] in ('SELL', 'STOP', 'FINAL')]
    wins = [t for t in sell_trades if t.get('pnl', 0) > 0]
    losses = [t for t in sell_trades if t.get('pnl', 0) <= 0]
    win_rate = len(wins) / len(sell_trades) * 100 if sell_trades else 0
    avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
    expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss) if sell_trades else 0
    total_pnl = sum(t.get('pnl', 0) for t in sell_trades)

    metrics = {
        'final_value': round(final_value, 2),
        'pnl': round(pnl, 2),
        'pnl_pct': round(pnl_pct, 2),
        'max_drawdown': round(max_dd, 2),
        'sharpe': round(sharpe, 4),
        'n_trades': len(trades),
        'n_buys': len(buy_trades),
        'n_sells': len(sell_trades),
        'win_rate': round(win_rate, 1),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'expectancy': round(expectancy, 2),
        'total_pnl_from_trades': round(total_pnl, 2),
    }

    return {
        'config': config,
        'trades': trades,
        'portfolio_history': portfolio_history,
        'metrics': metrics,
    }


# =========================================================================
# PARAMETER SWEEP — calls run_walkforward for each config combination
# =========================================================================

def run_parameter_sweep(symbols, strategies, base_config, sweep_params, output_table):
    """
    Sweep through parameter combinations, running one walk-forward per combo.
    Each combo gets its own timestamped portfolio in the output table.
    """
    conn = db()
    create_tables(conn)

    # Build sweep grid
    param_keys = list(sweep_params.keys())
    param_values = [sweep_params[k] for k in param_keys]
    combos = list(itertools.product(*param_values))

    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    results = []
    t0 = time.time()

    for i, combo in enumerate(combos):
        cfg = dict(base_config)
        name_parts = []
        for k, v in zip(param_keys, combo):
            cfg[k] = v
            name_parts.append(f"{k}={v}")
        cfg['name'] = '_'.join(name_parts)
        cfg['symbols'] = symbols
        cfg['strategies'] = strategies

        try:
            result = run_walkforward(cfg, conn=conn)
            if 'error' in result:
                continue

            m = result['metrics']
            results.append((cfg['name'], m))

            # Save to DB
            conn.execute(f"""
                INSERT INTO {output_table}
                (ts, config_name, strategies, start_date, end_date,
                 initial_capital, max_pct_portfolio, rebalance_days,
                 max_risk_pct, stop_factor, max_positions,
                 final_value, pnl, pnl_pct, n_trades, win_rate,
                 avg_win, avg_loss, expectancy,
                 total_pnl_from_trades, max_drawdown, sharpe,
                 params_json, portfolio_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts, cfg['name'], '+'.join(strategies),
                cfg['start'], cfg['end'],
                cfg.get('initial_capital', 100000),
                cfg.get('max_pct_portfolio', 0.05),
                cfg.get('rebalance_days', 30),
                cfg.get('max_risk_pct', 0.01),
                cfg.get('stop_factor', 2.0),
                cfg.get('max_positions', 12),
                m['final_value'], m['pnl'], m['pnl_pct'],
                m['n_trades'], m['win_rate'],
                m['avg_win'], m['avg_loss'], m['expectancy'],
                m['total_pnl_from_trades'], m['max_drawdown'], m['sharpe'],
                json.dumps(cfg),
                json.dumps(result['portfolio_history'][-30:])  # last 30 days
            ))

            if (i + 1) % 50 == 0:
                conn.commit()
                elapsed = time.time() - t0
                print(f"    [{i+1}/{len(combos)}] {elapsed:.0f}s, best_sharpe={max(r[1]['sharpe'] for r in results):.3f}")

        except Exception as e:
            print(f"    ERROR {cfg['name']}: {e}")

    conn.commit()
    conn.close()
    elapsed = time.time() - t0

    # Sort by Sharpe
    results.sort(key=lambda x: x[1]['sharpe'], reverse=True)
    return results, elapsed


# =========================================================================
# COMBO SWEEP — try pairs/triples/quads of strategies via consensus voting
# =========================================================================

def run_combo_sweep(symbols, base_config, sweep_params, output_table):
    """
    For each combination of N strategies (N=1,2,3,4), run walk-forward.
    The key difference from run_parameter_sweep: multiple strategies vote
    on each signal, and we require consensus before entering.
    """
    all_strategies = list(SIGNAL_STRATEGIES.keys())
    results = []

    for combo_size in [1, 2, 3, 4]:
        combos = list(itertools.combinations(all_strategies, combo_size))
        print(f"\n  Combo size {combo_size}: {len(combos)} combinations to test")

        for ci, combo in enumerate(combos):
            strat_names = list(combo)
            try:
                # For single strategies, do a full sweep
                if combo_size == 1:
                    sweep_results, _ = run_parameter_sweep(
                        symbols, strat_names, base_config, sweep_params, output_table
                    )
                    results.extend(sweep_results)
                else:
                    # For combos, run with fixed params (rebalance=30, max_risk=1%)
                    cfg = dict(base_config)
                    cfg['strategies'] = strat_names
                    cfg['rebalance_days'] = 30
                    cfg['stop_factor'] = 2.0
                    cfg['max_risk_pct'] = 0.01
                    cfg['name'] = f"combo{combo_size}_{'_'.join(strat_names)}"
                    cfg['symbols'] = symbols

                    conn = db()
                    result = run_walkforward(cfg, conn=conn)
                    conn.close()

                    if 'error' not in result:
                        m = result['metrics']
                        results.append((cfg['name'], m))
            except Exception as e:
                print(f"    ERROR combo {combo}: {e}")

            if (ci + 1) % 20 == 0:
                print(f"    [{ci+1}/{len(combos)}] done")

    results.sort(key=lambda x: x[1]['sharpe'], reverse=True)
    return results


# =========================================================================
# MAIN — orchestrate the full pipeline
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Trading Pipeline v3 — Walk-Forward Layered Architecture")
    parser.add_argument('--start', default='2020-01-01')
    parser.add_argument('--end', default=None)
    parser.add_argument('--symbols', default=None, help='Comma-separated')
    parser.add_argument('--strategies', default=None)
    parser.add_argument('--capital', type=float, default=100000)
    parser.add_argument('--sweep', action='store_true', help='Run full parameter sweep')
    parser.add_argument('--combos', action='store_true', help='Run combo sweep')
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--output-table', default='pipeline_v3_walkforward')
    args = parser.parse_args()

    if args.end is None:
        args.end = str(datetime.date.today())

    # Get symbols
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
    else:
        conn = db()
        rows = conn.execute("""
            SELECT DISTINCT symbol FROM stockprices
            WHERE price_date BETWEEN ? AND ?
            GROUP BY symbol HAVING COUNT(*) >= 60
            ORDER BY symbol
        """, (args.start, args.end)).fetchall()
        conn.close()
        symbols = [r[0] for r in rows]

    # Create output table
    conn = db()
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {args.output_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            config_name TEXT,
            strategies TEXT,
            start_date TEXT,
            end_date TEXT,
            initial_capital REAL,
            max_pct_portfolio REAL,
            rebalance_days INTEGER,
            max_risk_pct REAL,
            stop_factor REAL,
            max_positions INTEGER,
            final_value REAL,
            pnl REAL,
            pnl_pct REAL,
            n_trades INTEGER,
            win_rate REAL,
            avg_win REAL,
            avg_loss REAL,
            expectancy REAL,
            total_pnl_from_trades REAL,
            max_drawdown REAL,
            sharpe REAL,
            params_json TEXT,
            portfolio_json TEXT
        )
    """)
    conn.commit()
    conn.close()

    base_config = {
        'start': args.start,
        'end': args.end,
        'initial_capital': args.capital,
        'commission': 9.95,
    }

    if args.quick:
        sweep_params = {
            'max_pct_portfolio': [0.05, 0.10],
            'rebalance_days': [30],
            'stop_factor': [2.0],
            'max_risk_pct': [0.01],
            'max_positions': [8, 12],
        }
    else:
        sweep_params = {
            'max_pct_portfolio': [0.02, 0.05, 0.10, 0.15, 0.20],
            'rebalance_days': [7, 14, 30, 90],
            'stop_factor': [1.5, 2.0, 2.5, 3.0],
            'max_risk_pct': [0.005, 0.01, 0.02],
            'max_positions': [4, 8, 12, 16],
        }

    strat_list = None
    if args.strategies:
        strat_list = [s.strip() for s in args.strategies.split(',')]
    else:
        strat_list = list(SIGNAL_STRATEGIES.keys())

    print("=" * 70)
    print("TRADING PIPELINE v3 — Walk-Forward Backtest")
    print("=" * 70)
    print(f"  Period: {args.start} → {args.end}")
    print(f"  Symbols: {len(symbols)} — {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
    print(f"  Strategies: {', '.join(strat_list)}")
    print(f"  Capital: ${args.capital:,.0f}")
    print(f"  Output: {args.output_table}")
    print()

    if args.sweep or not args.combos:
        print(f"── PARAMETER SWEEP ({len(strat_list)} strategies × {len(list(itertools.product(*sweep_params.values())))} combos each) ──")
        results, elapsed = run_parameter_sweep(
            symbols, strat_list, base_config, sweep_params, args.output_table
        )
        print(f"\n  Sweep complete: {len(results)} results in {elapsed:.0f}s")

        print("\nTOP 10 (by Sharpe):")
        print(f"  {'#':>3} {'Sharpe':>7} {'P&L%':>7} {'MaxDD':>7} {'Trades':>6}  Config")
        for i, (name, m) in enumerate(results[:10], 1):
            print(f"  {i:3d} {m['sharpe']:7.3f} {m['pnl_pct']:7.1f} {m['max_drawdown']:7.1f} {m['n_trades']:6d}  {name}")

    if args.combos:
        print(f"\n── COMBO SWEEP (consensus voting across strategies) ──")
        combo_results = run_combo_sweep(symbols, base_config, sweep_params, args.output_table)

        print("\nTOP 10 COMBOS (by Sharpe):")
        print(f"  {'#':>3} {'Sharpe':>7} {'P&L%':>7} {'MaxDD':>7} {'Trades':>6}  Config")
        for i, (name, m) in enumerate(combo_results[:10], 1):
            print(f"  {i:3d} {m['sharpe']:7.3f} {m['pnl_pct']:7.1f} {m['max_drawdown']:7.1f} {m['n_trades']:6d}  {name}")

        # Merge
        all_results = results + combo_results if args.sweep else combo_results
    else:
        all_results = results

    print(f"\n── SUMMARY ──")
    print(f"  Total walk-forward runs: {len(all_results)}")
    if all_results:
        best = all_results[0]
        print(f"  Best: {best[0]} → Sharpe={best[1]['sharpe']:.3f} P&L={best[1]['pnl_pct']:.1f}% DD={best[1]['max_drawdown']:.1f}%")

    # Save all results JSON
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pipeline_v3_results.json')
    with open(json_path, 'w') as f:
        json.dump({
            'period': f'{args.start} → {args.end}',
            'symbols': symbols,
            'strategies': strat_list,
            'n_results': len(all_results),
            'top_20': [{'name': n, **m} for n, m in all_results[:20]],
        }, f, indent=2, default=str)
    print(f"  Results saved to: {json_path}")


if __name__ == '__main__':
    main()
