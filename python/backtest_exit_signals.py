#!/usr/bin/env python3
"""
Backtest framework for exit signal correlations.
Uses SQLite so we don't hammer MySQL during iteration.
"""

import argparse
import json
import logging
import math
import sqlite3
from pathlib import Path

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'CNR.TO', 'JNJ', 'PG', 'KO', 'PEP']
LOOKBACK_DAYS = 10 * 365
FORWARD_HORIZONS = [5, 22, 66]  # 1wk, 1mo, 3mo
DB_PATH = Path('/tmp/backtest_exit_signals.sqlite')

SIGNAL_META = [
    ('trailing_stop_breach', 'Trailing Stop Breach', 0.20),
    ('rsi_overbought', 'RSI Overbought', 0.10),
    ('ma200_breakdown', '200D MA Breakdown', 0.15),
    ('bb_upper_touch', 'Bollinger Band Upper Touch', 0.10),
    ('price_drop_7d', '7-Day Hard Drop', 0.15),
    ('roe_deterioration', 'ROE Deterioration', 0.10),
    ('debt_equity_rise', 'Debt/Equity Rise', 0.10),
    ('fcf_negative', 'FCF Negative', 0.10),
    ('pe_extreme', 'P/E Extreme', 0.08),
    ('insider_selling', 'Insider Selling', 0.05),
    ('corporate_event_risk', 'Corporate Event Risk', 0.05),
    ('sector_underperformance', 'Sector Underperformance', 0.08),
    ('fcf_yield_low', 'FCF Yield Low', 0.05),
    ('earnings_drop', 'Earnings Drop', 0.08),
    ('dividend_cut_signal', 'Dividend Cut Signal', 0.08),
    ('yield_on_cost_low', 'Yield on Cost Low', 0.05),
    ('debt_ebitda_high', 'Debt/EBITDA High', 0.08),
    ('cash_burn', 'Cash Burn', 0.08),
]
SIGNAL_NAMES = [s[0] for s in SIGNAL_META]


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS backtest_bars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            price_date TEXT NOT NULL,
            close REAL,
            forward_return_5d REAL,
            forward_return_22d REAL,
            forward_return_66d REAL,
            UNIQUE(symbol, price_date)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS backtest_signals (
            bar_id INTEGER NOT NULL,
            signal TEXT NOT NULL,
            triggered INTEGER NOT NULL,
            PRIMARY KEY(bar_id, signal)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_backtest_bars_sym ON backtest_bars(symbol)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_backtest_signals_bar ON backtest_signals(bar_id)')
    return conn


def get_symbol_data(symbol: str, days: int = LOOKBACK_DAYS) -> Optional[pd.DataFrame]:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=f'{days}d', auto_adjust=True)
        if hist.empty:
            return None
        hist = hist.rename(columns={c: c.lower().replace(' ', '_') for c in hist.columns})
        hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
        return hist
    except Exception as exc:
        logger.warning('fetch error %s: %s', symbol, exc)
        return None


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, min_periods=period).mean()


