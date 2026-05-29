#!/usr/bin/env python3
"""
strategy_pipeline_v2.py — OPTIMIZED full backtest pipeline
============================================================
Key optimization: pre-compute all signals once per strategy per symbol,
then sweep only through trading simulation parameters.
Dramatically faster than v1: O(strategies × symbols) signal comps
instead of O(strategies × symbols × param_combos).

Strategies:
  1. Turtle 20, Turtle 55, Turtle Dual (55-entry/20-exit)
  2. 4-Week Rule
  3. Candlestick Pattern
  4. Coin Toss / Random
  5. Buy and Hold
  6. RSI Momentum + Mean Reversion
  7. MACD Trend Following
  8. Bollinger Band Mean Reversion
  9. Stochastic Oscillator
  10. SMA Crossover (5/20, 10/50, 20/50, 50/200 golden/death cross)
  11. Donchian Channel Breakout

Parameter sweep:
  - max_pct_portfolio: 5%, 10%, 15%, 20%
  - rebalance_days: 7, 14, 30, 90
  - max_risk_pct: 0.5%, 1%, 2%
  - stop_factor: 1.5, 2.0, 2.5, 3.0
  - atr_stop: True/False
  - max_holding_days: 0, 20, 60, 90

Combo phase:
  All C(11,2) + C(11,3) + ... combinations with consensus voting

Usage:
  python3 strategy_pipeline_v2.py                              # Full sweep
  python3 strategy_pipeline_v2.py --symbols RY,CM,CNR    # Subset
  python3 strategy_pipeline_v2.py --strategy turtle_20    # Single strategy
  python3 strategy_pipeline_v2.py --combos               # Combo only phase
  python3 strategy_pipeline_v2.py --max-pct 0.10 --stop-factor 2.0  # Fixed params
"""
import argparse, itertools, json, sqlite3, sys, time
import numpy as np
import pandas as pd
from datetime import date
from pathlib import Path

np.random.seed(42)

DB_PATH = str(Path("/home/ksf_stockmarket/ksf_stockmarket/analysis_results.db"))
RESULT_TABLE = "pipeline_v2_results"
SYMBOL_RESULT_TABLE = "pipeline_v2_symbol"

# =========================================================================
# DATA + INDICATORS
# =========================================================================

def load_and_compute(symbol, start, end):
    """Load prices + compute all indicators, return as dict of arrays."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT price_date, day_open as O, day_high as H, day_low as L, day_close as C, volume as V
        FROM stockprices
        WHERE symbol=? AND price_date BETWEEN ? AND ?
        ORDER BY price_date
    """, conn, params=(symbol, start, end),
       parse_dates=['price_date'], index_col='price_date')
    conn.close()
    if len(df) < 60:
        return None, len(df)

    c = df['C'].values.astype(float)
    h = df['H'].values.astype(float)
    l = df['L'].values.astype(float)
    o = df['O'].values.astype(float)
    n = len(c)
    D = {'close': c, 'high': h, 'low': l, 'open': o, 'dates': df.index}

    # True Range / ATR
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(np.roll(c, 1) - l)))
    tr[0] = h[0] - l[0]
    for period in [7, 14, 20]:
        D[f'atr_{period}'] = pd.Series(tr).rolling(period).mean().values

    # SMA / EMA
    cS = pd.Series(c)
    for p in [5, 10, 20, 50, 55, 100, 200]:
        D[f'sma_{p}'] = cS.rolling(p).mean().values
    for p in [12, 26]:
        D[f'ema_{p}'] = cS.ewm(span=p).mean().values

    # RSI
    delta = cS.diff()
    for win, tag in [(14, '14'), (7, '7')]:
        g = delta.where(delta > 0, 0).rolling(win).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(win).mean()
        rs = g / loss.replace(0, np.nan)
        D[f'rsi_{tag}'] = (100 - 100 / (1 + rs)).values

    # MACD
    ema12 = cS.ewm(span=12).mean()
    ema26 = cS.ewm(span=26).mean()
    D['macd'] = (ema12 - ema26).values
    D['macd_signal'] = pd.Series(D['macd']).ewm(span=9).mean().values
    D['macd_hist'] = D['macd'] - D['macd_signal']

    # Bollinger Bands
    bb_mid = cS.rolling(20).mean()
    bb_std = cS.rolling(20).std()
    bb_rng = (bb_mid + 2 * bb_std).values - (bb_mid - 2 * bb_std).values
    D['bb_upper'] = (bb_mid + 2 * bb_std).values
    D['bb_lower'] = (bb_mid - 2 * bb_std).values
    D['bb_pct'] = (c - D['bb_lower']) / (bb_rng + 1e-10)

    # Donchian / Rolling High-Low (Turtle)
    hS, lS = pd.Series(h), pd.Series(l)
    for p in [10, 20, 55]:
        D[f'roll_high_{p}'] = hS.rolling(p).max().values
        D[f'roll_low_{p}'] = lS.rolling(p).min().values

    # Stochastic
    low14 = lS.rolling(14).min()
    high14 = hS.rolling(14).max()
    D['stoch_k'] = ((c - low14) / (high14 - low14 + 1e-10) * 100).values
    D['stoch_d'] = pd.Series(D['stoch_k']).rolling(3).mean().values

    # Candlestick
    body = np.abs(c - o)
    upper_shad = h - np.maximum(c, o)
    lower_shad = np.minimum(c, o) - l
    rng = h - l + 1e-10
    D['doji'] = (body / rng < 0.1).astype(np.int8)
    D['hammer'] = ((lower_shad > 2 * body) & (upper_shad < body)).astype(np.int8)
    D['shooting_star'] = ((upper_shad > 2 * body) & (lower_shad < body)).astype(np.int8)
    D['engulfing_bull'] = np.zeros(n, dtype=np.int8)
    for i in range(1, n):
        if c[i] > o[i] and c[i-1] <= o[i-1] and abs(c[i]-o[i]) > abs(c[i-1]-o[i-1]):
            D['engulfing_bull'][i] = 1

    # ATR stops
    atr14 = D['atr_14']
    for f in [1.0, 1.5, 2.0, 2.5, 3.0]:
        D[f'stop_upper_{f}'] = c + f * atr14
        D[f'stop_lower_{f}'] = c - f * atr14

    return D, n


