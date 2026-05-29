#!/usr/bin/env python3
"""
sqlite_scoring.py — Lightweight scoring engine for SQLite dev DB
=================================================================
Computes momentum, mean-reversion, trend, and volatility signals
from price data and writes to evalsummary table for backtest engine.

Usage:
  python3 sqlite_scoring.py                    # Score all symbols
  python3 sqlite_scoring.py --symbols RY.TO,CM  # Specific symbols
"""

import argparse
import logging
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "analysis_results.db"


def get_symbols(conn):
    """Get all symbols that have price data."""
    cur = conn.execute("SELECT DISTINCT symbol FROM stockprices ORDER BY symbol")
    return [r[0] for r in cur.fetchall()]


def compute_signals_for_symbol(conn, symbol):
    """
    Compute scoring signals for a single symbol from price data.
    Returns list of dicts, one per date, with signal scores.
    """
    df = pd.read_sql_query(
        "SELECT symbol, price_date, day_open as open, day_high as high, day_low as low, day_close as close, volume FROM stockprices WHERE symbol = ? ORDER BY price_date",
        conn, params=(symbol,), parse_dates=['price_date']
    )
    df = df.set_index('price_date').sort_index()

    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    volume = df['volume'].astype(float) if 'volume' in df.columns else pd.Series(0, index=df.index)

    # === MOMENTUM SIGNALS ===
    # Rate of Change (10-day, 20-day, 60-day)
    roc_10 = close.pct_change(10) * 100
    roc_20 = close.pct_change(20) * 100
    roc_60 = close.pct_change(60) * 100

    # RSI (14-day)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    macd_hist = macd_line - signal_line

    # === TREND SIGNALS ===
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()
    ema_12 = close.ewm(span=12).mean()
    ema_26 = close.ewm(span=26).mean()

    # Price vs SMA position (-1 to 1)
    vs_sma20 = (close - sma_20) / sma_20 * 100
    vs_sma50 = (close - sma_50) / sma_50 * 100
    vs_sma200 = (close - sma_200) / sma200 * 100 if 'sma200' in dir() else (close - sma_200) / sma_200 * 100

    # SMA crossovers
    sma_cross = np.where(sma_20 > sma_50, 1, -1)

    # === MEAN REVERSION ===
    # Bollinger Bands
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_pct = (close - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan)

    # Z-score (20-day)
    zscore_20 = (close - close.rolling(20).mean()) / close.rolling(20).std().replace(0, np.nan)

    # === VOLATILITY ===
    # ATR (14-day)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_14 = tr.rolling(14).mean()
    atr_pct = atr_14 / close * 100

    # Historical volatility (20-day annualized)
    returns = close.pct_change()
    hvol_20 = returns.rolling(20).std() * np.sqrt(252) * 100

    # === VOLUME ===
    vol_sma20 = volume.rolling(20).mean()
    vol_ratio = volume / vol_sma20.replace(0, np.nan)

    # === COMPOSITE SCORING ===
    # Momentum score: -100 to +100
    momentum_score = (
        roc_10.fillna(0) * 1.0 +
        roc_20.fillna(0) * 0.8 +
        roc_60.fillna(0) * 0.5 +
        (rsi.fillna(50) - 50) * 0.5 +
        macd_hist.fillna(0) * 2.0
    )

    # Trend score: -100 to +100
    trend_score = (
        vs_sma20.fillna(0) * 1.5 +
        vs_sma50.fillna(0) * 1.0 +
        np.where(sma_20.fillna(0) > sma_50.fillna(0), 20, -20)
    )

    # Mean reversion score: -100 to +100 (contrarian)
    mr_score = (
        -zscore_20.fillna(0) * 15 +
        -(bb_pct.fillna(0.5) - 0.5) * 100
    )

    # Volatility score: 0 to 100 (higher = more volatile)
    vol_score = atr_pct.fillna(0) * 2 + hvol_20.fillna(0) * 0.5

    # Volume confirmation: -50 to +50
    vol_confirm = (vol_ratio.fillna(1) - 1) * 30

    # === FINAL COMPOSITE ===
    # Weighted combination
    total_score = (
        momentum_score * 0.35 +
        trend_score * 0.30 +
        mr_score * 0.15 +
        vol_confirm * 0.20
    )

    # Signal strength: -100 to +100
    signal_strength = total_score.clip(-100, 100)

    # Build results
    results = []
    for idx in df.index:
        row = {
            'symbol': symbol,
            'eval_date': idx.strftime('%Y-%m-%d'),
            'close_price': round(float(close.loc[idx]), 4) if idx in close.index else None,
            'momentum_score': round(float(momentum_score.loc[idx]), 4) if idx in momentum_score.index and not np.isnan(momentum_score.loc[idx]) else 0,
            'trend_score': round(float(trend_score.loc[idx]), 4) if idx in trend_score.index and not np.isnan(trend_score.loc[idx]) else 0,
            'mean_reversion_score': round(float(mr_score.loc[idx]), 4) if idx in mr_score.index and not np.isnan(mr_score.loc[idx]) else 0,
            'volatility_score': round(float(vol_score.loc[idx]), 4) if idx in vol_score.index and not np.isnan(vol_score.loc[idx]) else 0,
            'volume_confirm': round(float(vol_confirm.loc[idx]), 4) if idx in vol_confirm.index and not np.isnan(vol_confirm.loc[idx]) else 0,
            'signal_strength': round(float(signal_strength.loc[idx]), 4) if idx in signal_strength.index and not np.isnan(signal_strength.loc[idx]) else 0,
            'rsi_14': round(float(rsi.loc[idx]), 2) if idx in rsi.index and not np.isnan(rsi.loc[idx]) else None,
            'macd_hist': round(float(macd_hist.loc[idx]), 4) if idx in macd_hist.index and not np.isnan(macd_hist.loc[idx]) else None,
            'atr_pct': round(float(atr_pct.loc[idx]), 4) if idx in atr_pct.index and not np.isnan(atr_pct.loc[idx]) else None,
            'bb_pct': round(float(bb_pct.loc[idx]), 4) if idx in bb_pct.index and not np.isnan(bb_pct.loc[idx]) else None,
            'zscore_20': round(float(zscore_20.loc[idx]), 4) if idx in zscore_20.index and not np.isnan(zscore_20.loc[idx]) else None,
            'roc_10': round(float(roc_10.loc[idx]), 4) if idx in roc_10.index and not np.isnan(roc_10.loc[idx]) else None,
            'roc_20': round(float(roc_20.loc[idx]), 4) if idx in roc_20.index and not np.isnan(roc_20.loc[idx]) else None,
            'hvol_20': round(float(hvol_20.loc[idx]), 4) if idx in hvol_20.index and not np.isnan(hvol_20.loc[idx]) else None,
        }
        results.append(row)

    return results


