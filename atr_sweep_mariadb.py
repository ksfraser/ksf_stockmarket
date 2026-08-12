#!/usr/bin/env python3
"""
ATR Stop Drawdown-Recovery Sweep for MariaDB
============================================

PURPOSE
-------
For each symbol and each candidate ATR multiple `m` (stop placed m x ATR below
the running local high), measure how often an m*ATR drawdown BOUNCES BACK to a
new high within a forward window.

WHY
---
A stop that is too tight gets hit on ordinary noise: the price dips m*ATR, we
exit, and then it recovers to new highs (resetting trailing stops we would have
kept). The bounce-back rate tells us exactly that: at m=2 (2ATR) what fraction
of drops recover? If it is ~90%+, a 2ATR stop is a FALSE-EXIT generator.

We therefore recommend the TIGHTEST multiple whose bounce-back rate is at or
below `BOUNCE_THRESHOLD` -- wide enough to avoid most recoverable dips, but
still tight enough to trigger on genuine adverse moves. We also report the
symbol's historical MAX DRAWDOWN in ATR units as context (how many ATRs the
worst real adverse move was).

OUTPUT TABLE: atr_stop_optimization
  ts, symbol, atr_multiple, n_drops, bounce_back_rate,
  avg_recovery_days, max_drawdown_atr, recommended
"""
import os
import sys
import logging
from datetime import datetime, date

import pandas as pd
import numpy as np

# MariaDB connection
import mysql.connector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'ksfraser.ca'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'ksfraser_stockmarket'),
    'password': os.environ.get('DB_PASS', 'Zaqwsx9sm1@'),
    'database': os.environ.get('DB_NAME', 'ksfraser_stock_market'),
    'charset': 'utf8mb4',
    'autocommit': True,
    'connection_timeout': 60,
    'pool_name': 'ksf_atr_sweep',
    'pool_size': 3,
}

_POOL = mysql.connector.pooling.MySQLConnectionPool(
    pool_name=DB_CONFIG['pool_name'],
    pool_size=DB_CONFIG['pool_size'],
    **{k: v for k, v in DB_CONFIG.items() if k not in ('pool_name', 'pool_size')}
)


def get_connection():
    """Get pooled MariaDB connection."""
    return _POOL.get_connection()


# ── Tunables ──────────────────────────────────────────────────────────────────
DEFAULT_START = '2018-01-01'
DEFAULT_END = str(date.today())
ATR_PERIOD = 14
LOOKFORWARD = 60          # trading days allowed for a bounce-back to count
BOUNCE_ACCEPTABLE = 0.70   # recommended = tightest m whose bounce_back_rate <= this.
                           # User's red line was "90% bounce = too tight"; we treat
                           # >70% bounce as still mostly recoverable dips, so the
                           # stop should be at least wide enough to pull bounce <=70%.
MULTIPLES = [1.0, 1.5, 2.0, 2.25, 2.5, 3.0, 3.5, 4.0]

SCHEMA = """
CREATE TABLE IF NOT EXISTS atr_stop_optimization (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    ts TEXT,
    symbol TEXT,
    atr_multiple REAL,
    n_drops INT,
    bounce_back_rate REAL,
    avg_recovery_days REAL,
    max_drawdown_atr REAL,
    recommended TINYINT DEFAULT 0
)
"""


