"""Common market-data façade for the stockmarket app.

This module is the ONLY place the rest of the app should import market data
from (as ``from common.market_data import ...``).
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

import yfinance as yf


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee the capitalized OHLCV columns the indicators expect."""
    lower_map = {c.lower(): c for c in df.columns}
    out = pd.DataFrame(index=df.index)
    for want in ("Open", "High", "Low", "Close", "Volume", "Adj Close"):
        if want in df.columns:
            out[want] = df[want]
        elif want.lower() in lower_map:
            out[want] = df[lower_map[want.lower()]]
    return out


def get_ohlcv(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV price history for *symbol* via yfinance."""
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception:
        return pd.DataFrame()
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df = df.get_level_values("Close") if "Close" in df.columns.names else df.iloc[:, 0]
        df = df.to_frame("Close")
    return _normalize_columns(df)


def get_info(symbol: str) -> Dict:
    """Fetch company info / quote data for *symbol* via yfinance."""
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        return {}
    return info
