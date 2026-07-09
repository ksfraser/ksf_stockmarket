#!/usr/bin/env python3
"""
Backtest framework for exit signal correlations.

- Uses SQLite so we don't hammer MySQL during iteration.
- Computes each of the 18 exit signals per bar.
- Stores signal hits + forward returns.
- Aggregates per-indicator correlations vs forward returns.
- Derives global weights from average correlations.
- Re-runs scoring with global weights and reports recommendations.
"""

import argparse
import json
import logging
import math
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pymysql
import yfinance as yf

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'CNR.TO', 'JNJ', 'PG', 'KO', 'PEP']
LOOKBACK_DAYS = 10 * 365

DB_CFG = {
    'host': 'ksfraser.ca',
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
}

# Mirror of investorsobserver 18 warning signs.
# Order: technical (5), fundamental (7), event/relative (6)
SIGNAL_META = [
    ('trailing_stop_breach', 'Trailing Stop Breach', 'Price below ATR-based trailing stop (3×ATR from 60d high)', 0.20),
    ('rsi_overbought', 'RSI Overbought', 'RSI(14) above 65 — momentum overextended', 0.10),
    ('ma200_breakdown', '200D MA Breakdown', 'Price below 95% of 200-day SMA — long-term trend broken', 0.15),
    ('bb_upper_touch', 'Bollinger Band Upper Touch', 'Price at >95% of BB(20,2) range — overextended', 0.10),
    ('price_drop_7d', '7-Day Hard Drop', 'Close < 95% of close 7 days ago — >5% drop in 1 week', 0.15),
    ('roe_deterioration', 'ROE Deterioration', 'Return on Equity below 10% — quality declining', 0.10),
    ('debt_equity_rise', 'Debt/Equity Rise', 'D/E ratio above 0.6 — leverage increasing', 0.10),
    ('fcf_negative', 'FCF Negative', 'Free Cash Flow negative — cash burn', 0.10),
    ('pe_extreme', 'P/E Extreme', 'Trailing P/E above 25× — valuation stretched', 0.08),
    ('insider_selling', 'Insider Selling', 'Insider sell ratio >50% in 90 days', 0.05),
    ('corporate_event_risk', 'Corporate Event Risk', 'Merger/acquisition/restructuring pending', 0.05),
    ('sector_underperformance', 'Sector Underperformance', 'Stock lagging sector ETF by >10%', 0.08),
    ('fcf_yield_low', 'FCF Yield Low', 'FCF/Market Cap below 2% — poor cash generation', 0.05),
    ('earnings_drop', 'Earnings Drop', 'EPS declined >20% YoY', 0.08),
    ('dividend_cut_signal', 'Dividend Cut Signal', 'Dividend history shows cuts or skipped payments', 0.08),
    ('yield_on_cost_low', 'Yield on Cost Low', 'Yield on cost below 1.5% for dividend investor', 0.05),
    ('debt_ebitda_high', 'Debt/EBITDA High', 'Debt/EBITDA above 4× — leverage risk', 0.08),
    ('cash_burn', 'Cash Burn', 'Cash runway <4 quarters at current burn rate', 0.08),
]

SIGNAL_NAMES = [s[0] for s in SIGNAL_META]


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


def compute_signals(hist: pd.DataFrame, fundamentals: Optional[dict]) -> pd.DataFrame:
    df = hist.copy()
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    # technical sets
    df['rsi_14'] = compute_rsi(close, 14)
    df['sma_200'] = close.rolling(200).mean()
    df['bb_mid'] = close.rolling(20).mean()
    df['bb_std'] = close.rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['atr_14'] = compute_atr(df, 14)
    df['high_60'] = high.rolling(60).max()

    out: dict[str, pd.Series] = {}

    # 1. Trailing stop breach
    ts = df['high_60'] - 3 * df['atr_14']
    out['trailing_stop_breach'] = (close < ts).astype(float)

    # 2. RSI overbought
    out['rsi_overbought'] = (df['rsi_14'] > 65).astype(float)

    # 3. 200D MA breakdown
    out['ma200_breakdown'] = (close < 0.95 * df['sma_200']).astype(float)

    # 4. Bollinger upper touch
    bb_range = df['bb_upper'] - df['bb_lower']
    bb_pos = np.where(bb_range > 0, (close - df['bb_lower']) / bb_range, 0.5)
    out['bb_upper_touch'] = (bb_pos > 0.95).astype(float)

    # 5. 7-day hard drop
    out['price_drop_7d'] = (close < 0.95 * close.shift(7)).astype(float)

    # fundamental: best-effort from yfinance