# ── Data access ───────────────────────────────────────────────────────────────
def fetch_price_data(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV data for a symbol from stockprices."""
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT price_date, open as o, high as h,
               low as l, close as c, volume as v
        FROM stockprices
        WHERE symbol = %s AND price_date BETWEEN %s AND %s
        ORDER BY price_date
        """,
        conn, params=(symbol, start, end), parse_dates=['price_date'])
    conn.close()
    if df.empty:
        return df
    df = df.set_index('price_date').sort_index()
    for col in ['o', 'h', 'l', 'c', 'v']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def fetch_portfolio_symbols() -> list:
    """Get symbols currently held in portfolio (shares > 0)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM portfolio WHERE shares > 0")
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return symbols


def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    """Simple rolling ATR (Ta-Lib style True Range, rolling mean)."""
    high = df['h'].values
    low = df['l'].values
    close = df['c'].values

    tr_list = []
    for i in range(1, len(high)):
        tr = max(high[i] - low[i],
                 abs(high[i] - close[i - 1]),
                 abs(low[i] - close[i - 1]))
        tr_list.append(tr)

    tr = np.array([0] + tr_list)
    atr = pd.Series(tr, index=df.index).rolling(period).mean()
    return atr


# ── Core analysis ─────────────────────────────────────────────────────────────
def analyze_drawdown_recovery(df: pd.DataFrame, atr: pd.Series, m: float,
                              lookforward: int = LOOKFORWARD) -> dict:
    """
    For a single ATR multiple m, walk the series tracking a running local high.
    Each time price falls m*ATR below that high -> a STOP event. Then check if
    price later recovers to >= the pre-drop high within `lookforward` trading
    days. bounce_back_rate = fraction of stop events that recovered.
    """
    hi = df['h'].values.astype(float)
    lo = df['l'].values.astype(float)
    cl = df['c'].values.astype(float)
    n = len(df)
    atr_med = atr.median()

    peak = None
    peak_idx = None
    events = []  # (peak_idx, peak_price, event_idx)

    for i in range(n):
        a = atr.iloc[i]
        # Skip NaN / non-positive / split-artifact bars (ATR far below typical)
        if pd.isna(a) or a <= 0 or a < 0.02 * atr_med:
            continue
        h_i, l_i = hi[i], lo[i]
        if peak is None:
            peak = h_i
            peak_idx = i
            continue
        if h_i > peak:
            peak = h_i
            peak_idx = i
        stop_level = peak - m * a
        if l_i <= stop_level:
            events.append((peak_idx, peak, i))
            # reset the local-high tracker from the event bar onward
            peak = h_i
            peak_idx = i

    bounced = 0
    rec_days = []
    for (pk_idx, pk_price, ev_idx) in events:
        recovered = False
        rd = None
        end_j = min(ev_idx + 1 + lookforward, n)
        for j in range(ev_idx + 1, end_j):
            if cl[j] >= pk_price or hi[j] >= pk_price:
                recovered = True
                rd = j - ev_idx
                break
        if recovered:
            bounced += 1
            rec_days.append(rd)

    n_ev = len(events)
    return {
        'n_drops': n_ev,
        'bounce_back_rate': (bounced / n_ev) if n_ev else None,
        'avg_recovery_days': (sum(rec_days) / len(rec_days)) if rec_days else None,
    }


def max_drawdown_in_atr(df: pd.DataFrame, atr: pd.Series) -> float:
    """Largest peak-to-trough decline expressed in ATR units (context only)."""
    cl = df['c'].values.astype(float)
    atr_med = atr.median()
    peak = -1e18
    maxdd = 0.0
    for i in range(len(df)):
        a = atr.iloc[i]
        if pd.isna(a) or a <= 0 or a < 0.02 * atr_med:
            continue
        if cl[i] > peak:
            peak = cl[i]
        dd = (peak - cl[i]) / a
        if dd > maxdd:
            maxdd = dd
    return maxdd


def choose_recommended(multiples, stats, threshold=BOUNCE_ACCEPTABLE):
    """Tightest multiple whose bounce-back rate <= threshold; else the multiple
    with the most drops and the lowest bounce rate; else 2.5."""
    eligible = [m for m in sorted(multiples)
                if stats[m]['n_drops'] and stats[m]['bounce_back_rate'] is not None
                and stats[m]['bounce_back_rate'] <= threshold]
    if eligible:
        return eligible[0]
    valid = [(m, stats[m]['bounce_back_rate']) for m in multiples if stats[m]['n_drops']]
    if valid:
        return min(valid, key=lambda x: (x[1] if x[1] is not None else 1.0))[0]
    return 2.5


# ── Per-symbol sweep (reusable by the add-symbol hook) ───────────────────────
def run_sweep_for_symbol(symbol: str, start: str = DEFAULT_START, end: str = DEFAULT_END,
                         multiples: list = None, lookforward: int = LOOKFORWARD,
                         threshold: float = BOUNCE_ACCEPTABLE, verbose: bool = True) -> dict:
    """Compute the drawdown-recovery sweep for ONE symbol and persist it.
    Safe to call from the daily pipeline when a new symbol is backfilled."""
    if multiples is None:
        multiples = MULTIPLES

    df = fetch_price_data(symbol, start, end)
    if df.empty or len(df) < 60:
        logger.warning(f"{symbol}: insufficient price data for sweep")
        return None

    atr = calculate_atr(df)
    maxdd = max_drawdown_in_atr(df, atr)

    stats = {m: analyze_drawdown_recovery(df, atr, m, lookforward) for m in multiples}
    rec = choose_recommended(multiples, stats, threshold)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM atr_stop_optimization WHERE symbol=%s", (symbol,))
    ts = datetime.now().isoformat()
    for m in multiples:
        s = stats[m]
        cur.execute(
            """INSERT INTO atr_stop_optimization
               (ts, symbol, atr_multiple, n_drops, bounce_back_rate,
                avg_recovery_days, max_drawdown_atr, recommended)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (ts, symbol, m, s['n_drops'], s['bounce_back_rate'],
             s['avg_recovery_days'], maxdd, 1 if m == rec else 0))
    conn.commit()
    conn.close()

    if verbose:
        parts = []
        for m in multiples:
            br = stats[m]['bounce_back_rate']
            br_s = '-' if br is None else '{:.2f}'.format(br)
            parts.append("{m}x:{br}(n={n})".format(m=m, br=br_s, n=stats[m]['n_drops']))
        bits = "  ".join(parts)
        logger.info("{sym}: maxDD={dd:.1f}ATR  recommended={rec}x  | {bits}".format(
            sym=symbol, dd=maxdd, rec=rec, bits=bits))

    return {'symbol': symbol, 'max_drawdown_atr': maxdd, 'recommended': rec, 'stats': stats}


# ── Full portfolio sweep ──────────────────────────────────────────────────────
def main():
    symbols = fetch_portfolio_symbols()
    logger.info(f"Sweeping {len(symbols)} portfolio symbols for ATR drawdown-recovery")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS atr_stop_optimization")
    cur.execute(SCHEMA)
    conn.commit()
    conn.close()

    results = []
    for sym in symbols:
        try:
            r = run_sweep_for_symbol(sym)
            if r:
                results.append(r)
        except Exception as e:
            logger.error(f"{sym}: sweep failed: {e}")

    if results:
        print("\n=== RECOMMENDED ATR MULTIPLE PER SYMBOL ===")
        for r in sorted(results, key=lambda x: x['symbol']):
            print(f"  {r['symbol']:8s}  recommended={r['recommended']}x  "
                  f"maxDD={r['max_drawdown_atr']:.1f}ATR")
        avg_rec = sum(r['recommended'] for r in results) / len(results)
        avg_dd = sum(r['max_drawdown_atr'] for r in results) / len(results)
        logger.info(f"Portfolio avg recommended multiple: {avg_rec:.2f}x  "
                    f"avg max drawdown: {avg_dd:.1f}ATR")


if __name__ == '__main__':
    main()