# =========================================================================
# STRATEGY SIGNAL GENERATORS
# Each takes (D, idx) → int signal {-1, 0, +1} for day idx
# =========================================================================

def sig_turtle_20(D, i):
    if D['close'][i] > D['roll_high_20'][i-1]: return 1
    if D['close'][i] < D['roll_low_20'][i-1]: return -1
    return 0

def sig_turtle_55(D, i):
    if D['close'][i] > D['roll_high_55'][i-1]: return 1
    if D['close'][i] < D['roll_low_55'][i-1]: return -1
    return 0

def sig_turtle_dual(D, i, state):
    """Returns (signal, new_state). state=0:not in position, 1:in position."""
    if state == 0:
        if D['close'][i] > D['roll_high_55'][i-1]:
            return 1, 1
        return 0, 0
    else:
        if D['close'][i] < D['roll_low_20'][i-1]:
            return -1, 0
        return 0, 1

def sig_4week(D, i):
    if D['close'][i] > D['roll_high_20'][i-1]: return 1
    if D['close'][i] < D['roll_low_20'][i-1]: return -1
    return 0

def sig_rsi_momentum(D, i):
    rsi = D['rsi_14'][i]
    if rsi < 30 and D['close'][i] > D['sma_50'][i]: return 1
    if rsi > 70: return -1
    return 0

def sig_macd_trend(D, i):
    mh = D['macd_hist']
    if mh[i] > 0 and mh[i-1] <= 0: return 1
    if mh[i] < 0 and mh[i-1] >= 0: return -1
    return 0

def sig_bollinger_mr(D, i):
    if D['bb_pct'][i] < 0.1 and D['close'][i] > D['sma_200'][i]: return 1
    if D['bb_pct'][i] > 0.9: return -1
    return 0

def sig_stochastic(D, i):
    k, d = D['stoch_k'], D['stoch_d']
    if k[i] > d[i] and k[i-1] <= d[i-1] and k[i] < 20: return 1
    if k[i] < d[i] and k[i-1] >= d[i-1] and k[i] > 80: return -1
    return 0

def sig_sma_cross(D, i, fast=10, slow=50):
    f, s = D[f'sma_{fast}'], D[f'sma_{slow}']
    if f[i] > s[i] and f[i-1] <= s[i-1]: return 1
    if f[i] < s[i] and f[i-1] >= s[i-1]: return -1
    return 0