def get_fundamentals(symbol: str) -> Optional[dict]:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        base = {
            'roe': info.get('returnOnEquity'),
            'debt_to_equity': info.get('debtToEquity'),
            'fcf': info.get('freeCashflow'),
            'pe': info.get('trailingPE'),
            'market_cap': info.get('marketCap'),
            'eps_growth': info.get('earningsQuarterlyGrowth'),
        }
    except Exception:
        base = {}

    # augment / override from local MySQL if available
    try:
        conn = pymysql.connect(
            host='ksfraser.ca',
            user='ksfraser_stockmarket',
            password='Zaqwsx9sm1@',
            database='ksfraser_stock_market',
            charset='utf8mb4',
            connect_timeout=5,
        )
        cur = conn.cursor()
        cur.execute('SELECT field, value FROM fundamentals WHERE symbol = %s', (symbol,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for field, value in rows:
            field = field.lower()
            if field in ('roe', 'return_on_equity'):
                base['roe'] = value
            elif field in ('debt_to_equity', 'debtequity'):
                base['debt_to_equity'] = value
            elif field in ('free_cashflow', 'fcf'):
                base['fcf'] = value
            elif field in ('trailing_pe', 'pe'):
                base['pe'] = value
            elif field in ('market_cap',):
                base['market_cap'] = value
    except Exception:
        pass

    return base


def signals_for_bar(row: pd.Series, fundamentals: Optional[dict]) -> List[Tuple[str, float]]:
    signals: List[Tuple[str, float]] = []
    close = float(row['close'] or 0)
    if not close:
        return signals

    if not pd.isna(row.get('high_60')) and not pd.isna(row.get('atr_14')):
        ts = float(row['high_60']) - 3 * float(row['atr_14'])
        signals.append(('trailing_stop_breach', 1.0 if close < ts else 0.0))

    if not pd.isna(row.get('rsi_14')):
        signals.append(('rsi_overbought', 1.0 if float(row['rsi_14']) > 65 else 0.0))

    if not pd.isna(row.get('sma_200')):
        signals.append(('ma200_breakdown', 1.0 if close < 0.95 * float(row['sma_200']) else 0.0))

    if not pd.isna(row.get('bb_upper')) and not pd.isna(row.get('bb_lower')) and (float(row['bb_upper']) - float(row['bb_lower'])) > 0:
        bb_pos = (close - float(row['bb_lower'])) / (float(row['bb_upper']) - float(row['bb_lower']))
        signals.append(('bb_upper_touch', 1.0 if bb_pos > 0.95 else 0.0))

    if not pd.isna(row.get('close_7d_ago')):
        signals.append(('price_drop_7d', 1.0 if close < 0.95 * float(row['close_7d_ago']) else 0.0))

    if fundamentals and fundamentals.get('roe') is not None:
        signals.append(('roe_deterioration', 1.0 if float(fundamentals['roe']) < 0.10 else 0.0))

    if fundamentals and fundamentals.get('debt_to_equity') is not None:
        signals.append(('debt_equity_rise', 1.0 if float(fundamentals['debt_to_equity']) > 0.6 else 0.0))

    if fundamentals and fundamentals.get('fcf') is not None:
        signals.append(('fcf_negative', 1.0 if float(fundamentals['fcf']) < 0 else 0.0))

    if fundamentals and fundamentals.get('pe') is not None:
        signals.append(('pe_extreme', 1.0 if float(fundamentals['pe']) > 25 else 0.0))

    if fundamentals and fundamentals.get('market_cap') and fundamentals.get('fcf') is not None:
        fcf_yield = float(fundamentals['fcf']) / float(fundamentals['market_cap'])
        signals.append(('fcf_yield_low', 1.0 if fcf_yield < 0.02 else 0.0))

    return signals


def process_symbol(conn: sqlite3.Connection, symbol: str) -> None:
    logger.info('Processing %s', symbol)
    hist = get_symbol_data(symbol)
    if hist is None or len(hist) < 200:
        logger.warning('Skipping %s: insufficient data', symbol)
        return

    hist['close_7d_ago'] = hist['close'].shift(7)
    hist['sma_200'] = hist['close'].rolling(200).mean()
    hist['bb_mid'] = hist['close'].rolling(20).mean()
    hist['bb_std'] = hist['close'].rolling(20).std()
    hist['bb_upper'] = hist['bb_mid'] + 2 * hist['bb_std']
    hist['bb_lower'] = hist['bb_mid'] - 2 * hist['bb_std']
    hist['atr_14'] = compute_atr(hist, 14)
    hist['high_60'] = hist['high'].rolling(60).max()
    hist['rsi_14'] = compute_rsi(hist['close'], 14)
    fundamentals = get_fundamentals(symbol)

    bars: list[tuple] = []
    sig_bulk: list[tuple] = []
    max_look = max(FORWARD_HORIZONS)

    for i in range(199, len(hist) - max_look):
        row = hist.iloc[i]
        dt = hist.index[i]
        dt_str = dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt)
        close = float(row['close'] or 0)
        if not close:
            continue

        fwd5 = (float(hist['close'].iloc[i + 5]) / close) - 1
        fwd22 = (float(hist['close'].iloc[i + 22]) / close) - 1
        fwd66 = (float(hist['close'].iloc[i + 66]) / close) - 1
        bar_id = None

        bars.append((symbol, dt_str, close, float(fwd5), float(fwd22), float(fwd66)))

    conn.executemany(
        '''INSERT OR REPLACE INTO backtest_bars(symbol, price_date, close, forward_return_5d, forward_return_22d, forward_return_66d) VALUES (?,?,?,?,?,?)''',
        bars,
    )
    conn.commit()

    bar_rows = conn.execute('SELECT id, price_date FROM backtest_bars WHERE symbol = ?', (symbol,)).fetchall()
    bar_map = {dt: bid for bid, dt in bar_rows}

    for i in range(199, len(hist) - max_look):
        row = hist.iloc[i]
        dt = hist.index[i]
        dt_str = dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt)
        bar_id = bar_map.get(dt_str)
        if not bar_id:
            continue
        sigs = signals_for_bar(row, fundamentals)
        for name, val in sigs:
            sig_bulk.append((bar_id, name, int(val > 0.5)))

    conn.executemany('INSERT OR REPLACE INTO backtest_signals(bar_id, signal, triggered) VALUES (?,?,?)', sig_bulk)
    conn.commit()
    logger.info('Saved %s bars + %s signals for %s', len(bars), len(sig_bulk), symbol)