def create_evalsummary_table(conn):
    """Create evalsummary table if it doesn't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evalsummary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            eval_date TEXT NOT NULL,
            close_price REAL,
            momentum_score REAL DEFAULT 0,
            trend_score REAL DEFAULT 0,
            mean_reversion_score REAL DEFAULT 0,
            volatility_score REAL DEFAULT 0,
            volume_confirm REAL DEFAULT 0,
            signal_strength REAL DEFAULT 0,
            rsi_14 REAL,
            macd_hist REAL,
            atr_pct REAL,
            bb_pct REAL,
            zscore_20 REAL,
            roc_10 REAL,
            roc_20 REAL,
            hvol_20 REAL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(symbol, eval_date)
        );
        CREATE INDEX IF NOT EXISTS idx_evalsum_symbol ON evalsummary(symbol);
        CREATE INDEX IF NOT EXISTS idx_evalsum_date ON evalsummary(eval_date);
        CREATE INDEX IF NOT EXISTS idx_evalsum_signal ON evalsummary(signal_strength);
    """)
    conn.commit()


def write_scores(conn, results):
    """Write scoring results to evalsummary table."""
    if not results:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO evalsummary (
            symbol, eval_date, close_price, momentum_score, trend_score,
            mean_reversion_score, volatility_score, volume_confirm,
            signal_strength, rsi_14, macd_hist, atr_pct, bb_pct,
            zscore_20, roc_10, roc_20, hvol_20
        ) VALUES (
            :symbol, :eval_date, :close_price, :momentum_score, :trend_score,
            :mean_reversion_score, :volatility_score, :volume_confirm,
            :signal_strength, :rsi_14, :macd_hist, :atr_pct, :bb_pct,
            :zscore_20, :roc_10, :roc_20, :hvol_20
        )
    """, results)
    conn.commit()
    return len(results)


def main():
    parser = argparse.ArgumentParser(description="SQLite Scoring Engine")
    parser.add_argument('--symbols', type=str, help='Comma-separated symbols')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))

    # Create table
    create_evalsummary_table(conn)

    # Get symbols
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
    else:
        symbols = get_symbols(conn)

    logger.info(f"Scoring {len(symbols)} symbols...")

    total_rows = 0
    for i, symbol in enumerate(symbols):
        logger.info(f"  [{i+1}/{len(symbols)}] {symbol}")
        results = compute_signals_for_symbol(conn, symbol)
        if results:
            n = write_scores(conn, results)
            total_rows += n
            logger.info(f"    → {n} rows written")

    logger.info(f"\n✅ Done! {total_rows} total scoring rows written for {len(symbols)} symbols")

    # Show summary stats
    stats = pd.read_sql_query("""
        SELECT symbol,
               COUNT(*) as rows,
               ROUND(AVG(signal_strength), 2) as avg_signal,
               ROUND(MIN(signal_strength), 2) as min_signal,
               ROUND(MAX(signal_strength), 2) as max_signal,
               ROUND(AVG(rsi_14), 1) as avg_rsi
        FROM evalsummary
        GROUP BY symbol
        ORDER BY symbol
    """, conn)
    print("\n" + stats.to_string(index=False))

    conn.close()


if __name__ == '__main__':
    main()