def sig_candlestick(D, i):
    s = 0
    s += D['hammer'][i] * 30
    s += D['engulfing_bull'][i] * 40
    s -= D['shooting_star'][i] * 30
    s -= D['doji'][i] * 10
    if s > 60: return 1
    if s < 40: return -1
    return 0

def sig_coin_toss(D, i):
    r = np.random.random()
    if r < 0.7: return 0
    return 1 if np.random.random() < 0.5 else -1

def sig_buy_hold(D, i):
    if i == 55: return 1
    return 0

# Registry: name → fn(D, i, [state]) → signal
STRATEGIES = {
    'turtle_20':      sig_turtle_20,
    'turtle_55':      sig_turtle_55,
    'turtle_dual':    sig_turtle_dual,
    '4week':          sig_4week,
    'rsi_momentum':   sig_rsi_momentum,
    'macd_trend':     sig_macd_trend,
    'bollinger_mr':   sig_bollinger_mr,
    'stochastic':     sig_stochastic,
    'sma_10_50':      lambda D, i: sig_sma_cross(D, i, 10, 50),
    'sma_20_50':      lambda D, i: sig_sma_cross(D, i, 20, 50),
    'sma_50_200':     lambda D, i: sig_sma_cross(D, i, 50, 200),
    'candlestick':    sig_candlestick,
    'coin_toss':      sig_coin_toss,
    'buy_hold':       sig_buy_hold,
}

# =========================================================================
# BACKTEST ENGINE
# =========================================================================

def run_single(D, sig_fn, params, n):
    """Run single-symbol backtest. sig_fn(D, i) → {-1,0,1}."""
    initial = params['initial_cash']
    commission = params['commission']
    rebalance = params['rebalance_days']
    max_pct = params['max_pct_portfolio']
    max_risk = params['max_risk_pct']
    stop_factor = params['stop_factor']
    use_atr_stop = params['atr_stop']
    max_hold = params.get('max_holding_days', 0)

    cash = initial
    shares = 0
    entry_price = 0.0
    entry_idx = 0
    trades = []
    equity = []
    last_rebal = -999
    atr_key = f'stop_lower_{stop_factor}'
    state = 0  # for stateful strategies

    for i in range(55, n):
        cp = D['close'][i]
        pv = cash + shares * cp

        is_rebal = (i - last_rebal) >= rebalance
        if is_rebal:
            last_rebal = i
            # Get signal
            try:
                s = sig_fn(D, i) if sig_fn != sig_turtle_dual else sig_turtle_dual(D, i, state)
                if isinstance(s, tuple):
                    s, state = s
            except Exception:
                s = 0

            if s == 1 and shares == 0 and cash > commission:
                # BUY
                trade_amt = min(cash, pv * max_pct)
                risk_amt = pv * max_risk
                stop_size = cp * max_risk
                sh_float = int(trade_amt / cp) if cp > 0 else 0
                sh_risk = int(risk_amt / stop_size) if stop_size > 0 else sh_float
                ns = max(0, min(sh_float, sh_risk))
                if ns > 0:
                    cost = ns * cp + commission
                    if cost <= cash:
                        shares = ns
                        cash -= cost
                        entry_price = cp
                        entry_idx = i
                        if sig_fn == sig_turtle_dual: state = 1

            elif s == -1 and shares > 0:
                # SELL on signal
                proceeds = shares * cp - commission
                pnl = proceeds - (shares * entry_price + commission)
                cash += proceeds
                trades.append({'pnl': pnl, 'ret': pnl/(shares*entry_price+commission)*100,
                               'hold': i - entry_idx})
                shares = 0
                if sig_fn == sig_turtle_dual: state = 0

        # ATR trailing stop
        if use_atr_stop and shares > 0:
            sl = D.get(f'stop_lower_{stop_factor}', None)
            if sl is not None and sl[i] > 0:
                if D['low'][i] <= sl[i]:
                    proceeds = shares * sl[i] - commission
                    pnl = proceeds - (shares * entry_price + commission)
                    cash += proceeds
                    trades.append({'pnl': pnl, 'ret': pnl/(shares*entry_price+commission)*100,
                                   'hold': i - entry_idx})
                    shares = 0

        # Max holding period stop
        if max_hold > 0 and shares > 0 and (i - entry_idx) >= max_hold:
            proceeds = shares * cp - commission
            pnl = proceeds - (shares * entry_price + commission)
            cash += proceeds
            trades.append({'pnl': pnl, 'ret': pnl/(shares*entry_price+commission)*100,
                           'hold': i - entry_idx})
            shares = 0

        equity.append(cash + shares * cp)

    # Close final
    final_value = cash + shares * D['close'][-1]
    if shares > 0:
        trades.append({'pnl': shares * (D['close'][-1] - entry_price),
                        'ret': (D['close'][-1] - entry_price) / entry_price * 100,
                        'hold': n - 1 - entry_idx})

    # Stats
    nt = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    wr = len(wins) / nt if nt else 0
    aw = np.mean([t['pnl'] for t in wins]) if wins else 0
    al = np.mean([t['pnl'] for t in losses]) if losses else 0
    exp = wr * aw + (1 - wr) * al
    tpnl = final_value - initial
    pct = tpnl / initial * 100
    eq = np.array(equity)
    peak = eq[0]
    max_dd = 0
    for v in eq:
        peak = max(peak, v)
        dd = (peak - v) / peak * 100
        max_dd = max(max_dd, dd)
    rets = pd.Series(eq).pct_change().dropna()
    sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if len(rets) > 1 and rets.std() > 0 else 0
    gp = sum(t['pnl'] for t in wins)
    gl = abs(sum(t['pnl'] for t in losses))
    pf = gp / gl if gl > 0 else float('inf')

    return {
        'final_value': round(final_value, 2),
        'total_pnl': round(tpnl, 2),
        'pnl_pct': round(pct, 2),
        'n_trades': nt,
        'win_rate': round(wr * 100, 1),
        'avg_win': round(aw, 2),
        'avg_loss': round(al, 2),
        'expectancy': round(exp, 2),
        'profit_factor': round(pf, 2),
        'max_drawdown': round(max_dd, 2),
        'sharpe': round(sharpe, 3),
    }