def correlations(conn: sqlite3.Connection, horizon_label: str = 'forward_return_22d') -> dict:
    rows = conn.execute(f'''
        SELECT s.signal, s.triggered, b.{horizon_label}
        FROM backtest_signals s
        JOIN backtest_bars b ON s.bar_id = b.id
        WHERE b.{horizon_label} IS NOT NULL
    ''').fetchall()
    if not rows:
        return {}
    df = pd.DataFrame(rows, columns=['signal', 'triggered', 'forward'])
    results = {}
    for sig, group in df.groupby('signal'):
        if group['triggered'].std() == 0 or group['forward'].std() == 0:
            continue
        corr = group['triggered'].corr(group['forward'])
        results[sig] = float(corr)
    return results


def recommendation(row: pd.Series, weights: dict, fundamentals: Optional[dict]) -> Tuple[str, float]:
    sigs = signals_for_bar(row, fundamentals)
    if not sigs:
        return 'HOLD', 0.5
    score = sum((weights.get(name, 0) or 0) * val for name, val in sigs)
    max_score = sum(abs(weights.get(name, 0) or 0) for name, _ in sigs) or 1
    norm = score / max_score
    if norm >= 0.55:
        return 'SELL', round(norm, 3)
    if norm <= 0.35:
        return 'BUY', round(norm, 3)
    return 'HOLD', round(norm, 3)


def run_backtest(symbols: List[str], compute_weights: bool = False):
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = init_db()

    for symbol in symbols:
        try:
            process_symbol(conn, symbol)
        except Exception as exc:
            logger.exception('Failed %s: %s', symbol, exc)

    agg = {}
    for horizon in ['5d', '22d', '66d']:
        c = correlations(conn, f'forward_return_{horizon}')
        agg[horizon] = c
        logger.info('Horizon %s correlations: %s', horizon, c)

    if compute_weights:
        primary = agg.get('22d', {})
        weights = {name: float(primary.get(name, 0) or 0) for name in SIGNAL_NAMES}
        total = sum(abs(w) for w in weights.values()) or 1
        weights = {k: round(v / total, 4) for k, v in weights.items()}
        logger.info('Derived weights: %s', weights)
    else:
        weights = {name: wt for _, name, wt in SIGNAL_META}

    return agg, weights


def current_recommendation(symbol: str, weights: dict, days: int = 250) -> Tuple[str, float]:
    hist = get_symbol_data(symbol, days)
    if hist is None or len(hist) < 200:
        return 'HOLD', 0.5
    hist['close_7d_ago'] = hist['close'].shift(7)
    hist['sma_200'] = hist['close'].rolling(200).mean()
    hist['bb_mid'] = hist['close'].rolling(20).mean()
    hist['bb_std'] = hist['close'].rolling(20).std()
    hist['bb_upper'] = hist['bb_mid'] + 2 * hist['bb_std']
    hist['bb_lower'] = hist['bb_mid'] - 2 * hist['bb_std']
    hist['atr_14'] = compute_atr(hist, 14)
    hist['high_60'] = hist['high'].rolling(60).max()
    hist['rsi_14'] = compute_rsi(hist['close'], 14)
    fundamentals = get_fundamentals(symbol)
    row = hist.iloc[-1]
    return recommendation(row, weights, fundamentals)


def main():
    parser = argparse.ArgumentParser(description='Backtest exit signals with SQLite')
    parser.add_argument('--symbols', nargs='*', default=DEFAULT_SYMBOLS, help='Comma/space separated symbols')
    parser.add_argument('--compute-weights', action='store_true')
    parser.add_argument('--symbol')
    args = parser.parse_args()

    if args.symbols:
        flat = []
        for token in args.symbols:
            flat.extend(token.split(','))
        args.symbols = [s.strip() for s in flat if s.strip()]

    if args.symbol:
        agg, weights = run_backtest(args.symbols, compute_weights=True)
        rec, score = current_recommendation(args.symbol, weights)
        print(f'=== {args.symbol} Recommendation ===')
        print(f'Recommendation: {rec} (score={score})')
        return

    agg, weights = run_backtest(args.symbols, args.compute_weights)
    print(json.dumps({'correlations': agg, 'weights': weights}, indent=2))


if __name__ == '__main__':
    main()