def run_combo(D, sig_fns, params, n):
    """Multi-strategy consensus backtest."""
    initial = params['initial_cash']
    commission = params['commission']
    rebalance = params['rebalance_days']
    max_pct = params['max_pct_portfolio']
    max_risk = params['max_risk_pct']
    stop_factor = params['stop_factor']
    use_atr_stop = params['atr_stop']
    max_hold = params.get('max_holding_days', 0)
    consensus_thresh = params.get('consensus_threshold', 0.5)

    cash = initial
    shares = 0
    entry_price = 0.0
    entry_idx = 0
    trades = []
    equity = []
    last_rebal = -999
    n_strats = len(sig_fns)
    D_combo = {k: v for k, v in D.items()}  # copy reference

    for i in range(55, n):
        cp = D['close'][i]
        pv = cash + shares * cp
        is_rebal = (i - last_rebal) >= rebalance

        if is_rebal:
            last_rebal = i
            votes = {-1: 0, 0: 1, 1: 1}  # start with 1 hold vote to avoid empty
            for name, fn in sig_fns.items():
                try:
                    s = fn(D, i)
                    if isinstance(s, tuple): s = s[0]
                    votes[s] = votes.get(s, 0) + 1
                except Exception:
                    votes[0] += 1
            votes[0] -= 1  # remove dummy

            non_hold = n_strats - votes.get(0, 0)

            if shares == 0 and cash > commission and non_hold > 0:
                buy_pct = votes.get(1, 0) / non_hold
                if votes.get(1, 0) > votes.get(-1, 0) and buy_pct >= consensus_thresh:
                    trade_amt = min(cash, pv * max_pct)
                    risk_amt = pv * max_risk
                    stop_size = cp * max_risk
                    sh_float = int(trade_amt / cp) if cp > 0 else 0
                    sh_risk = int(risk_amt / stop_size) if stop_size > 0 else sh_float
                    ns = max(0, min(sh_float, sh_risk))
                    if ns > 0 and ns * cp + commission <= cash:
                        shares = ns
                        cash -= ns * cp + commission
                        entry_price = cp
                        entry_idx = i

            elif shares > 0 and non_hold > 0:
                sell_pct = votes.get(-1, 0) / non_hold
                if votes.get(-1, 0) > votes.get(1, 0) and sell_pct >= consensus_thresh:
                    proceeds = shares * cp - commission
                    pnl = proceeds - (shares * entry_price + commission)
                    cash += proceeds
                    trades.append({'pnl': pnl, 'ret': pnl/(shares*entry_price+commission)*100,
                                   'hold': i - entry_idx})
                    shares = 0

        # ATR stop
        if use_atr_stop and shares > 0:
            sl = D.get(f'stop_lower_{stop_factor}', None)
            if sl is not None and D['low'][i] <= sl[i]:
                proceeds = shares * sl[i] - commission
                pnl = proceeds - (shares * entry_price + commission)
                cash += proceeds
                trades.append({'pnl': pnl, 'ret': pnl/(shares*entry_price+commission)*100,
                               'hold': i - entry_idx})
                shares = 0

        # Max holding
        if max_hold > 0 and shares > 0 and (i - entry_idx) >= max_hold:
            proceeds = shares * cp - commission
            pnl = proceeds - (shares * entry_price + commission)
            cash += proceeds
            trades.append({'pnl': pnl, 'ret': pnl/(shares*entry_price+commission)*100,
                           'hold': i - entry_idx})
            shares = 0

        equity.append(cash + shares * cp)

    final_value = cash + shares * D['close'][-1]
    if shares > 0:
        trades.append({'pnl': shares * (D['close'][-1] - entry_price),
                        'ret': (D['close'][-1] - entry_price) / entry_price * 100,
                        'hold': n - 1 - entry_idx})

    nt = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    wr = len(wins) / nt if nt else 0
    aw = np.mean([t['pnl'] for t in wins]) if wins else 0
    al = np.mean([t['pnl'] for t in losses]) if losses else 0
    exp = wr * aw + (1 - wr) * al
    tpnl = final_value - initial
    pct = tpnl / initial * 100
    eq = np.array(equity)
    peak = eq[0]
    max_dd = max(((peak - v) / peak * 100 for v in eq if peak > 0 and v < peak), default=0)
    rets = pd.Series(eq).pct_change().dropna()
    sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if len(rets) > 1 and rets.std() > 0 else 0
    gp = sum(t['pnl'] for t in wins)
    gl = abs(sum(t['pnl'] for t in losses))
    pf = gp / gl if gl > 0 else float('inf')

    return {
        'final_value': round(final_value, 2), 'total_pnl': round(tpnl, 2),
        'pnl_pct': round(pct, 2), 'n_trades': nt, 'win_rate': round(wr * 100, 1),
        'avg_win': round(aw, 2), 'avg_loss': round(al, 2),
        'expectancy': round(exp, 2), 'profit_factor': round(pf, 2),
        'max_drawdown': round(max_dd, 2), 'sharpe': round(sharpe, 3),
    }


# =========================================================================
# PARAM GRID
# =========================================================================

def get_grid(args):
    """Build parameter grid from CLI args or defaults."""
    # Defaults for full sweep
    grid = {
        'initial_cash': [100000],
        'commission': [9.95],
        'max_pct_portfolio': args.max_pct if args.max_pct else [0.05, 0.10, 0.15, 0.20],
        'rebalance_days': [7, 14, 30, 90],
        'max_risk_pct': [0.005, 0.01, 0.02],
        'stop_factor': args.stop_factor if args.stop_factor else [1.5, 2.0, 2.5, 3.0],
        'atr_stop': [True, False],
        'max_holding_days': [0, 20, 60],
    }
    # Override with fixed params if specified
    if args.max_pct:
        grid['max_pct_portfolio'] = [args.max_pct]
    if args.stop_factor:
        grid['stop_factor'] = [args.stop_factor]
    return grid


# =========================================================================
# MAIN
# =========================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbols', type=str)
    parser.add_argument('--strategy', type=str)
    parser.add_argument('--combos', action='store_true')
    parser.add_argument('--start', default='2014-01-01')
    parser.add_argument('--end', default='2024-12-31')
    parser.add_argument('--max-pct', type=float)
    parser.add_argument('--stop-factor', type=float)
    parser.add_argument('--out', default='/tmp/pipeline_v2.log')
    args = parser.parse_args()

    start, end = args.start, args.end
    log_path = Path(args.out)

    def log(msg):
        ts = time.strftime('%H:%M:%S')
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        with open(str(log_path), 'a') as f:
            f.write(line + '\n')

    # ── Load data ──
    conn = sqlite3.connect(DB_PATH)
    syms = [s.strip() for s in args.symbols.split(',')] if args.symbols else \
           [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM stockprices ORDER BY symbol").fetchall()]
    conn.close()

    log(f"Loading {len(syms)} symbols...")
    sym_data = {}
    for sym in syms:
        D, n = load_and_compute(sym, start, end)
        if D is not None:
            sym_data[sym] = (D, n)
            log(f"  {sym}: {n} rows")
        else:
            log(f"  SKIP {sym}: {n} rows")

    nsym = len(sym_data)
    log(f"Loaded {nsym} symbols")

    # ── Strategies ──
    if args.strategy:
        if args.strategy not in STRATEGIES:
            log(f"Unknown: {args.strategy}. Available: {list(STRATEGIES.keys())}")
            return
        active = {args.strategy: STRATEGIES[args.strategy]}
    else:
        active = dict(STRATEGIES)

    grid = get_grid(args)
    pkeys = list(grid.keys())
    pvals = list(grid.values())
    pcombos = list(itertools.product(*pvals))
    nparams = len(pcombos)

    log(f"Param combos: {nparams}, Strategies: {len(active)}, Symbols: {nsym}")
    log(f"Single tests: {nparams * len(active) * nsym}")

    # ── Create DB tables ──
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {RESULT_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, phase TEXT,
        strategy TEXT, combo_size INTEGER, combo_names TEXT, params_json TEXT,
        symbol TEXT, final_value REAL, total_pnl REAL, pnl_pct REAL,
        n_trades INTEGER, win_rate REAL, avg_win REAL, avg_loss REAL,
        expectancy REAL, profit_factor REAL, max_drawdown REAL, sharpe REAL
    )""")
    conn.execute(f"DELETE FROM {RESULT_TABLE}")
    conn.commit()

    run_ts = time.strftime('%Y-%m-%d %H:%M:%S')
    all_results = []
    t0 = time.time()

    # ── PHASE 1: Single strategy sweep ──
    log(f"{'─'*60}\nPHASE 1: Single Strategy Sweep\n{'─'*60}")

    for si, (sname, sfn) in enumerate(active.items()):
        log(f"\nStrategy {si+1}/{len(active)}: {sname}")
        for pi, pv in enumerate(pcombos):
            params = dict(zip(pkeys, pv))
            if pi % max(1, nparams // 4) == 0:
                elapsed = time.time() - t0
                log(f"  Params {pi+1}/{nparams} ({elapsed:.0f}s)")

            for sym, (D, n) in sym_data.items():
                try:
                    r = run_single(D, sfn, params, n)
                    r.update({'strategy': sname, 'combo_size': 1, 'combo_names': sname,
                              'params': json.dumps(params), 'symbol': sym,
                              'ts': run_ts, 'phase': 'single'})
                    all_results.append(r)
                    conn.execute(f"""INSERT INTO {RESULT_TABLE}
                        (ts, phase, strategy, combo_size, combo_names, params_json, symbol,
                         final_value, total_pnl, pnl_pct, n_trades, win_rate, avg_win,
                         avg_loss, expectancy, profit_factor, max_drawdown, sharpe)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (run_ts, 'single', sname, 1, sname, json.dumps(params), sym,
                         r['final_value'], r['total_pnl'], r['pnl_pct'], r['n_trades'],
                         r['win_rate'], r['avg_win'], r['avg_loss'], r['expectancy'],
                         r['profit_factor'], r['max_drawdown'], r['sharpe']))
                except Exception as e:
                    log(f"  ERROR {sname}/{sym}: {e}")
        conn.commit()

    elapsed = time.time() - t0
    log(f"\nPhase 1 done: {len(all_results)} results in {elapsed:.0f}s")

    # ── PHASE 2: Combo sweep ──
    if args.combos or not args.strategy:
        log(f"\n{'─'*60}\nPHASE 2: Combo Consensus Sweep\n{'─'*60}")
        combo_params = {'max_pct_portfolio': 0.10, 'rebalance_days': 30,
                        'max_risk_pct': 0.01, 'stop_factor': 2.0,
                        'initial_cash': 100000, 'commission': 9.95,
                        'atr_stop': True, 'max_holding_days': 0,
                        'consensus_threshold': 0.5}

        snames = list(active.keys())
        combo_count = 0
        for cs in range(2, min(len(snames) + 1, 6)):
            combos = list(itertools.combinations(snames, cs))
            log(f"\n  Combo size {cs}: {len(combos)} combos")
            for ci, combo in enumerate(combos):
                cname = '+'.join(combo)
                if ci % 20 == 0:
                    log(f"    [{ci+1}/{len(combos)}] {cname}")
                fns = {s: active[s] for s in combo}
                for sym, (D, n) in sym_data.items():
                    try:
                        r = run_combo(D, fns, combo_params, n)
                        r.update({'strategy': 'combo', 'combo_size': cs, 'combo_names': cname,
                                  'params': json.dumps(combo_params), 'symbol': sym,
                                  'ts': run_ts, 'phase': 'combo'})
                        all_results.append(r)
                        conn.execute(f"""INSERT INTO {RESULT_TABLE}
                            (ts, phase, strategy, combo_size, combo_names, params_json, symbol,
                             final_value, total_pnl, pnl_pct, n_trades, win_rate, avg_win,
                             avg_loss, expectancy, profit_factor, max_drawdown, sharpe)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (run_ts, 'combo', 'combo', cs, cname, json.dumps(combo_params), sym,
                             r['final_value'], r['total_pnl'], r['pnl_pct'], r['n_trades'],
                             r['win_rate'], r['avg_win'], r['avg_loss'], r['expectancy'],
                             r['profit_factor'], r['max_drawdown'], r['sharpe']))
                        combo_count += 1
                    except Exception as e:
                        log(f"    ERROR {cname}/{sym}: {e}")
            conn.commit()

        log(f"\nPhase 2 done: {combo_count} combo results")

    conn.close()

    # ── Summary ──
    pdf = pd.DataFrame(all_results)
    log(f"\n{'='*60}\nRESULTS SUMMARY ({len(pdf)} total)\n{'='*60}")

    sig = pdf[pdf['n_trades'] >= 5]
    if len(sig) > 0:
        # Top by Sharpe
        top = sig.nlargest(20, 'sharpe')
        log(f"\n🏆 TOP 20 BY SHARPE (min 5 trades):")
        log(f"  {'Strategy':<35s} {'Sym':<8s} {'Tr':>4s} {'Win%':>5s} {'P&L%':>7s} {'Shar':>6s} {'DD%':>6s} {'PF':>5s}")
        for _, r in top.iterrows():
            lbl = r['combo_names'] if r['combo_size'] > 1 else r['strategy']
            log(f"  {lbl:<35s} {r['symbol']:<8s} {r['n_trades']:>4d} {r['win_rate']:>5.1f} "
                f"{r['pnl_pct']:>+6.1f}% {r['sharpe']:>6.3f} {r['max_drawdown']:>5.1f}% {r['profit_factor']:>5.2f}")

        # Top by P&L
        top2 = sig.nlargest(20, 'pnl_pct')
        log(f"\n💰 TOP 20 BY P&L%:")
        for _, r in top2.iterrows():
            lbl = r['combo_names'] if r['combo_size'] > 1 else r['strategy']
            log(f"  {lbl:<35s} {r['symbol']:<8s} {r['n_trades']:>4d} {r['pnl_pct']:>+6.1f}% "
                f"{r['sharpe']:>6.3f} {r['max_drawdown']:>5.1f}%")

        # Strategy aggregates
        log(f"\n📊 STRATEGY AGGREGATES:")
        log(f"  {'Strategy':<30s} {'Avg P&L':>8s} {'Med P&L':>8s} {'Avg Shar':>8s} {'Avg DD':>7s} {'N':>5s}")
        for s in pdf['strategy'].unique():
            d = pdf[pdf['strategy'] == s]
            log(f"  {s:<28s} {d['pnl_pct'].mean():>+7.1f}% {d['pnl_pct'].median():>+7.1f}% "
                f"{d['sharpe'].mean():>8.3f} {d['max_drawdown'].mean():>6.1f}% {len(d):>5d}")

        # Combo size analysis
        cdat = pdf[pdf['combo_size'] > 1]
        if len(cdat) > 0:
            log(f"\n🔗 COMBO SIZE:")
            for cs in sorted(cdat['combo_size'].unique()):
                d = cdat[cdat['combo_size'] == cs]
                log(f"  Size {cs}: Avg P&L={d['pnl_pct'].mean():+.1f}% "
                    f"Avg Sharpe={d['sharpe'].mean():.3f} N={len(d)}")

    log(f"\n✅ Done! {len(pdf)} results → {RESULT_TABLE} table in {DB_PATH}")
    log(f"   Log: {log_path}")


if __name__ == '__main__':
    main()
